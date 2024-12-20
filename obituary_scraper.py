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
import random
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv
import io
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

    def setup_google_drive(self):
        """Setup Google Drive API service"""
        try:
            credentials = service_account.Credentials.from_service_account_info(
                eval(os.getenv('GOOGLE_CREDENTIALS_JSON')),
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            return build('drive', 'v3', credentials=credentials)
        except Exception as e:
            print(f"Error setting up Google Drive: {e}")
            return None
    
    def add_random_delay(self):
        """Add random delay between actions to appear more human-like"""
        time.sleep(random.uniform(1, 3))

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

    def setup_driver(self):
        """Initialize undetected-chromedriver with macOS compatibility fixes"""
        try:
            time.sleep(2)
            
            options = uc.ChromeOptions()
            
            # Basic required options
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            # Don't use --headless=new on macOS as it can cause issues
            options.add_argument('--headless')
            
            # Set a reasonable window size
            options.add_argument('--window-size=1920,1080')
            
            # Add user agent
            options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Reduce memory usage
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-software-rasterizer')
            options.add_argument('--disable-extensions')
            
            # Create the driver with minimal options first
            self.driver = uc.Chrome(
                options=options,
                driver_executable_path=None,
                use_subprocess=True,
                version_main=None
            )
            
            # Set window size after initialization
            self.driver.set_window_size(1920, 1080)
            
            # Basic stealth settings after driver is created
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            # Add a small delay after setup
            time.sleep(3)
            
            return self.driver
            
        except Exception as e:
            print(f"Detailed error setting up Chrome driver: {str(e)}")
            if self.driver:
                self.driver.quit()
            raise e


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
        """Scrape obituaries from legacy.com with enhanced anti-detection measures"""
        print("\nScraping legacy.com...")
        
        # Add random delay before navigation
        self.add_random_delay()
        
        # Clear cookies and cache before visiting
        driver.execute_cdp_cmd('Network.clearBrowserCookies', {})
        driver.execute_cdp_cmd('Network.clearBrowserCache', {})
        
        driver.get(self.sources['legacy'])
        self.add_random_delay()
        
        # Simulate human-like scrolling behavior
        def human_like_scroll():
            total_height = driver.execute_script("return document.body.scrollHeight")
            current_height = 0
            scroll_step = random.randint(100, 300)
            
            while current_height < total_height:
                next_height = min(current_height + scroll_step, total_height)
                driver.execute_script(f"window.scrollTo({current_height}, {next_height})")
                current_height = next_height
                time.sleep(random.uniform(0.5, 1.5))
        
        try:
            # Handle popup with retry mechanism
            for _ in range(3):
                try:
                    WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-click='close']"))
                    ).click()
                    print("Closed popup successfully")
                    break
                except:
                    self.add_random_delay()
                    continue
        except Exception as e:
            print("No popup found or couldn't close it:", e)

        def collect_visible_obituaries():
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            current_date = None
            current_entries = set()
            
            for element in soup.find_all(['p', 'h4']):
                if element.get('color') == 'neutral50' and 'Box-sc-ucqo0b-0' in element.get('class', []):
                    current_date = element.text.strip()
                elif element.get('data-component') == 'PersonCardFullName':
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
                        self.obituaries.append(entry)
            
        current_position = 0
        scroll_amount = 200
        
        while True:
            collect_visible_obituaries()
            current_position += scroll_amount
            driver.execute_script(f"window.scrollTo(0, {current_position});")
            time.sleep(1)
            
            total_height = driver.execute_script("return document.body.scrollHeight")
            if current_position >= total_height:
                collect_visible_obituaries()
                break
    #        
    def scrape_dispatch(self, driver):
        """Scrape obituaries from dispatch.com with improved timeout handling"""
        print("\nScraping dispatch.com...")
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Initial navigation
                driver.set_page_load_timeout(30)  # Shorter initial timeout
                driver.get(self.sources['dispatch'])
                
                # Simulate pressing enter in URL bar by executing JavaScript refresh
                driver.execute_script("window.location.href = window.location.href")
                
                # Wait for initial content with explicit wait
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.MuiGrid-root.MuiGrid-container'))
                )
                print("Successfully loaded dispatch.com")
                break
                
            except Exception as e:
                retry_count += 1
                print(f"Attempt {retry_count} failed: {str(e)}")
                
                if retry_count < max_retries:
                    print(f"Retrying... (Attempt {retry_count + 1} of {max_retries})")
                    # Clear cookies and cache between attempts
                    driver.delete_all_cookies()
                    try:
                        driver.execute_script("window.localStorage.clear()")
                        driver.execute_script("window.sessionStorage.clear()")
                    except:
                        pass
                    time.sleep(5)  # Wait between retries
                else:
                    print("Max retries reached for initial load")
                    raise
        
        scroll_count = 0
        max_scrolls = 50
        
        while scroll_count < max_scrolls:
            try:
                # Use explicit waits for date headers
                date_headers = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'h2.MuiTypography-root.MuiTypography-h2.css-1cbvm0s'))
                )
                
                for date_header in date_headers:
                    current_date = date_header.text
                    
                    # Use explicit waits for containers
                    containers = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.MuiGrid-root.MuiGrid-container.css-1rwztak'))
                    )
                    
                    for container in containers:
                        try:
                            # Use explicit waits for each element
                            name_element = WebDriverWait(container, 5).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, 'h2.obit-title'))
                            )
                            name = name_element.text.strip()
                            
                            try:
                                age = WebDriverWait(container, 2).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, '[aria-label="age"]'))
                                ).text.replace('Age ', '').strip()
                            except:
                                age = 'N/A'
                                
                            try:
                                location = WebDriverWait(container, 2).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, '[aria-label="location"]'))
                                ).text.strip()
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
                            
                # Improved scrolling with verification
                last_height = driver.execute_script("return document.body.scrollHeight")
                driver.execute_script("window.scrollBy(0, 500);")
                time.sleep(2)  # Give more time for content to load
                
                # Verify scroll was successful
                new_height = driver.execute_script("return document.body.scrollHeight")
                current_scroll = driver.execute_script("return window.pageYOffset")
                
                if new_height == last_height and current_scroll > 0:
                    # Try to force refresh of content
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    
                    if driver.execute_script("return document.body.scrollHeight") == last_height:
                        print("Reached end of page")
                        break
                
                scroll_count += 1
                
            except Exception as e:
                print(f"Error during scroll iteration: {e}")
                # Try to recover and continue
                time.sleep(2)
                continue

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
