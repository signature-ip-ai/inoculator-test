import pandas as pd
import time
from datetime import datetime

def trigger_simulation(page, project_id):
    """Trigger simulation for a project"""
    try:
        project_url = f"https://dev.inoculator.ai/projects/{project_id}"
        page.goto(project_url)
        page.wait_for_timeout(2000)
        page.click('button:has([data-testid="DvrIcon"])')
        page.wait_for_selector('button:has-text("New")')
        page.click('button:has-text("New")')
        page.wait_for_timeout(4000)
        
        # Get created_at timestamp
        created_at = ""
        try:
            created_at = page.inner_text('div[data-field="createdAt"] p')
        except Exception:
            created_at = ""
        return created_at
    except Exception as e:
        print(f"Simulation trigger failed for project ID {project_id}: {e}")
        return ""

def check_simulation_completion(page, project_id):
    """Check completion status of simulation"""
    try:
        project_url = f"https://dev.inoculator.ai/projects/{project_id}"
        page.goto(project_url)
        page.click('button:has([data-testid="DvrIcon"])')
        page.wait_for_timeout(2000)
        
        all_rows = page.query_selector_all('div[role="row"]')
        row = all_rows[1] if len(all_rows) > 1 else None
        
        # Get updated_at timestamp
        updated_at = ""
        if row:
            updated_at_cell = row.query_selector('div[data-field="updatedAt"] p')
            if updated_at_cell:
                updated_at = updated_at_cell.inner_text()
                
        # Check status
        status = "Pending"
        if row:
            status_cell = row.query_selector('div[data-field="status"]')
            if status_cell:
                if status_cell.query_selector('svg[data-testid="CheckCircleIcon"]'):
                    status = "Passed"
                elif status_cell.query_selector('svg[data-testid="HighlightOffIcon"]'):
                    status = "Failed"
                elif status_cell.query_selector('svg.MuiCircularProgress-svg'):
                    status = "Processing"
                else:
                    status = "Pending"
                    
        return updated_at, status
    except Exception as e:
        print(f"Simulation check failed for project ID {project_id}: {e}")
        return "", "Failed"

def run_simulate_rtl(page, projects):
    """Run RTL simulation for all projects"""
    print("Starting RTL Simulation phase...")
    
    # Initialize DataFrame for simulate results
    simulate_data = []
    
    # First pass: trigger simulation
    for project in projects:
        project_id = project['ID']
        project_name = project['NAME']
        print(f"Triggering simulation for: {project_name} (ID: {project_id})")
        
        created_at = trigger_simulation(page, project_id)
        
        simulate_data.append({
            'ID': project_id,
            'NAME': project_name,
            'STATUS': '',
            'started on': created_at,
            'completed on': ''
        })
        
        page.goto("https://dev.inoculator.ai/projects")
        page.wait_for_timeout(1000)
        
    # Create DataFrame
    simulate_df = pd.DataFrame(simulate_data)
    
    # Wait 15 minutes before checking completion
    print("Waiting 15 minutes before checking simulation completion...")
    time.sleep(900)  # 15 minutes
    
    # Second pass: check completion
    max_retries = 6
    retry_count = 0
    
    while retry_count < max_retries:
        all_done = True
        
        for idx, project in enumerate(projects):
            project_id = project['ID']
            project_name = project['NAME']
            print(f"Checking simulation completion for: {project_name}")
            
            updated_at, status = check_simulation_completion(page, project_id)
            if not updated_at or status not in ["Passed", "Failed"]:
                all_done = False
                
            simulate_df.at[idx, 'completed on'] = updated_at
            simulate_df.at[idx, 'STATUS'] = status
            page.goto("https://dev.inoculator.ai/projects")
            page.wait_for_timeout(1000)
            
        if all_done:
            break
            
        retry_count += 1
        print(f"Some simulations not completed yet. Retry {retry_count}/{max_retries}")
        time.sleep(300)  # Wait 5 minutes before next check
        
    # Mark incomplete simulations
    if not all_done:
        for idx in range(len(projects)):
            if simulate_df.at[idx, 'STATUS'] not in ["Passed", "Failed"]:
                simulate_df.at[idx, 'STATUS'] = "Incomplete"
                
    print("RTL Simulation phase completed!")
    return simulate_df