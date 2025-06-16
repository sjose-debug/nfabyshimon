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

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Morningstar credentials
USERNAME = os.getenv("MORNINGSTAR_USERNAME")
PASSWORD = os.getenv("MORNINGSTAR_PASSWORD")
if not USERNAME or not PASSWORD:
    raise ValueError("Please set MORNINGSTAR_USERNAME and MORNINGSTAR_PASSWORD in .env")

# XPATH configuration
XPATHS = {
    "overview_tab":        "//span[text()='Overview']",
    "mer":                 "//div[@class='sal-dp-pair'][.//div[@class='sal-dp-name' and normalize-space(text())='Total Cost Ratio (Prospective)']]//div[@class='sal-dp-value']",
    "performance":         "//div[@class='sal-dp-pair'][.//div[@class='sal-dp-name' and normalize-space(text())='1 Yr Return']]//div[@class='sal-dp-value']",
    "fund_profile":        "//div[@class='sal-mip-strategy-content']//div[@class='sal-mip-strategy__body']",
}

def get_driver():
    """Create a new Chrome driver instance"""
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--log-level=3")
    service = Service(log_path=os.devnull)
    driver = webdriver.Chrome(service=service, options=opts)
    driver.maximize_window()
    return driver

def login(driver):
    """Your working login function"""
    driver.get("https://premium.morningstar.com.au/auth/logout")
    wait = WebDriverWait(driver, 15)
    # Open login form
    sign_in = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Sign-In']")))
    sign_in.click()
    # Enter email and continue
    email_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
    email_field.send_keys(USERNAME)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class,'_button-login-id')]"))).click()
    # Enter password and submit
    pwd_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
    pwd_field.send_keys(PASSWORD)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class,'_button-login-password')]"))).click()
    # Confirm login via search bar
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Search..."]')))

def click_and_extract(driver, xpath: str) -> str:
    wait = WebDriverWait(driver, 10)
    # Dismiss subscription pop-up if present
    driver.execute_script(
        "var el=document.getElementById('subscription-notification'); if(el) el.remove();"
    )
    # Select Overview tab
    wait.until(EC.element_to_be_clickable((By.XPATH, XPATHS["overview_tab"]))).click()
    # Return text of target section
    elem = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
    return elem.text.strip()

def fetch_data(fund: str, data_point: str) -> str:
    # Create a fresh driver for each request
    driver = get_driver()
    try:
        # Login
        login(driver)
        wait = WebDriverWait(driver, 15)
        # Search fund
        main_search = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[placeholder="Search..."]')))
        main_search.click()
        
        # Wait for secondary search input
        sec_search = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[placeholder="Search securities and site"]')))
        sec_search.clear()
        sec_search.send_keys(fund)
        time.sleep(1)  # Allow suggestions to load
        
        # Click first suggestion
        suggestion = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.mds-search-results__mca.search-results__mca ul.mds-list-group__mca li a')))
        suggestion.click()
        
        # Wait for overview tab
        wait.until(EC.presence_of_element_located((By.XPATH, XPATHS['overview_tab'])))
        time.sleep(1)
        
        # Extract data using click_and_extract
        text = click_and_extract(driver, XPATHS[data_point])
        return text
        
    except Exception as e:
        return f"Error fetching {data_point}: {str(e)}"
    finally:
        # Always close the driver
        driver.quit()

# Note: The UI components have been moved to app.py
# This file now only contains the scraping functions