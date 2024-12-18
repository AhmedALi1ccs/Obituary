#!/usr/bin/env python3
import sys
import os
import logging
from datetime import datetime
import traceback
from IntegratedObituaryPropertyScraper import IntegratedObituaryPropertyScraper

# Set up logging
log_dir = os.path.expanduser('~/obituary_scraper_logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'{log_dir}/scraper_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

def main():
    try:
        logging.info("Starting obituary scraper")
        logging.info(f"Script started at {datetime.now()}")
        
        # Initialize and run the scraper
        scraper = IntegratedObituaryPropertyScraper()
        scraper.run()
        
        logging.info("Scraping completed successfully")
        
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        logging.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()