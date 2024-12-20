from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
import pandas as pd
import time
from datetime import datetime
import re
import os
import sys
import csv
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv
import io
import logging
from pathlib import Path
import json
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('error.log'),
        logging.StreamHandler()
    ]
)
class IntegratedObituaryPropertyScraper:
    def __init__(self):
        self.obituaries = []
        self.sources = {
            'legacy': "https://www.legacy.com/us/obituaries/local/ohio/franklin-county",
            'dispatch': "https://www.dispatch.com/obituaries/"
        }
        self.driver = None
        self.folder_id = "1Vn02sVpKU9fGLGG3fo-ZgngWXKhntNvb"
        load_dotenv()  # Load environment variables
    #
    def setup_google_drive(self):
            """Setup Google Drive API service"""
            try:
                # Check for credentials file first
                creds_file = Path('google_credentials.json')
                if creds_file.exists():
                    credentials = service_account.Credentials.from_service_account_file(
                        str(creds_file),
                        scopes=['https://www.googleapis.com/auth/drive.file']
                    )
                else:
                    # Fall back to environment variable
                    creds_json = json.loads(os.getenv('GOOGLE_CREDENTIALS_JSON', '{}'))
                    credentials = service_account.Credentials.from_service_account_info(
                        creds_json,
                        scopes=['https://www.googleapis.com/auth/drive.file']
                    )
                return build('drive', 'v3', credentials=credentials)
            except Exception as e:
                logging.error(f"Error setting up Google Drive: {e}")
                return None
    def save_to_drive(self, df, filename):
        """Save DataFrame to Google Drive"""
        try:
            # Create drive service
            drive_service = self.setup_google_drive()
            if not drive_service:
                print("Failed to setup Google Drive service")
                return False

            # Save DataFrame to temporary file
            temp_filename = f"temp_{filename}"
            df.to_csv(temp_filename, index=False)

            # Prepare file metadata
            file_metadata = {
                'name': filename,
                'parents': [self.folder_id]
            }

            # Create media
            media = MediaFileUpload(
                temp_filename,
                mimetype='text/csv',
                resumable=True
            )

            # Upload file
            file = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            # Remove temporary file
            os.remove(temp_filename)

            print(f"\nSuccessfully uploaded {filename} to Google Drive")
            print(f"File ID: {file.get('id')}")
            return True

        except Exception as e:
            print(f"Error saving to Google Drive: {e}")
            return False
    #
    def setup_driver(self):
            """Initialize undetected-chromedriver for CI environment"""
            try:
                options = uc.ChromeOptions()
                
                # CI-specific options
                options.add_argument('--headless')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument('--window-size=1920,1080')
                options.add_argument('--disable-features=VizDisplayCompositor')
                options.add_argument('--disable-blink-features=AutomationControlled')
                
                # Set specific Chrome binary path for CI
                if os.getenv('CI'):
                    options.binary_location = '/usr/bin/google-chrome'
                
                self.driver = uc.Chrome(options=options)
                logging.info("Chrome driver setup successful")
                
            except Exception as e:
                logging.error(f"Error setting up Chrome driver: {e}")
                raise

    def split_name(self, full_name):
        """Split full name into first and last name with special case handling"""
        # Clean and split the name
        name_without_dates = re.sub(r'\s*\d{4}-\d{4}\s*$', '', full_name.strip())
        name_without_dates = re.sub(r'\s*(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\s*$', '', name_without_dates)
        name_without_nickname = re.sub(r'\s*[\(\[].+?[\)\]]\s*', '', name_without_dates)
        parts = [part for part in name_without_nickname.strip().split() if part]
        
        if len(parts) >= 2:
            if parts[0].lower().replace('.', '') == 'dr':
                first_name = parts[1] if len(parts) > 2 else parts[0]
                start_index = 1
            else:
                first_name = parts[0]
                start_index = 0

            last_word = parts[-1].lower().replace('.', '')
            if (last_word in ['jr', 'sr', 'ii', 'iii', 'iv', 'v','tr'] or 
                (len(last_word) == 1 and last_word.isalpha())):
                last_name = parts[-2] if len(parts) > 1 else parts[-1]
            else:
                last_name = parts[-1]
            
            full_name = ' '.join(parts)
            return first_name, last_name, full_name
        
        return full_name, '', full_name

    # [Previous scraping methods remain the same: scrape_legacy, scrape_fcfreepress, scrape_dispatch]
    # Include all the scraping methods from the first code here
    def scrape_legacy(self, driver):
        """Scrape obituaries from legacy.com with enhanced anti-bot handling"""
        print("\nScraping legacy.com...")
        
        try:
            # Additional options for undetected_chromedriver to appear more human-like
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            # Set additional headers
            driver.execute_cdp_cmd('Network.enable', {})
            driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {
                "headers": {
                    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                    "accept-language": "en-US,en;q=0.9",
                    "sec-ch-ua": '"Not.A/Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                    "sec-fetch-dest": "document",
                    "sec-fetch-mode": "navigate",
                    "sec-fetch-site": "same-origin",
                    "sec-fetch-user": "?1",
                    "upgrade-insecure-requests": "1"
                }
            })
    
            # Add random delay before accessing the site
            time.sleep(random.uniform(2, 5))
            
            driver.get(self.sources['legacy'])
            
            # Wait longer for initial page load
            time.sleep(random.uniform(5, 8))
    
            # Handle cookie consent if it appears
            try:
                cookie_buttons = driver.find_elements(By.CSS_SELECTOR, "button[data-testid='button-accept']")
                if cookie_buttons:
                    cookie_buttons[0].click()
                    time.sleep(2)
            except Exception as e:
                print(f"No cookie consent found or error handling it: {e}")
    
            # Try to handle "No thanks" popup with multiple approaches
            popup_selectors = [
                "button[data-click='close']",
                "button.modal__close",
                "button[aria-label='Close']",
                ".modal-close-button",
                "#close-button"
            ]
            
            for selector in popup_selectors:
                try:
                    popup = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    popup.click()
                    print(f"Closed popup using selector: {selector}")
                    time.sleep(2)
                    break
                except:
                    continue
    
            def collect_visible_obituaries():
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                current_date = None
                
                for element in soup.find_all(['p', 'h4', 'div']):
                    # Look for date elements with multiple possible class combinations
                    if (element.get('color') == 'neutral50' and 
                        any(cls in element.get('class', []) for cls in ['Box-sc', 'DateText'])):
                        current_date = element.text.strip()
                    
                    # Look for name elements with multiple possible attributes
                    elif (element.get('data-component') == 'PersonCardFullName' or 
                          'obituary-name' in element.get('class', [])):
                        full_name = element.text.strip()
                        if current_date and full_name:
                            first_name, last_name, name = self.split_name(full_name)
                            entry = {
                                'first_name': first_name,
                                'last_name': last_name,
                                'name': name,
                                'date': current_date,
                                'source': 'legacy.com',
                                'age': 'N/A',
                                'location': 'Ohio'
                            }
                            if not any(o['name'] == entry['name'] and 
                                     o['date'] == entry['date'] for o in self.obituaries):
                                self.obituaries.append(entry)
                                print(f"Found obituary: {name} - {current_date}")
            
            # Scroll with random delays and human-like behavior
            current_position = 0
            last_count = 0
            no_new_entries_count = 0
            
            while no_new_entries_count < 3:  # Stop if no new entries found after 3 attempts
                initial_count = len(self.obituaries)
                
                # Random scroll amount
                scroll_amount = random.randint(300, 700)
                current_position += scroll_amount
                
                # Smooth scroll
                driver.execute_script(f"""
                    window.scrollTo({{
                        top: {current_position},
                        behavior: 'smooth'
                    }});
                """)
                
                # Random wait between scrolls
                time.sleep(random.uniform(1.5, 3.5))
                
                collect_visible_obituaries()
                
                # Check if we found new entries
                if len(self.obituaries) == initial_count:
                    no_new_entries_count += 1
                else:
                    no_new_entries_count = 0
                
                # Check if we've reached the bottom
                total_height = driver.execute_script("return document.body.scrollHeight")
                if current_position >= total_height:
                    break
                    
                # Add some random mouse movements
                if random.random() < 0.3:  # 30% chance of mouse movement
                    try:
                        element = driver.find_element(By.TAG_NAME, "body")
                        ActionChains(driver).move_to_element_with_offset(
                            element, 
                            random.randint(0, 500), 
                            random.randint(0, 500)
                        ).perform()
                    except:
                        pass
            
            print(f"Total obituaries collected from legacy.com: {len(self.obituaries)}")
            
        except Exception as e:
            print(f"Error during legacy.com scraping: {str(e)}")
            logging.error(f"Legacy.com scraping error: {str(e)}", exc_info=True)
            
    def scrape_dispatch(self, driver):
        """Scrape obituaries from dispatch.com"""
        print("\nScraping dispatch.com...")
        driver.get(self.sources['dispatch'])
        time.sleep(2)

        scroll_count = 0
        max_scrolls = 50

        while scroll_count < max_scrolls:
            try:
                date_headers = driver.find_elements(By.CSS_SELECTOR, 'h2.MuiTypography-root.MuiTypography-h2.css-1cbvm0s')
                
                for date_header in date_headers:
                    current_date = date_header.text
                    
                    containers = driver.find_elements(By.CSS_SELECTOR, 'div.MuiGrid-root.MuiGrid-container.css-1rwztak')
                    
                    for container in containers:
                        try:
                            name_element = container.find_element(By.CSS_SELECTOR, 'h2.obit-title')
                            name = name_element.text.strip()
                            
                            try:
                                age = container.find_element(By.CSS_SELECTOR, '[aria-label="age"]').text.replace('Age ', '').strip()
                            except:
                                age = 'N/A'
                                
                            try:
                                location = container.find_element(By.CSS_SELECTOR, '[aria-label="location"]').text.strip()
                            except:
                                location = 'N/A'
                            
                            first_name, last_name, full_name = self.split_name(name)
                            entry = {
                                'first_name': first_name,
                                'last_name': last_name,
                                'date': current_date,
                                'name': full_name,
                                'source': 'dispatch.com',
                                'age': age,
                                'location': location
                            }
                            
                            # Check for duplicates before adding
                            if not any(
                                o['first_name'] == entry['first_name'] and 
                                o['last_name'] == entry['last_name'] and 
                                o['date'] == entry['date'] and 
                                o['source'] == entry['source'] 
                                for o in self.obituaries
                            ):
                                self.obituaries.append(entry)
                                print(f"Successfully scraped: {name}")
                                
                        except Exception as e:
                            print(f"Error processing container: {e}")
                            continue
                            
            except Exception as e:
                print(f"Error extracting data: {e}")

            last_height = driver.execute_script("return document.body.scrollHeight")
            current_scroll = driver.execute_script("return window.pageYOffset")
            
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(1)
            
            new_scroll = driver.execute_script("return window.pageYOffset")
            if new_scroll == current_scroll:
                print("Reached end of page")
                break
                
            scroll_count += 1

    def search_property(self, first_name, last_name):
        """Search property information for a given name"""
        try:
            # Navigate to the search page
            self.driver.get('https://property.franklincountyauditor.com/_web/search/commonsearch.aspx?mode=owner')
            
            # Wait for the search input
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "inpOwner"))
            )
            
            # Enter search query
            search_query = f"{last_name} {first_name}"
            search_box.clear()
            search_box.send_keys(search_query)
            search_box.send_keys(Keys.RETURN)
            
            time.sleep(2)
            
            # Check for "no records found"
            try:
                no_records = self.driver.find_element(By.XPATH, "//large[contains(text(), 'Your search did not find any records')]")
                if no_records:
                    return 'NOTONAUDITOR', 'NOTONAUDITOR', 'NOTONAUDITOR', 'NOTONAUDITOR', 'NOTONAUDITOR'
            except:
                pass
            
            # Handle results page
            if "CommonSearch.aspx?mode=OWNER" in self.driver.current_url:
                try:
                    first_result = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "tr.SearchResults"))
                    )
                    first_result.click()
                except:
                    return 'NOTONAUDITOR', 'NOTONAUDITOR', 'NOTONAUDITOR', 'NOTONAUDITOR', 'NOTONAUDITOR'
            
            time.sleep(2)
            
            # Extract information
            owner_mailing = 'NOTONAUDITOR'
            contact_address = 'NOTONAUDITOR'
            site_address = 'NOTONAUDITOR'
            city = 'NOTONAUDITOR'
            zip_code = 'NOTONAUDITOR'
            
            rows = self.driver.find_elements(By.CSS_SELECTOR, "tr")
            for row in rows:
                try:
                    heading = row.find_element(By.CLASS_NAME, "DataletSideHeading").text
                    data = row.find_element(By.CLASS_NAME, "DataletData").text
                    
                    if "Owner Mailing" in heading and "Contact Address" not in heading:
                        owner_mailing = data
                    elif "Contact Address" in heading:
                        contact_address = data
                    elif "Site (Property) Address" in heading:
                        site_address = data
                    elif "City/Village" in heading:
                        city = data
                    elif "Zip Code" in heading:
                        zip_code = data
                except:
                    continue
            
            return owner_mailing, contact_address, site_address, city, zip_code
            
        except Exception as e:
            print(f"Error searching property for {first_name} {last_name}: {str(e)}")
            return 'NOTONAUDITOR', 'NOTONAUDITOR', 'NOTONAUDITOR', 'NOTONAUDITOR', 'NOTONAUDITOR'

    def run(self):
        """Run the complete integrated scraping process"""
        try:
            print("Starting integrated obituary and property scraper...")
            self.setup_driver()
            
            # Scrape obituaries
            self.scrape_legacy(self.driver)
            self.scrape_dispatch(self.driver)
            
            # Convert to DataFrame and remove duplicates
            df = pd.DataFrame(self.obituaries)
            df = df.drop_duplicates(subset=['name', 'source'])
            
            # Add new columns for property information
            df['owner_mailing'] = ''
            df['contact_address'] = ''
            df['site_address'] = ''
            df['city'] = ''
            df['zip_code'] = ''
            
            # Process each obituary for property information
            print("\nSearching property records...")
            for index, row in df.iterrows():
                owner_mailing, contact_address, site_address, city, zip_code = self.search_property(row['first_name'], row['last_name'])
                df.at[index, 'owner_mailing'] = owner_mailing
                df.at[index, 'contact_address'] = contact_address
                df.at[index, 'site_address'] = site_address
                df.at[index, 'city'] = city
                df.at[index, 'zip_code'] = zip_code
                print(f"Processed: {row['first_name']} {row['last_name']}")
                print(f"  Owner Mailing: {owner_mailing}")
                print(f"  Contact Address: {contact_address}")
                print(f"  Site Address: {site_address}")
                print(f"  City: {city}, Zip: {zip_code}")
                time.sleep(2)
            
            # Get current date in MM/DD/YY format
            current_date = datetime.now().strftime('%m_%d_%y')
            filename = f'obituaries_with_property_{current_date}.csv'
            
            # Save to Google Drive
            if self.save_to_drive(df, filename):
                print(f"\nSuccessfully saved {len(df)} records to Google Drive")
            else:
                print("\nFailed to save to Google Drive, saving locally instead")
                df.to_csv(filename, index=False)
            
            # Print summary
            print(f"\nScraping Summary:")
            sources_count = df['source'].value_counts()
            print("\nObituaries by source:")
            for source, count in sources_count.items():
                print(f"{source}: {count}")
            
            print("\nProperty records found:")
            property_count = len(df[df['owner_mailing'] != 'NOTONAUDITOR'])
            print(f"Records with property information: {property_count}")
            print(f"Records without property information: {len(df) - property_count}")
            
        except Exception as e:
            print(f"Error during scraping: {e}")
            raise e
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    print("\nDriver closed successfully")
                except:
                    print("\nError closing driver")
if __name__ == "__main__":
    scraper = IntegratedObituaryPropertyScraper()
    scraper.run()
