from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
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
import logging
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
import random
from typing import Dict, List, Tuple, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def rate_limit(min_delay: float, max_delay: float):
    """Rate limiting decorator with randomized delay"""
    def decorator(func):
        last_called = [0]
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            delay = random.uniform(min_delay, max_delay)
            if elapsed < delay:
                time.sleep(delay - elapsed)
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        return wrapper
    return decorator

class IntegratedObituaryPropertyScraper:
    def __init__(self):
        self.obituaries: List[Dict] = []
        self.sources = {
            'legacy': "https://www.legacy.com/us/obituaries/local/ohio/franklin-county",
            'dispatch': "https://www.dispatch.com/obituaries/"
        }
        self.driver = None
        self.folder_id = "1Vn02sVpKU9fGLGG3fo-ZgngWXKhntNvb"
        load_dotenv()
        self.setup_logging()

    def setup_logging(self):
        """Setup custom logging for the scraper"""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def setup_google_drive(self):
        """Setup Google Drive API service with enhanced error handling"""
        try:
            creds_raw = os.getenv('GOOGLE_CREDENTIALS_JSON')
            if not creds_raw:
                self.logger.error("No Google credentials found")
                return None

            try:
                creds_dict = json.loads(creds_raw)
            except json.JSONDecodeError:
                creds_dict = eval(creds_raw)

            credentials = service_account.Credentials.from_service_account_info(
                creds_dict,
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            return build('drive', 'v3', credentials=credentials)
        except Exception as e:
            self.logger.error(f"Google Drive setup error: {e}")
            return None

    def setup_driver(self):
        """Initialize undetected-chromedriver with enhanced stability"""
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--headless=new')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # Additional stability options
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-web-security')
        
        # Randomized user agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        options.add_argument(f'--user-agent={random.choice(user_agents)}')

        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.driver = uc.Chrome(options=options)
                self.driver.set_page_load_timeout(30)
                self.driver.implicitly_wait(10)
                self.driver.get('about:blank')
                return
            except Exception as e:
                self.logger.error(f"Driver setup attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise

    @rate_limit(2.0, 4.0)
    def fetch_page(self, url: str) -> bool:
        """Fetch a page with rate limiting and error handling"""
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            return True
        except Exception as e:
            self.logger.error(f"Error fetching page {url}: {e}")
            return False

    def scrape_legacy(self):
        """Scrape obituaries from legacy.com with enhanced rate limiting"""
        self.logger.info("Starting legacy.com scraping")
        if not self.fetch_page(self.sources['legacy']):
            return

        def collect_visible_obituaries():
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            current_date = None
            
            for element in soup.find_all(['p', 'h4']):
                if element.get('color') == 'neutral50':
                    current_date = element.text.strip()
                elif element.get('data-component') == 'PersonCardFullName':
                    name = element.text.strip()
                    if current_date and name:
                        first_name, last_name, full_name = self.split_name(name)
                        entry = {
                            'first_name': first_name,
                            'last_name': last_name,
                            'name': full_name,
                            'date': current_date,
                            'source': 'legacy.com',
                            'age': 'N/A',
                            'location': 'Ohio',
                            'Tag': 'Obituary-Ahmed fetched'
                        }
                        if self.validate_obituary_data(entry):
                            self.obituaries.append(entry)

        scroll_position = 0
        last_count = 0
        no_new_entries_count = 0

        while no_new_entries_count < 3:
            current_count = len(self.obituaries)
            if current_count == last_count:
                no_new_entries_count += 1
            else:
                no_new_entries_count = 0
            
            last_count = current_count
            collect_visible_obituaries()
            scroll_position += 500
            self.driver.execute_script(f"window.scrollTo(0, {scroll_position});")
            time.sleep(random.uniform(1.5, 3.0))

    def validate_obituary_data(self, entry: Dict) -> bool:
        """Validate obituary data entries"""
        required_fields = ['first_name', 'last_name', 'date', 'source']
        return all(entry.get(field) for field in required_fields)

    @rate_limit(1.5, 3.0)
    def search_property(self, first_name: str, last_name: str) -> Tuple[str, str, str, str, str]:
        """Search property information with enhanced rate limiting"""
        try:
            url = 'https://property.franklincountyauditor.com/_web/search/commonsearch.aspx?mode=owner'
            if not self.fetch_page(url):
                return ('NOTONAUDITOR',) * 5

            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "inpOwner"))
            )
            
            search_query = f"{last_name} {first_name}"
            search_box.clear()
            search_box.send_keys(search_query)
            search_box.send_keys(Keys.RETURN)
            
            time.sleep(random.uniform(2.0, 3.0))
            
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "tr.SearchResults"))
                ).click()
            except TimeoutException:
                return ('NOTONAUDITOR',) * 5

            # Extract property information with enhanced error handling
            property_data = {
                'owner_mailing': 'NOTONAUDITOR',
                'contact_address': 'NOTONAUDITOR',
                'site_address': 'NOTONAUDITOR',
                'city': 'NOTONAUDITOR',
                'zip_code': 'NOTONAUDITOR'
            }

            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "DataletData"))
            )

            rows = self.driver.find_elements(By.CSS_SELECTOR, "tr")
            for row in rows:
                try:
                    heading = row.find_element(By.CLASS_NAME, "DataletSideHeading").text
                    data = row.find_element(By.CLASS_NAME, "DataletData").text
                    
                    if "Owner Mailing" in heading and "Contact Address" not in heading:
                        property_data['owner_mailing'] = data
                    elif "Contact Address" in heading:
                        property_data['contact_address'] = data
                    elif "Site (Property) Address" in heading:
                        property_data['site_address'] = data
                    elif "City/Village" in heading:
                        property_data['city'] = data
                    elif "Zip Code" in heading:
                        property_data['zip_code'] = data
                except NoSuchElementException:
                    continue

            return tuple(property_data.values())

        except Exception as e:
            self.logger.error(f"Property search error for {first_name} {last_name}: {e}")
            return ('NOTONAUDITOR',) * 5

    def process_property_batch(self, batch: pd.DataFrame) -> List[Tuple[str, str, str, str, str]]:
        """Process a batch of property searches with ThreadPoolExecutor"""
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(self.search_property, row['first_name'], row['last_name'])
                for _, row in batch.iterrows()
            ]
            return [future.result() for future in futures]

    def run(self):
        """Run the complete integrated scraping process"""
        try:
            self.logger.info("Starting scraping process")
            self.setup_driver()

            # Scrape obituaries
            self.scrape_legacy()
            self.logger.info(f"Found {len(self.obituaries)} obituaries")

            if not self.obituaries:
                self.logger.warning("No obituaries found")
                return

            # Convert to DataFrame and remove duplicates
            df = pd.DataFrame(self.obituaries)
            df = df.drop_duplicates(subset=['name', 'source'])

            # Add property information columns
            property_columns = ['owner_mailing', 'contact_address', 'site_address', 'city', 'zip_code']
            for col in property_columns:
                df[col] = ''

            # Process property information in batches
            batch_size = 5
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i+batch_size]
                results = self.process_property_batch(batch)
                for j, result in enumerate(results):
                    for k, col in enumerate(property_columns):
                        df.iloc[i+j, df.columns.get_loc(col)] = result[k]
                
                self.logger.info(f"Processed batch {i//batch_size + 1}/{(len(df) + batch_size - 1)//batch_size}")

            # Ensure Tag column exists
            df['Tag'] = 'Obituary-Ahmed fetched'

            # Save results
            current_date = datetime.now().strftime('%m_%d_%y')
            filename = f'obituaries_with_property_{current_date}.csv'
            
            if self.save_to_drive(df, filename):
                self.logger.info(f"Saved {len(df)} records to Google Drive")
            else:
                self.logger.warning("Failed to save to Google Drive, saving locally")
                df.to_csv(filename, index=False)

            # Print summary
            self.logger.info("\n=== Scraping Summary ===")
            self.logger.info(f"Total records: {len(df)}")
            self.logger.info(f"Records with property: {len(df[df['owner_mailing'] != 'NOTONAUDITOR'])}")

        except Exception as e:
            self.logger.error(f"Scraping error: {e}")
            self.logger.error(traceback.format_exc())
            raise
        finally:
            if self.driver:
                self.driver.quit()

if __name__ == "__main__":
    scraper = IntegratedObituaryPropertyScraper()
    scraper.run()
