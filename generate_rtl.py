import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import logging
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
EXCEL_PATH = os.environ.get("EXCEL_PATH", "generateRTLtest.xlsx")
BASE_URL = "https://dev.inoculator.ai"
EMAIL = os.environ.get("INOCULATOR_EMAIL", "maita.leonida@signatureip.ai")
PASSWORD = os.environ.get("INOCULATOR_PASSWORD", "Mypassword2023")

MAX_WORKERS = 3          # parallel browser tabs/pages
MAX_RETRIES = 3          # retries per project on failure
POLL_INTERVAL_S = 30     # seconds between completion-check rounds
MAX_POLL_ROUNDS = 20     # give up after this many rounds (~10 min)
TRIGGER_WAIT_MS = 4000   # ms to wait after clicking Generate Design
PAGE_LOAD_WAIT_MS = 2000

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_filename = os.path.join(log_dir, f"rtl_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# Thread-safe Excel write lock
excel_lock = threading.Lock()


# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────
def login(page) -> bool:
    """Log in and handle OTP (assumed auto-filled in dev env)."""
    try:
        log.info("Navigating to login page...")
        page.goto(f"{BASE_URL}/login")
        page.fill('input[name="email"]', EMAIL)
        page.fill('input[name="password"]', PASSWORD)
        page.click('text="Request OTP"')
        page.wait_for_selector('input[name="loginToken"]', timeout=10_000)

        # Dev env: OTP is auto-filled — just wait briefly then submit
        log.info("Waiting for OTP to be auto-filled...")
        page.wait_for_timeout(3000)
        page.click('button[type="submit"]')
        page.wait_for_timeout(3000)

        # Confirm login succeeded
        if "/login" not in page.url:
            log.info("Login successful.")
            return True
        else:
            log.error("Login failed — still on login page.")
            return False
    except Exception as e:
        log.error(f"Login exception: {e}")
        return False


# ─────────────────────────────────────────────
# TRIGGER
# ─────────────────────────────────────────────
def trigger_generate_design(page, project_id: str, project_name: str) -> str:
    """Click Generate Design and return the createdAt timestamp."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log.info(f"[{project_name}] Trigger attempt {attempt}/{MAX_RETRIES}")
            page.goto(f"{BASE_URL}/projects/{project_id}")
            page.wait_for_timeout(PAGE_LOAD_WAIT_MS)

            page.click('button:has([data-testid="ConstructionIcon"])')
            page.wait_for_selector('button:has-text("Generate Design")', timeout=8000)
            page.click('button:has-text("Generate Design")')
            page.wait_for_timeout(TRIGGER_WAIT_MS)

            created_at = ""
            try:
                created_at = page.inner_text('div[data-field="createdAt"] p', timeout=5000)
            except Exception:
                log.warning(f"[{project_name}] Could not read createdAt after trigger.")

            log.info(f"[{project_name}] Triggered. createdAt={created_at!r}")
            return created_at

        except PlaywrightTimeoutError as e:
            log.warning(f"[{project_name}] Timeout on trigger attempt {attempt}: {e}")
        except Exception as e:
            log.warning(f"[{project_name}] Error on trigger attempt {attempt}: {e}")

        if attempt < MAX_RETRIES:
            time.sleep(5)

    log.error(f"[{project_name}] All trigger attempts failed.")
    return ""


# ─────────────────────────────────────────────
# CHECK COMPLETION
# ─────────────────────────────────────────────
def check_completion(page, project_id: str, project_name: str) -> tuple[str, str]:
    """
    Returns (updated_at, status) where status is 'Passed', 'Failed', or 'Pending'.
    """
    try:
        page.goto(f"{BASE_URL}/projects/{project_id}")
        page.click('button:has([data-testid="ConstructionIcon"])')
        page.wait_for_timeout(PAGE_LOAD_WAIT_MS)

        try:
            page.wait_for_selector('div[role="row"]', timeout=8000)
        except PlaywrightTimeoutError:
            log.warning(f"[{project_name}] No rows appeared.")
            return "", "Pending"

        all_rows = page.query_selector_all('div[role="row"]')
        log.info(f"[{project_name}] Found {len(all_rows)} row(s).")

        row = all_rows[1] if len(all_rows) > 1 else None
        if not row:
            log.warning(f"[{project_name}] No data row found.")
            return "", "Pending"

        # Read updatedAt
        updated_at = ""
        try:
            cell = row.query_selector('div[data-field="updatedAt"] p')
            updated_at = cell.inner_text() if cell else ""
        except Exception:
            pass

        # Check icons — wait briefly for CheckCircle to appear
        try:
            row.wait_for_selector('svg[data-testid="CheckCircleIcon"]', timeout=3000)
        except Exception:
            pass  # might already be failed

        icon_failed  = row.query_selector('svg[data-testid="HighlightOffIcon"]')
        icon_success = row.query_selector('svg[data-testid="CheckCircleIcon"]')
        icon_pending = row.query_selector('svg[data-testid="HourglassEmptyIcon"]')  # adjust testid if different

        if icon_success:
            status = "Passed"
        elif icon_failed:
            status = "Failed"
        elif icon_pending:
            status = "Pending"
        else:
            # No terminal icon yet — treat as still running
            status = "Pending"

        log.info(f"[{project_name}] updatedAt={updated_at!r} status={status}")
        return updated_at, status

    except Exception as e:
        log.error(f"[{project_name}] check_completion error: {e}")
        return "", "Pending"


# ─────────────────────────────────────────────
# PER-PROJECT WORKER
# ─────────────────────────────────────────────
def process_project(browser_context, idx: int, project_id: str, project_name: str, df: pd.DataFrame):
    """Full lifecycle for one project: trigger → poll until done → write result."""
    page = browser_context.new_page()
    try:
        # 1. Trigger
        created_at = trigger_generate_design(page, project_id, project_name)
        with excel_lock:
            df.at[idx, "started on"] = created_at

        # 2. Poll for completion
        for round_num in range(1, MAX_POLL_ROUNDS + 1):
            log.info(f"[{project_name}] Poll round {round_num}/{MAX_POLL_ROUNDS}")
            updated_at, status = check_completion(page, project_id, project_name)

            with excel_lock:
                df.at[idx, "completed on"] = updated_at
                df.at[idx, "STATUS"] = status

            if status in ("Passed", "Failed"):
                log.info(f"[{project_name}] Finished with status={status}")
                break

            if round_num < MAX_POLL_ROUNDS:
                log.info(f"[{project_name}] Still pending, waiting {POLL_INTERVAL_S}s...")
                time.sleep(POLL_INTERVAL_S)
        else:
            log.error(f"[{project_name}] Timed out waiting for completion.")
            with excel_lock:
                df.at[idx, "STATUS"] = "Timeout"

    finally:
        page.close()


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    log.info("=" * 60)
    log.info(f"RTL Automation run started at {datetime.now().isoformat()}")
    log.info(f"Excel: {EXCEL_PATH}")
    log.info("=" * 60)

    # Load Excel
    df = pd.read_excel(EXCEL_PATH)
    for col in ("started on", "completed on", "STATUS"):
        if col not in df.columns:
            df[col] = ""

    projects = [(idx, str(row["ID"]), str(row["NAME"])) for idx, row in df.iterrows()]
    log.info(f"Loaded {len(projects)} project(s) from Excel.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="msedge")

        # --- Login on a dedicated page ---
        auth_context = browser.new_context()
        auth_page = auth_context.new_page()
        if not login(auth_page):
            log.error("Login failed. Aborting run.")
            browser.close()
            return

        # Save auth state (cookies/session) so worker contexts share the session
        auth_state = auth_context.storage_state()
        auth_page.close()
        auth_context.close()

        # --- Run projects in parallel ---
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {}
            for idx, project_id, project_name in projects:
                worker_context = browser.new_context(storage_state=auth_state)
                future = executor.submit(
                    process_project,
                    worker_context,
                    idx,
                    project_id,
                    project_name,
                    df,
                )
                futures[future] = (project_name, worker_context)

            for future in as_completed(futures):
                project_name, ctx = futures[future]
                try:
                    future.result()
                except Exception as e:
                    log.error(f"[{project_name}] Unhandled worker error: {e}")
                finally:
                    ctx.close()

        browser.close()

    # --- Save results ---
    df.to_excel(EXCEL_PATH, index=False)
    log.info(f"Results written to {EXCEL_PATH}")

    # --- Summary ---
    passed  = (df["STATUS"] == "Passed").sum()
    failed  = (df["STATUS"] == "Failed").sum()
    timeout = (df["STATUS"] == "Timeout").sum()
    pending = (df["STATUS"] == "Pending").sum()
    log.info(f"Summary → Passed: {passed} | Failed: {failed} | Timeout: {timeout} | Pending: {pending}")
    log.info(f"Log saved to: {log_filename}")


if __name__ == "__main__":
    main()
