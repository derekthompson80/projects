from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

def get_webpage_info(url):
    """
    Opens a webpage using Selenium and extracts the text from the page.

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

        # Get the page title
        title = driver.title

        # Get the page source
        page_source = driver.page_source

        # Print the title and page source
        # print("Page Title:", title)
        # print("Page Source:", page_source)

        # Do not close the browser
        # driver.quit()

        # Fill in the form fields
        first_name_field = driver.find_element(By.NAME, "fName")
        first_name_field.send_keys("John")

        last_name_field = driver.find_element(By.NAME, "lName")
        last_name_field.send_keys("Doe")

        email_field = driver.find_element(By.NAME, "email")
        email_field.send_keys("john.doe@example.com")

        # Keep the browser window open for a few seconds
        time.sleep(10)


    except Exception as e:
        print(f"An error occurred: {e}")


# Example usage:
if __name__ == "__main__":
    get_webpage_info("https://secure-retreat-92358.herokuapp.com/")