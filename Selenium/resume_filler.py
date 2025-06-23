from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_linkedin_jobs(url):
    """
    Opens a webpage using Selenium and displays the page source.

    Args:
        url (str): The URL of the webpage to open.
    """
    try:
        # Configure Chrome options
        chrome_options = Options()
        # chrome_options.add_argument("--headless")  # Uncomment to run Chrome in headless mode

        # Initialize the Chrome webdriver
        driver = webdriver.Chrome(options=chrome_options)

        # Open the webpage
        driver.get(url)

        # Wait for the sign-in button to be clickable
        sign_in_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Sign in')]"))
        )
        sign_in_button.click()

        # Wait for the username field to be present
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        username_field.send_keys("spade605@gmail.com")

        # Wait for the password field to be present
        password_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "password"))
        )
        password_field.send_keys("Beholder30!")

        # Submit the form
        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Submit')]"))
        )
        submit_button.click()

        # Keep the browser window open for a few seconds
        time.sleep(300)

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    linkedin_url = "https://www.linkedin.com/jobs/search/?currentJobId=4238469430&distance=10&f_AL=true&geoId=105138576&keywords=python%20developer&origin=JOB_SEARCH_PAGE_JOB_FILTER&refresh=true&spellCorrectionEnabled=true"
    get_linkedin_jobs(linkedin_url)