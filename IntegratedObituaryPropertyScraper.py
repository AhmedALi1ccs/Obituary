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
import json
import traceback
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
        """Setup Google Drive API service with GitHub Actions support"""
        try:
            # Try environment variable first (for GitHub Actions)
            creds_raw = os.getenv('GOOGLE_CREDENTIALS_JSON')
            if creds_raw:
                try:
                    creds_dict = json.loads(creds_raw)
                except json.JSONDecodeError as e:
                    print(f"Error parsing credentials JSON: {e}")
                    return None
            else:
                # Fallback to .env file (for local development)
                creds_raw = os.getenv('GOOGLE_CREDENTIALS_JSON')
                if not creds_raw:
                    print("No credentials found in environment or .env file")
                    return None
                creds_dict = eval(creds_raw)
    
            credentials = service_account.Credentials.from_service_account_info(
                creds_dict,
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            return build('drive', 'v3', credentials=credentials)
        except Exception as e:
            print(f"Error setting up Google Drive: {e}")
            print(f"Full error: {traceback.format_exc()}")
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
        """Initialize undetected-chromedriver with enhanced stability for GitHub Actions"""
        try:
            time.sleep(2)
            
            options = uc.ChromeOptions()
            
            # Stability options
            options.add_argument('--no-sandbox')
            options.add_argument('--headless=new')  # New headless mode
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--start-maximized')
            options.add_argument('--disable-notifications')
            options.add_argument('--disable-extensions')
            
            # Additional stability options
            options.add_argument('--disable-features=VizDisplayCompositor')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-web-security')
            options.add_argument('--no-first-run')
            options.add_argument('--no-default-browser-check')
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--remote-debugging-port=9222')
            
            # Set user agent
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Create driver with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    print(f"Attempt {attempt + 1} to create driver...")
                    self.driver = uc.Chrome(
                        options=options,
                        driver_executable_path=None,
                        version_main=None,
                        use_subprocess=True
                    )
                    
                    # Configure driver settings
                    self.driver.set_page_load_timeout(30)
                    self.driver.implicitly_wait(10)
                    
                    # Test the driver
                    self.driver.get('about:blank')
                    print(f"✓ Chrome driver setup complete (attempt {attempt + 1})")
                    return
                    
                except Exception as e:
                    print(f"Driver setup attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        print("Retrying driver setup...")
                        time.sleep(5)
                        if self.driver:
                            try:
                                self.driver.quit()
                            except:
                                pass
                    else:
                        raise
            
        except Exception as e:
            print(f"Error setting up Chrome driver: {e}")
            print(f"Full error: {traceback.format_exc()}")
            sys.exit(1)
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
        """Scrape obituaries from legacy.com with enhanced error handling"""
        print("\nScraping legacy.com...")
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                print(f"Attempt {attempt + 1} to load legacy.com")
                
                # Test driver before proceeding
                driver.get('about:blank')
                time.sleep(2)
                
                # Load the target page
                print("Loading legacy.com...")
                driver.get(self.sources['legacy'])
                
                # Wait for page to load
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                print("Page loaded successfully")
                time.sleep(5)
                
                # Verify driver is still active
                if not driver.current_url:
                    raise Exception("Driver lost connection")
                
                # Handle popup
                try:
                    no_thanks_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-click='close']"))
                    )
                    no_thanks_button.click()
                    print("Closed popup successfully")
                    time.sleep(2)
                except Exception as e:
                    print(f"No popup found or couldn't close it: {e}")
    
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
                scroll_amount = 500
                
                while True:
                    collect_visible_obituaries()
                    current_position += scroll_amount
                    driver.execute_script(f"window.scrollTo(0, {current_position});")
                    time.sleep(1)
                    
                    total_height = driver.execute_script("return document.body.scrollHeight")
                    if current_position >= total_height:
                        collect_visible_obituaries()
                        break
                        
                return  # Successful completion
                
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    print("Retrying after delay...")
                    time.sleep(10)
                    # Refresh driver state
                    try:
                        driver.get('about:blank')
                    except:
                        pass
                else:
                    print("All attempts to scrape legacy.com failed")
                    raise
                
    def scrape_dispatch(self, driver):
        """Scrape obituaries from dispatch.com with enhanced timeout handling"""
        print("\nScraping dispatch.com...")
        max_retries = 3
        current_retry = 0
        
        while current_retry < max_retries:
            try:
                print(f"Attempt {current_retry + 1} of {max_retries}")
                # Set page load timeout
                driver.set_page_load_timeout(30)
                driver.implicitly_wait(10)
                
                # Try to load the page
                driver.get(self.sources['dispatch'])
                print("Successfully loaded dispatch.com")
                time.sleep(5)  # Increased initial wait
                
                scroll_count = 0
                max_scrolls = 50
                entries_found = 0
    
                while scroll_count < max_scrolls:
                    try:
                        # Use WebDriverWait for better reliability
                        date_headers = WebDriverWait(driver, 10).until(
                            EC.presence_of_all_elements_located(
                                (By.CSS_SELECTOR, 'h2.MuiTypography-root.MuiTypography-h2.css-1cbvm0s')
                            )
                        )
                        
                        for date_header in date_headers:
                            try:
                                current_date = date_header.text
                                print(f"Processing date: {current_date}")
                                
                                containers = WebDriverWait(driver, 5).until(
                                    EC.presence_of_all_elements_located(
                                        (By.CSS_SELECTOR, 'div.MuiGrid-root.MuiGrid-container.css-1rwztak')
                                    )
                                )
                                
                                for container in containers:
                                    try:
                                        name_element = container.find_element(By.CSS_SELECTOR, 'h2.obit-title')
                                        name = name_element.text.strip()
                                        
                                        age = 'N/A'
                                        try:
                                            age_element = container.find_element(By.CSS_SELECTOR, '[aria-label="age"]')
                                            age = age_element.text.replace('Age ', '').strip()
                                        except:
                                            pass
                                            
                                        location = 'N/A'
                                        try:
                                            location_element = container.find_element(By.CSS_SELECTOR, '[aria-label="location"]')
                                            location = location_element.text.strip()
                                        except:
                                            pass
                                        
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
                                        
                                        if not any(
                                            o['first_name'] == entry['first_name'] and 
                                            o['last_name'] == entry['last_name'] and 
                                            o['date'] == entry['date'] and 
                                            o['source'] == entry['source'] 
                                            for o in self.obituaries
                                        ):
                                            self.obituaries.append(entry)
                                            entries_found += 1
                                            print(f"Found obituary: {name}")
                                            
                                    except Exception as e:
                                        print(f"Error processing individual entry: {str(e)}")
                                        continue
                            except Exception as e:
                                print(f"Error processing date header: {str(e)}")
                                continue
                                
                        # Scroll with explicit wait
                        last_height = driver.execute_script("return document.body.scrollHeight")
                        driver.execute_script("window.scrollBy(0, 500);")
                        time.sleep(2)  # Increased scroll wait
                        
                        new_height = driver.execute_script("return document.body.scrollHeight")
                        if new_height == last_height or scroll_count >= max_scrolls:
                            print("Reached end of page or max scrolls")
                            return  # Successfully completed
                            
                        scroll_count += 1
                        print(f"Scrolled {scroll_count} times, found {entries_found} entries")
                        
                    except Exception as e:
                        print(f"Error during scroll iteration: {str(e)}")
                        if scroll_count > 0:  # If we've already found some entries, consider it a success
                            return
                        break  # Otherwise try again
                        
                return  # Successfully completed
                
            except Exception as e:
                print(f"Attempt {current_retry + 1} failed: {str(e)}")
                current_retry += 1
                if current_retry < max_retries:
                    print("Retrying after short delay...")
                    time.sleep(5)
                else:
                    print("All attempts to scrape dispatch.com failed")
                    break  # Exit after all retries are exhausted
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
            print("=== Starting integrated obituary and property scraper ===")
            self.setup_driver()
            
            # Scrape obituaries
            print("\n=== Scraping obituaries ===")
            self.scrape_legacy(self.driver)
            legacy_count = len([o for o in self.obituaries if o['source'] == 'legacy.com'])
            print(f"Found {legacy_count} obituaries from Legacy.com")
            
            self.scrape_dispatch(self.driver)
            dispatch_count = len([o for o in self.obituaries if o['source'] == 'dispatch.com'])
            print(f"Found {dispatch_count} obituaries from Dispatch.com")
            
            if not self.obituaries:
                print("No obituaries found. Exiting.")
                return
                
            # Convert to DataFrame
            print("\n=== Processing data ===")
            df = pd.DataFrame(self.obituaries)
            df = df.drop_duplicates(subset=['name', 'source'])
            
            # Add property information columns
            df['owner_mailing'] = ''
            df['contact_address'] = ''
            df['site_address'] = ''
            df['city'] = ''
            df['zip_code'] = ''
            
            # Process property information
            print("\n=== Searching property records ===")
            for index, row in df.iterrows():
                print(f"\nProcessing: {row['first_name']} {row['last_name']}")
                owner_mailing, contact_address, site_address, city, zip_code = self.search_property(
                    row['first_name'], row['last_name']
                )
                df.at[index, 'owner_mailing'] = owner_mailing
                df.at[index, 'contact_address'] = contact_address
                df.at[index, 'site_address'] = site_address
                df.at[index, 'city'] = city
                df.at[index, 'zip_code'] = zip_code
                print(f"✓ Found property data: {site_address}, {city}")
                time.sleep(2)
            
            # Save results
            print("\n=== Saving results ===")
            current_date = datetime.now().strftime('%m_%d_%y')
            filename = f'obituaries_with_property_{current_date}.csv'
            
            if self.save_to_drive(df, filename):
                print(f"✓ Successfully saved {len(df)} records to Google Drive")
            else:
                print("❌ Failed to save to Google Drive, saving locally")
                df.to_csv(filename, index=False)
            
            # Print summary
            print("\n=== Scraping Summary ===")
            if 'source' in df.columns:
                sources_count = df['source'].value_counts()
                print("\nObituaries by source:")
                for source, count in sources_count.items():
                    print(f"{source}: {count}")
                
                print("\nProperty records found:")
                property_count = len(df[df['owner_mailing'] != 'NOTONAUDITOR'])
                print(f"Records with property information: {property_count}")
                print(f"Records without property information: {len(df) - property_count}")
            else:
                print("No source column found in results")
            
        except Exception as e:
            print(f"\n❌ Error during scraping: {str(e)}")
            print(f"Full error: {traceback.format_exc()}")
            raise e
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    print("\n✓ Driver closed successfully")
                except:
                    print("\n❌ Error closing driver")
if __name__ == "__main__":
    scraper = IntegratedObituaryPropertyScraper()
    scraper.run()
