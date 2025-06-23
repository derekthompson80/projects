# Tested with the following package versions:
# beautifulsoup4==4.12.2
# Requests==2.31.0
# selenium==4.15.1


from bs4 import BeautifulSoup
import requests
import urllib3
from selenium import webdriver
from selenium.webdriver.common.by import By
import time

# Disable InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Part 1 - Scrape the links, addresses, and prices of the rental properties

header = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.google.com/",
    "sec-ch-ua": "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
    "Upgrade-Insecure-Requests": "1"
}

# Use our Zillow-Clone website (instead of Zillow.com)
# Note: Setting verify=False disables SSL certificate verification, which can pose security risks.
# This is a workaround for the SSL certificate verification issue but should be used with caution in production.
response = requests.get("https://appbrewery.github.io/Zillow-Clone/", headers=header, verify=False)

# Print the status code to confirm if we're getting a 403 error
print(f"Response status code: {response.status_code}")

data = response.text
soup = BeautifulSoup(data, "html.parser")

# Create a list of all the links on the page using a CSS Selector
all_link_elements = soup.select(".StyledPropertyCardDataWrapper a")
# Python list comprehension (covered in Day 26)
all_links = [link["href"] for link in all_link_elements]
print(f"There are {len(all_links)} links to individual listings in total: \n")
print(all_links)

# Create a list of all the addresses on the page using a CSS Selector
# Remove newlines \n, pipe symbols |, and whitespaces to clean up the address data
all_address_elements = soup.select(".StyledPropertyCardDataWrapper address")
all_addresses = [address.get_text().replace(" | ", " ").strip() for address in all_address_elements]
print(f"\n After having been cleaned up, the {len(all_addresses)} addresses now look like this: \n")
print(all_addresses)

# Create a list of all the prices on the page using a CSS Selector
# Get a clean dollar price and strip off any "+" symbols and "per month" /mo abbreviation
all_price_elements = soup.select(".PropertyCardWrapper span")
all_prices = [price.get_text().replace("/mo", "").split("+")[0] for price in all_price_elements if "$" in price.text]
print(f"\n After having been cleaned up, the {len(all_prices)} prices now look like this: \n")
print(all_prices)

# Part 2 - Fill in the Google Form using Selenium

# Optional - Keep the browser open (helps diagnose issues if the script crashes)
chrome_options = webdriver.ChromeOptions()
chrome_options.add_experimental_option("detach", True)
driver = webdriver.Chrome(options=chrome_options)

# Uncomment and modify the code below when you have your own Google Form ready

for n in range(len(all_links)):
    try:
        # Replace it with your own Google Form URL
        form_url = "https://docs.google.com/spreadsheets/d/1bIGuwp1Z4PsIvqWaNpDroAuHJAcxZQF2bU1WnabyrKU/edit?gid=1927927831#gid=1927927831"
        driver.get(form_url)
        time.sleep(2)

        # Update these XPath selectors to match your form's structure
        address = driver.find_element(by=By.XPATH,
                                     value='XPATH_TO_ADDRESS_FIELD')
        price = driver.find_element(by=By.XPATH,
                                   value='XPATH_TO_PRICE_FIELD')
        link = driver.find_element(by=By.XPATH,
                                  value='XPATH_TO_LINK_FIELD')
        submit_button = driver.find_element(by=By.XPATH,
                                           value='XPATH_TO_SUBMIT_BUTTON')

        address.send_keys(all_addresses[n])
        price.send_keys(all_prices[n])
        link.send_keys(all_links[n])
        submit_button.click()

        # Wait for form submission to complete
        time.sleep(1)
    except Exception as e:
        print(f"Error submitting form for property {n+1}: {e}")


# Close the browser
driver.quit()
