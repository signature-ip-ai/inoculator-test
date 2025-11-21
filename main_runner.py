#!/usr/bin/env python3
"""
Consolidated Inoculator RTL Automation Master Script
===================================================

This script consolidates all three RTL automation operations:
1. Generate RTL designs
2. Simulate RTL designs  
3. Export RTL packages

All operations use a single Excel file for output with the following structure:

Generate/Simulate Results:
- ID: Project ID
- NAME: Project Name
- STATUS: Passed/Failed/Pending
- started on: When operation started
- completed on: When operation completed

Export Results:
- ID: Project ID
- NAME: Project Name
- Encrypted, Obfuscated, Clean, All 3, Enc+Clean, Obs+Clean, Enc+Obs: Export statuses
- createdAt_Encrypted, createdAt_Obfuscated, etc.: Creation timestamps

Usage:
    python main_runner.py [options]

Options:
    --generate-only      Run only RTL generation
    --simulate-only      Run only RTL simulation
    --export-only        Run only RTL export
    --skip-generate      Skip generation, run simulate + export
    --skip-simulate      Skip simulation, run generate + export
    --skip-export        Skip export, run generate + simulate
    --help               Show this help message
"""

from playwright.sync_api import sync_playwright
import pandas as pd
from datetime import datetime
import time
import os
import argparse
import sys

# Import functions from individual modules
from generateRTL import run_generate_rtl as generate_rtl_func, run_generate_rtl_with_CAM as generate_rtl_CAM_func
from simulateRTL import run_simulate_rtl as simulate_rtl_func
from exportRTL import run_export_rtl as export_rtl_func, export_types

class InoculatorMasterRunner:
    def __init__(self, headless=True):
        self.start_time = datetime.now()
        self.headless = headless
        
        # Define projects to test (you can modify this list)
        self.projects = [
            # {"ID": "0b966ea3-ab3e-4e16-8de8-10e92b7896ab", "NAME": "New_Project_4"},
            # {"ID": "6bc228aa-fcf9-452c-b670-5f917610ff04", "NAME": "New_Project_6A"},
            # {"ID": "18d2687a-e343-4a2b-b50f-109161d10798", "NAME": "with_bridge"},
            # {"ID": "0b82eba0-d45b-432a-993f-0b189c2d564c", "NAME": "New_Project_5"},
            # {"ID": "6889fb83-6b9a-49f0-9e32-5dd87cea5fb2", "NAME": "CA_simulation"},
            # {"ID": "d2bbbd93-391b-4c38-9c8e-e7e956f287b8", "NAME": "with_virtual_device_sram_subtopology"},
            {"ID": "0bce4ca1-e5c2-4fc8-b404-e9000efb6a86", "NAME": "exclusiveaccess_aligned_address"}
        ]
        
        # Export types for RTL export
        self.export_types = export_types
        
        # Initialize DataFrames for each operation
        self.generate_df = None
        self.simulate_df = None
        self.export_df = None
        
    def log(self, message, level="INFO"):
        """Log messages with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def login_to_inoculator(self):
        """Login to the inoculator application - centralized login"""
        playwright = sync_playwright().start()
        
        # Configure browser launch options for headless mode
        browser = playwright.chromium.launch(headless=self.headless)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            # --- Login steps ---
            self.log("Starting centralized login process...")
            page.goto("https://dev.inoculator.ai/login")
            page.fill('input[name="email"]', 'susmita.dash@marqueesemi.com')
            page.fill('input[name="password"]', 'Put your password here') # Replace with your password
            page.click('text="Request OTP"')
            
            # For admin users, login completes automatically after clicking "Request OTP"
            # Wait for navigation away from login page to confirm login success
            page.wait_for_timeout(7000)
            
            self.log("Centralized login successful! You are now logged into Inoculator.")
            return browser, page
            
        except Exception as e:
            self.log(f"Login failed: {str(e)}", "ERROR")
            browser.close()
            return None, None
            
    def save_results_to_excel(self):
        """Save all results to Excel file with multiple sheets"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"inoculator_test_results_{timestamp}.xlsx"
            
            # Debug: Check what DataFrames we have
            self.log(f"Debug: generate_df is {'None' if self.generate_df is None else 'Present'}")
            self.log(f"Debug: simulate_df is {'None' if self.simulate_df is None else 'Present'}")
            self.log(f"Debug: export_df is {'None' if self.export_df is None else 'Present'}")
            
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                if self.generate_df is not None:
                    self.log("Saving GenerateRTL sheet...")
                    self.generate_df.to_excel(writer, sheet_name='GenerateRTL', index=False)
                    
                if self.simulate_df is not None:
                    self.log("Saving SimulateRTL sheet...")
                    self.simulate_df.to_excel(writer, sheet_name='SimulateRTL', index=False)
                    
                if self.export_df is not None:
                    self.log("Saving ExportRTL sheet...")
                    self.export_df.to_excel(writer, sheet_name='ExportRTL', index=False)
                    
            self.log(f"Test results saved to {filename}")
            return filename
            
        except Exception as e:
            self.log(f"Failed to save test results: {str(e)}", "ERROR")
            return None
            
    # ==================== GENERATE RTL FUNCTIONS ====================
    
    def run_generate_rtl(self, page):
        """Run RTL generation for all projects (both without and with CAM)"""
        self.log("Starting RTL Generation phase...")
        
        try:
            # Phase 1: Generate without CAM
            self.log("="*50)
            self.log("PHASE 1: RTL Generation WITHOUT CAM")
            self.log("="*50)
            generate_df = generate_rtl_func(page, self.projects)
            self.log("RTL Generation without CAM phase completed!")
            
            # Phase 2: Generate with CAM
            self.log("="*50)
            self.log("PHASE 2: RTL Generation WITH CAM")
            self.log("="*50)
            generate_df_CAM = generate_rtl_CAM_func(page, self.projects)
            self.log("RTL Generation with CAM phase completed!")
            
            # Combine results into a single DataFrame
            # Merge the CAM results into the main DataFrame
            if generate_df is not None and generate_df_CAM is not None:
                # Add CAM columns to the main DataFrame
                generate_df['started on CAM'] = generate_df_CAM['started on']
                generate_df['completed on CAM'] = generate_df_CAM['completed on']
                generate_df['STATUS CAM'] = generate_df_CAM['STATUS']
                self.generate_df = generate_df
            elif generate_df is not None:
                self.generate_df = generate_df
            else:
                self.generate_df = generate_df_CAM
            
            self.log("RTL Generation phase (both without and with CAM) completed!")
            return True
        except Exception as e:
            self.log(f"RTL Generation failed with error: {str(e)}", "ERROR")
            # Create empty DataFrame to ensure it gets saved
            self.generate_df = pd.DataFrame([{
                'ID': project['ID'], 
                'NAME': project['NAME'], 
                'STATUS': 'Error', 
                'started on': '', 
                'completed on': '',
                'started on CAM': '',
                'completed on CAM': '',
                'STATUS CAM': 'Error'
            } for project in self.projects])
            return False
        
    # ==================== SIMULATE RTL FUNCTIONS ====================
    
    def run_simulate_rtl(self, page):
        """Run RTL simulation for all projects"""
        self.log("Starting RTL Simulation phase...")
        
        try:
            # Call the imported function
            self.simulate_df = simulate_rtl_func(page, self.projects)
            self.log("RTL Simulation phase completed!")
            return True
        except Exception as e:
            self.log(f"RTL Simulation failed with error: {str(e)}", "ERROR")
            # Create empty DataFrame to ensure it gets saved
            self.simulate_df = pd.DataFrame([{
                'ID': project['ID'], 
                'NAME': project['NAME'], 
                'STATUS': 'Error', 
                'started on': '', 
                'completed on': ''
            } for project in self.projects])
            return False
        
    # ==================== EXPORT RTL FUNCTIONS ====================
    
    def run_export_rtl(self, page):
        """Run RTL export for all projects"""
        self.log("Starting RTL Export phase...")
        
        try:
            # Call the imported function
            self.export_df = export_rtl_func(page, self.projects)
            self.log("RTL Export phase completed!")
            return True
        except Exception as e:
            self.log(f"RTL Export failed with error: {str(e)}", "ERROR")
            # Create empty DataFrame to ensure it gets saved
            export_data = []
            for project in self.projects:
                project_data = {
                    'ID': project['ID'],
                    'NAME': project['NAME']
                }
                # Add export type columns
                for export_type in self.export_types:
                    project_data[export_type] = "Error"
                    project_data[f'createdAt_{export_type}'] = ""
                export_data.append(project_data)
            self.export_df = pd.DataFrame(export_data)
            return False
        
    # ==================== MAIN EXECUTION ====================
        
    def run_all_tests(self):
        """Run all three phases: Generate, Simulate, Export with centralized login"""
        self.log("Starting complete RTL automation pipeline with centralized login...")
        
        # Single login for all phases
        browser, page = self.login_to_inoculator()
        
        if not browser or not page:
            self.log("Cannot proceed with tests due to login failure", "ERROR")
            return False
            
        try:
            # Phase 1: Generate RTL
            generate_success = self.run_generate_rtl(page)
            if not generate_success:
                self.log("RTL Generation failed. Continuing with other phases.", "WARNING")
                
            self.log("Waiting 2 minutes before starting simulation...")
            time.sleep(120)
            
            # Phase 2: Simulate RTL
            simulate_success = self.run_simulate_rtl(page)
            if not simulate_success:
                self.log("RTL Simulation failed. Continuing with export phase.", "WARNING")
                
            self.log("Waiting 2 minutes before starting export...")
            time.sleep(120)
            
            # Phase 3: Export RTL
            export_success = self.run_export_rtl(page)
            if not export_success:
                self.log("RTL Export failed.", "WARNING")
                
            # Check if any phase succeeded
            if generate_success or simulate_success or export_success:
                self.log("Pipeline completed with some phases successful!", "SUCCESS")
                return True
            else:
                self.log("All phases failed.", "ERROR")
                return False
            
        except Exception as e:
            self.log(f"Test execution failed: {str(e)}", "ERROR")
            return False
        finally:
            # Save results
            filename = self.save_results_to_excel()
            if filename:
                self.log(f"Results saved to: {filename}")
            
            # Close browser automatically
            browser.close()
            
    def print_summary(self):
        """Print execution summary"""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        print("\n" + "="*80)
        print("EXECUTION SUMMARY")
        print("="*80)
        print(f"Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Duration: {duration}")
        print(f"Projects Processed: {len(self.projects)}")
        
        if self.generate_df is not None:
            generate_passed = len(self.generate_df[self.generate_df['STATUS'] == 'Passed'])
            generate_failed = len(self.generate_df[self.generate_df['STATUS'] == 'Failed'])
            print(f"Generate Results: {generate_passed} passed, {generate_failed} failed")
            
        if self.simulate_df is not None:
            simulate_passed = len(self.simulate_df[self.simulate_df['STATUS'] == 'Passed'])
            simulate_failed = len(self.simulate_df[self.simulate_df['STATUS'] == 'Failed'])
            print(f"Simulate Results: {simulate_passed} passed, {simulate_failed} failed")
            
        if self.export_df is not None:
            print("Export Results:")
            for export_type in self.export_types:
                if export_type in self.export_df.columns:
                    passed = len(self.export_df[self.export_df[export_type] == 'Passed'])
                    failed = len(self.export_df[self.export_df[export_type] == 'Failed'])
                    print(f"  {export_type}: {passed} passed, {failed} failed")
                    
        print("="*80)

def main():
    parser = argparse.ArgumentParser(
        description="Consolidated Inoculator RTL Automation Master Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main_runner.py                    # Run all phases in headless mode (default)
  python main_runner.py --no-headless     # Run with visible browser (for debugging)
  python main_runner.py --generate-only   # Run only generation
  python main_runner.py --simulate-only   # Run only simulation
  python main_runner.py --export-only     # Run only export
  python main_runner.py --skip-generate    # Skip generation
        """
    )
    
    # Single phase options
    single_group = parser.add_mutually_exclusive_group()
    single_group.add_argument('--generate-only', action='store_true',
                            help='Run only RTL generation')
    single_group.add_argument('--simulate-only', action='store_true',
                            help='Run only RTL simulation')
    single_group.add_argument('--export-only', action='store_true',
                            help='Run only RTL export')
    
    # Skip options
    skip_group = parser.add_mutually_exclusive_group()
    skip_group.add_argument('--skip-generate', action='store_true',
                           help='Skip generation, run simulate + export')
    skip_group.add_argument('--skip-simulate', action='store_true',
                           help='Skip simulation, run generate + export')
    skip_group.add_argument('--skip-export', action='store_true',
                           help='Skip export, run generate + simulate')
    
    # Headless mode option
    parser.add_argument('--no-headless', dest='headless', action='store_false', default=True,
                       help='Run browser in visible mode (for debugging, default: headless)')
    
    args = parser.parse_args()
    
    # Headless mode: defaults to True, use --no-headless to disable
    # Can also be set via HEADLESS environment variable
    headless_mode = args.headless
    if os.getenv('HEADLESS') and args.headless:  # Only override if not explicitly set via --no-headless
        headless_mode = os.getenv('HEADLESS').lower() == 'true'
    
    runner = InoculatorMasterRunner(headless=headless_mode)
    
    try:
        success = False
        
        if args.generate_only:
            browser, page = runner.login_to_inoculator()
            if browser and page:
                success = runner.run_generate_rtl(page)
                runner.save_results_to_excel()
                browser.close()
        elif args.simulate_only:
            browser, page = runner.login_to_inoculator()
            if browser and page:
                success = runner.run_simulate_rtl(page)
                runner.save_results_to_excel()
                browser.close()
        elif args.export_only:
            browser, page = runner.login_to_inoculator()
            if browser and page:
                success = runner.run_export_rtl(page)
                runner.save_results_to_excel()
                browser.close()
        elif args.skip_generate:
            runner.log("Skipping RTL Generation...")
            browser, page = runner.login_to_inoculator()
            if browser and page:
                success = runner.run_simulate_rtl(page) and runner.run_export_rtl(page)
                runner.save_results_to_excel()
                browser.close()
        elif args.skip_simulate:
            browser, page = runner.login_to_inoculator()
            if browser and page:
                success = runner.run_generate_rtl(page)
                if success:
                    success = runner.run_export_rtl(page)
                runner.save_results_to_excel()
                browser.close()
        elif args.skip_export:
            browser, page = runner.login_to_inoculator()
            if browser and page:
                success = runner.run_generate_rtl(page)
                if success:
                    success = runner.run_simulate_rtl(page)
                runner.save_results_to_excel()
                browser.close()
        else:
            # Run all phases by default with centralized login
            success = runner.run_all_tests()
            
        runner.print_summary()
        
        if success:
            runner.log("Master runner completed successfully!", "SUCCESS")
            sys.exit(0)
        else:
            runner.log("Master runner completed with errors.", "ERROR")
            sys.exit(1)
            
    except KeyboardInterrupt:
        runner.log("Master runner interrupted by user.", "WARNING")
        runner.print_summary()
        sys.exit(1)
    except Exception as e:
        runner.log(f"Unexpected error: {str(e)}", "ERROR")
        runner.print_summary()
        sys.exit(1)

if __name__ == "__main__":
    main()