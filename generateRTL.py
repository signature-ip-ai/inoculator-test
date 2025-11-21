import pandas as pd
from playwright.sync_api import sync_playwright
import time
from datetime import datetime

def trigger_generate_design(page, project_id):
    """Trigger RTL generation for a project"""
    try:
        project_url = f"https://dev.inoculator.ai/projects/{project_id}"
        page.goto(project_url)
        page.wait_for_timeout(2000)
        page.click('button:has([data-testid="ConstructionIcon"])')
        page.wait_for_selector('button:has-text("Generate Design")')
        page.click('button:has-text("Generate Design")')
        page.wait_for_timeout(4000)
        
        # Get created_at timestamp
        created_at = ""
        try:
            created_at = page.inner_text('div[data-field="createdAt"] p')
        except Exception:
            created_at = ""
        return created_at
    except Exception as e:
        print(f"Generate trigger failed for project ID {project_id}: {e}")
        return ""

def trigger_generate_design_with_CAM(page, project_id):
    """Trigger RTL generation with CAM for a project"""
    try:
        project_url = f"https://dev.inoculator.ai/projects/{project_id}"
        page.goto(project_url)
        page.wait_for_timeout(2000)
        page.click('button:has([data-testid="ConstructionIcon"])')
        page.wait_for_timeout(2000)
        
        # Click the CAM checkbox
        try:
            page.wait_for_selector('input.PrivateSwitchBase-input[type="checkbox"]', timeout=5000)
            page.click('input.PrivateSwitchBase-input[type="checkbox"]')
            page.wait_for_timeout(1000)
        except Exception as e:
            print(f"Failed to click CAM checkbox for project ID {project_id}: {e}")
            return ""
        
        page.wait_for_selector('button:has-text("Generate Design")')
        page.click('button:has-text("Generate Design")')
        page.wait_for_timeout(4000)
        
        # Get created_at timestamp
        created_at = ""
        try:
            created_at = page.inner_text('div[data-field="createdAt"] p')
        except Exception:
            created_at = ""
        return created_at
    except Exception as e:
        print(f"Generate trigger with CAM failed for project ID {project_id}: {e}")
        return ""

def check_generate_completion(page, project_id):
    """Check completion status of RTL generation"""
    try:
        project_url = f"https://dev.inoculator.ai/projects/{project_id}"
        page.goto(project_url)
        page.click('button:has([data-testid="ConstructionIcon"])')
        page.wait_for_timeout(2000)
        
        # Wait for rows to appear
        try:
            page.wait_for_selector('div[role="row"]', timeout=5000)
        except Exception as e:
            print(f"No rows appeared: {e}")
            
        all_rows = page.query_selector_all('div[role="row"]')
        row = all_rows[1] if len(all_rows) > 1 else None
        
        # Get updated_at timestamp
        updated_at = ""
        if row:
            updated_at_cell = row.query_selector('div[data-field="updatedAt"] p')
            if updated_at_cell:
                updated_at = updated_at_cell.inner_text()
                
        # Check status
        status = "Failed"
        if row:
            icon_failed = row.query_selector('svg[data-testid="HighlightOffIcon"]')
            icon_success = row.query_selector('svg[data-testid="CheckCircleIcon"]')
            
            if icon_failed:
                status = "Failed"
            elif icon_success:
                status = "Passed"
            else:
                status = "Pending"
                
        return updated_at, status
    except Exception as e:
        print(f"Generate check failed for project ID {project_id}: {e}")
        return "", "Failed"

def run_generate_rtl(page, projects):
    """Run RTL generation for all projects"""
    print("Starting RTL Generation phase...")
    
    # Initialize DataFrame for generate results
    generate_data = []
    
    # First pass: trigger generation
    for project in projects:
        project_id = project['ID']
        project_name = project['NAME']
        print(f"Triggering generation for: {project_name} (ID: {project_id})")
        
        created_at = trigger_generate_design(page, project_id)
        
        generate_data.append({
            'ID': project_id,
            'NAME': project_name,
            'STATUS': '',
            'started on': created_at,
            'completed on': ''
        })
        
        page.wait_for_timeout(1000)
        
    # Create DataFrame
    generate_df = pd.DataFrame(generate_data)
    
    # Second pass: check completion
    while True:
        all_done = True
        
        for idx, project in enumerate(projects):
            project_id = project['ID']
            project_name = project['NAME']
            print(f"Checking generation completion for: {project_name}")
            
            updated_at, status = check_generate_completion(page, project_id)
            if not updated_at or status not in ["Passed", "Failed"]:
                all_done = False
                
            generate_df.at[idx, 'completed on'] = updated_at
            generate_df.at[idx, 'STATUS'] = status
            page.wait_for_timeout(1000)
            
        if all_done:
            break
        print("Some generations not completed yet, repeating check...")
        time.sleep(30)  # Wait 30 seconds before next check
        
    print("RTL Generation phase completed!")
    return generate_df

def run_generate_rtl_with_CAM(page, projects):
    """Run RTL generation with CAM for all projects"""
    print("Starting RTL Generation with CAM phase...")
    
    # Initialize DataFrame for generate results
    generate_data = []
    
    # First pass: trigger generation with CAM
    for project in projects:
        project_id = project['ID']
        project_name = project['NAME']
        print(f"Triggering generation with CAM for: {project_name} (ID: {project_id})")
        
        created_at = trigger_generate_design_with_CAM(page, project_id)
        
        generate_data.append({
            'ID': project_id,
            'NAME': project_name,
            'STATUS': '',
            'started on': created_at,
            'completed on': ''
        })
        
        page.wait_for_timeout(1000)
        
    # Create DataFrame
    generate_df = pd.DataFrame(generate_data)
    
    # Second pass: check completion
    while True:
        all_done = True
        
        for idx, project in enumerate(projects):
            project_id = project['ID']
            project_name = project['NAME']
            print(f"Checking generation completion with CAM for: {project_name}")
            
            updated_at, status = check_generate_completion(page, project_id)
            if not updated_at or status not in ["Passed", "Failed"]:
                all_done = False
                
            generate_df.at[idx, 'completed on'] = updated_at
            generate_df.at[idx, 'STATUS'] = status
            page.wait_for_timeout(1000)
            
        if all_done:
            break
        print("Some generations with CAM not completed yet, repeating check...")
        time.sleep(30)  # Wait 30 seconds before next check
        
    print("RTL Generation with CAM phase completed!")
    return generate_df

def login_to_inoculator():
    """Login to the inoculator application"""
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False, channel="msedge")
    context = browser.new_context()
    page = context.new_page()
    
    try:
        # --- Login steps ---
        print("Starting login process...")
        page.goto("https://dev.inoculator.ai/login")
        page.fill('input[name="email"]', 'susmita.dash@marqueesemi.com')
        page.fill('input[name="password"]', 'Dash@1234')
        page.click('text="Request OTP"')
        
        # For admin users, login completes automatically after clicking "Request OTP"
        # Wait for navigation away from login page to confirm login success
        page.wait_for_timeout(7000)
        
        print("Login successful! You are now logged into Inoculator.")
        return browser, page
        
    except Exception as e:
        print(f"Login failed: {str(e)}")
        browser.close()
        return None, None

def main():
    """Standalone function to run generateRTL with Excel file"""
    # Path to your Excel file
    excel_path = r"C:\Users\0018\Documents\generateRTLtest.xlsx"
    
    # Read the Excel file
    df = pd.read_excel(excel_path)
    
    # Ensure the new columns exist
    if 'started on' not in df.columns:
        df['started on'] = ""
    if 'completed on' not in df.columns:
        df['completed on'] = ""
    if 'STATUS' not in df.columns:
        df['STATUS'] = ""
    if 'started on CAM' not in df.columns:
        df['started on CAM'] = ""
    if 'completed on CAM' not in df.columns:
        df['completed on CAM'] = ""
    if 'STATUS CAM' not in df.columns:
        df['STATUS CAM'] = ""
    
    # Login to inoculator
    browser, page = login_to_inoculator()
    
    if not browser or not page:
        print("Cannot proceed with tests due to login failure")
        return
    
    try:
        # Convert DataFrame to projects list
        projects = []
        for idx, row in df.iterrows():
            projects.append({
                'ID': row['ID'],
                'NAME': row['NAME']
            })

        # Run generation without CAM
        print("\n" + "="*50)
        print("PHASE 1: RTL Generation WITHOUT CAM")
        print("="*50 + "\n")
        generate_df = run_generate_rtl(page, projects)
        
        # Update original DataFrame with results
        for idx, row in generate_df.iterrows():
            df.at[idx, 'started on'] = row['started on']
            df.at[idx, 'completed on'] = row['completed on']
            df.at[idx, 'STATUS'] = row['STATUS']

        # Run generation with CAM
        print("\n" + "="*50)
        print("PHASE 2: RTL Generation WITH CAM")
        print("="*50 + "\n")
        generate_df_CAM = run_generate_rtl_with_CAM(page, projects)
        
        # Update original DataFrame with CAM results
        for idx, row in generate_df_CAM.iterrows():
            df.at[idx, 'started on CAM'] = row['started on']
            df.at[idx, 'completed on CAM'] = row['completed on']
            df.at[idx, 'STATUS CAM'] = row['STATUS']

        # Save results
        df.to_excel(excel_path, index=False)
        print("\nResults written to Excel.")
        
    finally:
        # Keep browser open for manual inspection
        input("Press Enter to close the browser...")
        browser.close()

if __name__ == "__main__":
    main()

    