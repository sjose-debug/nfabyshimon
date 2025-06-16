import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pathlib import Path
import time
import streamlit as st
import glob

# Load environment variables
load_dotenv()

USERNAME = os.getenv("MORNINGSTAR_USERNAME")
PASSWORD = os.getenv("MORNINGSTAR_PASSWORD")

if not USERNAME or not PASSWORD:
    try:
        USERNAME = st.secrets["MORNINGSTAR_USERNAME"]
        PASSWORD = st.secrets["MORNINGSTAR_PASSWORD"]
    except:
        # For Replit, also check os.environ directly
        USERNAME = os.environ.get("MORNINGSTAR_USERNAME")
        PASSWORD = os.environ.get("MORNINGSTAR_PASSWORD")

# Your XPATHS dictionary remains the same
XPATHS = {
    "overview_tab":        "//span[text()='Overview']",
    "mer":                 "//div[@class='sal-dp-pair'][.//div[@class='sal-dp-name' and normalize-space(text())='Total Cost Ratio (Prospective)']]//div[@class='sal-dp-value']",
    "performance":         "//div[@class='sal-dp-pair'][.//div[@class='sal-dp-name' and normalize-space(text())='1 Yr Return']]//div[@class='sal-dp-value']",
    "fund_profile":        "//div[@class='sal-mip-strategy-content']//div[@class='sal-mip-strategy__body']",
}

def get_driver():
    """Modified get_driver for Replit compatibility"""
    opts = Options()
    
    # Essential options
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-features=NetworkService")
    opts.add_argument("--window-size=1920x1080")
    opts.add_argument("--disable-features=VizDisplayCompositor")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-images")
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option('useAutomationExtension', False)
    
    # Check if running on Replit
    if os.environ.get('REPL_ID'):
        # Find Chrome binary on Replit
        chrome_bins = glob.glob("/nix/store/*/bin/chromium")
        if chrome_bins:
            opts.binary_location = chrome_bins[0]
        
        # Find chromedriver on Replit
        chromedrivers = glob.glob("/nix/store/*/bin/chromedriver")
        if chromedrivers:
            service = Service(chromedrivers[0])
            driver = webdriver.Chrome(service=service, options=opts)
        else:
            driver = webdriver.Chrome(options=opts)
    else:
        # Your existing local setup
        chrome_binaries = [
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/usr/bin/chrome",
            "/usr/bin/google-chrome",
        ]
        
        for binary in chrome_binaries:
            if os.path.exists(binary):
                opts.binary_location = binary
                break
        
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from webdriver_manager.core.os_manager import ChromeType
            
            try:
                service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
            except:
                service = Service(ChromeDriverManager().install())
                
            driver = webdriver.Chrome(service=service, options=opts)
        except Exception as e:
            print(f"Error with webdriver_manager: {e}")
            driver = webdriver.Chrome(options=opts)
    
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(10)
    return driver

def dismiss_popups(driver):
    """Dismiss subscription and other popups"""
    try:
        # Multiple methods to ensure popup is dismissed
        driver.execute_script("""
            // Remove subscription notification
            var sub = document.getElementById('subscription-notification');
            if(sub) sub.remove();
            
            // Remove any modal backdrops
            var backdrops = document.querySelectorAll('.modal-backdrop, .popup-overlay, .overlay');
            backdrops.forEach(function(el) { el.remove(); });
            
            // Close any modals
            var modals = document.querySelectorAll('.modal, .popup, [role="dialog"]');
            modals.forEach(function(el) { 
                el.style.display = 'none';
                el.remove();
            });
            
            // Remove any divs that might be blocking
            var blockers = document.querySelectorAll('div[style*="position: fixed"], div[style*="position: absolute"]');
            blockers.forEach(function(el) {
                if(el.style.zIndex && parseInt(el.style.zIndex) > 1000) {
                    el.remove();
                }
            });
        """)
    except:
        pass

def login(driver):
    """Your working login function with added error handling"""
    try:
        print("Starting login process...")
        driver.get("https://premium.morningstar.com.au/auth/logout")
        wait = WebDriverWait(driver, 20)  # Increased timeout
        
        # Wait for page to fully load - INCREASED for cloud
        time.sleep(10)  # Increased from 8
        
        # Dismiss any initial popups
        dismiss_popups(driver)
        
        # Open login form
        print("Looking for Sign-In button...")
        sign_in = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Sign-In']")))
        sign_in.click()
        
        # Enter email and continue
        print("Entering username...")
        email_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
        email_field.clear()
        email_field.send_keys(USERNAME)
        time.sleep(5)
        
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class,'_button-login-id')]"))).click()
        
        # Wait for password field to be ready - INCREASED for cloud
        time.sleep(3)
        
        # Enter password and submit
        print("Entering password...")
        pwd_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
        pwd_field.clear()
        pwd_field.send_keys(PASSWORD)
        time.sleep(5)
        
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class,'_button-login-password')]"))).click()
        
        # Wait for login to complete - INCREASED for cloud
        time.sleep(5)
        
        # Confirm login via search bar
        print("Verifying login success...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Search..."]')))
        print("Login successful!")
        
        # Dismiss any post-login popups
        time.sleep(2)
        dismiss_popups(driver)
        
    except Exception as e:
        print(f"Login error: {str(e)}")
        raise

def click_and_extract(driver, xpath: str) -> str:
    wait = WebDriverWait(driver, 15)
    try:
        # Enhanced popup dismissal before clicking
        dismiss_popups(driver)
        time.sleep(1)
        
        # Select Overview tab
        overview_tab = wait.until(EC.element_to_be_clickable((By.XPATH, XPATHS["overview_tab"])))
        # Try JavaScript click if regular click might be blocked
        driver.execute_script("arguments[0].click();", overview_tab)
        time.sleep(5)  # Wait for content to load
        
        # Dismiss popups again after tab click
        dismiss_popups(driver)
        
        # Return text of target section
        elem = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        return elem.text.strip()
    except Exception as e:
        print(f"Error in click_and_extract: {str(e)}")
        raise

def fetch_data(fund: str, data_point: str) -> str:
    """Fetch a single data point - maintains backwards compatibility"""
    results = fetch_multiple_data(fund, [data_point])
    return results.get(data_point, "Error: Data not found")

def fetch_multiple_data(fund: str, data_points: list) -> dict:
    """Fetch multiple data points in a single session with better error handling"""
    print(f"Starting fetch for fund: {fund}, data points: {data_points}")
    driver = None
    results = {}
    
    try:
        # Create driver
        print("Creating driver...")
        driver = get_driver()
        
        # Login
        login(driver)
        wait = WebDriverWait(driver, 20)
        
        # Search for fund
        print(f"Searching for fund: {fund}")
        main_search = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[placeholder="Search..."]')))
        main_search.click()
        time.sleep(5)
        
        # Dismiss any popups that might appear
        dismiss_popups(driver)
        
        # Wait for secondary search input
        sec_search = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[placeholder="Search securities and site"]')))
        sec_search.clear()
        sec_search.send_keys(fund)
        time.sleep(7)  # Increased wait for suggestions on cloud
        
        # Click first suggestion
        print("Clicking fund suggestion...")
        suggestion = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.mds-search-results__mca.search-results__mca ul.mds-list-group__mca li a')))
        suggestion.click()
        
        # Wait for overview tab - INCREASED for cloud
        print("Waiting for fund page to load...")
        time.sleep(7)
        wait.until(EC.presence_of_element_located((By.XPATH, XPATHS['overview_tab'])))
        
        # Dismiss any popups on fund page
        dismiss_popups(driver)
        
        # Extract all requested data points
        for data_point in data_points:
            try:
                print(f"Extracting {data_point}...")
                text = click_and_extract(driver, XPATHS[data_point])
                results[data_point] = text
                print(f"Successfully extracted {data_point}: {text[:50]}...")
            except Exception as e:
                error_msg = f"Error fetching {data_point}: {str(e)}"
                print(error_msg)
                results[data_point] = error_msg
        
        return results
        
    except Exception as e:
        error_msg = f"Error during fetch process: {str(e)}"
        print(error_msg)
        # Return error for all requested data points
        for data_point in data_points:
            results[data_point] = error_msg
        return results
    finally:
        # Always close the driver
        if driver:
            try:
                driver.quit()
                print("Driver closed successfully")
            except:
                pass
