import pandas as pd
import time
from datetime import datetime

export_types = ['Encrypted', 'Obfuscated', 'Clean', 'All 3', 'Enc+Clean', 'Obs+Clean', 'Enc+Obs']

def wait_for_new_row(page, previous_created_ats, timeout=30):
    """Wait for a new row to appear in the export table"""
    start = time.time()
    while time.time() - start < timeout:
        all_rows = page.query_selector_all('div[role="row"]')
        for r in all_rows:
            created_at_cell = r.query_selector('div[data-field="createdAt"] p')
            if created_at_cell:
                created_at_val = created_at_cell.inner_text().strip()
                if created_at_val not in previous_created_ats:
                    return created_at_val
        time.sleep(1)
    return None

def trigger_export(page, project_name, export_type):
    """Trigger export for a specific type"""
    try:
        # Navigate to project
        page.goto("https://dev.inoculator.ai/projects")
        page.wait_for_selector(f'.MuiCard-root:has-text("{project_name}")', timeout=30000)
        page.click(f'.MuiCard-root:has-text("{project_name}")')
        page.wait_for_timeout(2000)
        
        # Go to export section
        page.click('button:has([data-testid="ImportExportIcon"])')
        page.wait_for_selector('button:has-text("Export Package")')
        page.wait_for_load_state('networkidle')
        
        # Collect current timestamps
        all_rows = page.query_selector_all('div[role="row"]')
        previous_created_ats = set()
        for r in all_rows:
            created_at_cell = r.query_selector('div[data-field="createdAt"] p')
            if created_at_cell:
                previous_created_ats.add(created_at_cell.inner_text().strip())
                
        # Select export type
        if export_type == 'Encrypted':
            page.get_by_label('Encrypted').check()
            page.get_by_label('Obfuscated').uncheck()
            page.get_by_label('Clean').uncheck()
        elif export_type == 'Obfuscated':
            page.get_by_label('Encrypted').uncheck()
            page.get_by_label('Obfuscated').check()
            page.get_by_label('Clean').uncheck()
        elif export_type == 'Clean':
            page.get_by_label('Encrypted').uncheck()
            page.get_by_label('Obfuscated').uncheck()
            page.get_by_label('Clean').check()
        elif export_type == 'All 3':
            page.get_by_label('Encrypted').check()
            page.get_by_label('Obfuscated').check()
            page.get_by_label('Clean').check()
        elif export_type == 'Enc+Clean':
            page.get_by_label('Encrypted').check()
            page.get_by_label('Obfuscated').uncheck()
            page.get_by_label('Clean').check()
        elif export_type == 'Obs+Clean':
            page.get_by_label('Encrypted').uncheck()
            page.get_by_label('Obfuscated').check()
            page.get_by_label('Clean').check()
        elif export_type == 'Enc+Obs':
            page.get_by_label('Encrypted').check()
            page.get_by_label('Obfuscated').check()
            page.get_by_label('Clean').uncheck()
            
        page.wait_for_timeout(2000)
        
        # Click export button
        page.wait_for_selector('button:has-text("Export Package"):enabled')
        page.get_by_role('button', name='Export Package').click()
        page.wait_for_timeout(2000)
        
        # Wait for new row and get timestamp
        new_created_at = wait_for_new_row(page, previous_created_ats)
        return new_created_at
        
    except Exception as e:
        print(f"Export trigger failed for {project_name}, {export_type}: {e}")
        return None

def check_export_completion(page, project_name, export_type, created_at_val):
    """Check completion status of export"""
    try:
        # Navigate to project
        page.goto("https://dev.inoculator.ai/projects")
        page.wait_for_selector(f'.MuiCard-root:has-text("{project_name}")', timeout=10000)
        page.click(f'.MuiCard-root:has-text("{project_name}")')
        page.wait_for_timeout(2000)
        
        # Go to export section
        page.click('button:has([data-testid="ImportExportIcon"])')
        page.wait_for_timeout(2000)
        
        # Find the specific row by timestamp
        all_rows = page.query_selector_all('div[role="row"]')
        target_row = None
        
        for r in all_rows:
            created_at_cell = r.query_selector('div[data-field="createdAt"] p')
            if created_at_cell and created_at_cell.inner_text().strip() == created_at_val.strip():
                target_row = r
                break
                
        if not target_row:
            return "Pending"
            
        # Check status
        status_cell = target_row.query_selector('div[data-field="status"]')
        if not status_cell:
            return "Pending"
            
        if status_cell.query_selector('svg[data-testid="CheckCircleIcon"], svg.css-bv3s9b'):
            return "Passed"
        if status_cell.query_selector('svg[data-testid="HighlightOffIcon"], svg.css-mfr23f'):
            return "Failed"
        if status_cell.query_selector('svg.MuiCircularProgress-svg, svg.css-13o7eu2'):
            return "Processing"
            
        return "Pending"
        
    except Exception as e:
        print(f"Export check failed for {project_name}, {export_type}: {e}")
        return "Failed"

def run_export_rtl(page, projects):
    """Run RTL export for all projects"""
    print("Starting RTL Export phase...")
    
    # Initialize DataFrame for export results
    export_data = []
    
    # Initialize data structure
    for project in projects:
        project_data = {
            'ID': project['ID'],
            'NAME': project['NAME']
        }
        
        # Add export type columns
        for export_type in export_types:
            project_data[export_type] = ""
            project_data[f'createdAt_{export_type}'] = ""
            
        export_data.append(project_data)
        
    # Create DataFrame
    export_df = pd.DataFrame(export_data)
    
    # First pass: trigger exports
    for idx, project in enumerate(projects):
        project_name = project['NAME']
        print(f"Triggering exports for: {project_name}")
        
        for export_type in export_types:
            print(f"  Triggering {export_type} export...")
            created_at = trigger_export(page, project_name, export_type)
            if created_at:
                export_df.at[idx, f'createdAt_{export_type}'] = created_at
                print(f"  Recorded timestamp for {export_type}: {created_at}")
            else:
                print(f"  Failed to trigger {export_type} export")
                
    # Wait 20 minutes before checking completion
    print("Waiting 20 minutes before checking export completion...")
    time.sleep(1200)  # 20 minutes
    
    # Second pass: check completion
    max_retries = 6
    retry_count = 0
    
    while retry_count < max_retries:
        all_exports_done = True
        retry_count += 1
        
        # Find pending exports
        pending_exports = []
        for idx, project in enumerate(projects):
            project_name = project['NAME']
            for export_type in export_types:
                created_at_val = export_df.at[idx, f'createdAt_{export_type}']
                current_status = export_df.at[idx, export_type]
                if created_at_val and current_status not in ["Passed", "Failed"]:
                    pending_exports.append((idx, project_name, export_type, created_at_val))
                    
        if not pending_exports:
            print("No pending exports to check!")
            break
            
        print(f"Found {len(pending_exports)} exports still pending")
        
        # Check each pending export
        visited_projects = set()
        for idx, project_name, export_type, created_at_val in pending_exports:
            if project_name not in visited_projects:
                print(f"Checking exports for: {project_name}")
                visited_projects.add(project_name)
                
            status = check_export_completion(page, project_name, export_type, created_at_val)
            old_status = export_df.at[idx, export_type]
            export_df.at[idx, export_type] = status
            print(f"  {export_type}: {old_status} -> {status}")
            
            if status in ["Processing", "Pending"]:
                all_exports_done = False
                
        if all_exports_done:
            print("All exports have completed processing!")
            break
            
        if retry_count >= max_retries:
            print(f"Reached maximum retries ({max_retries}). Marking incomplete exports.")
            for idx in range(len(projects)):
                for export_type in export_types:
                    if export_df.at[idx, export_type] in ["Pending", "Processing"]:
                        export_df.at[idx, export_type] = "Incomplete"
            break
            
        print(f"Retry {retry_count}/{max_retries}. Waiting 5 minutes...")
        time.sleep(300)  # 5 minutes
        
    print("RTL Export phase completed!")
    return export_df
  