import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pandas as pd

def test_drive_access():
    print("\n=== Testing Google Drive Access ===")
    
    try:
        # Get credentials from environment and debug their format
        print("\nDebugging credentials...")
        creds_raw = os.getenv('GOOGLE_CREDENTIALS_JSON')
        
        if not creds_raw:
            print("❌ No credentials found in environment")
            return
            
        print(f"Credentials type: {type(creds_raw)}")
        print(f"First 100 characters of credentials: {creds_raw[:100]}")
        
        try:
            # Try to parse JSON with explicit error handling
            print("\nAttempting to parse JSON...")
            
            # Remove any extra quotes if they exist
            if creds_raw.startswith('"') and creds_raw.endswith('"'):
                creds_raw = creds_raw[1:-1]
                print("Removed surrounding quotes")
            
            # Replace escaped quotes if they exist
            creds_raw = creds_raw.replace('\\"', '"')
            print("Replaced escaped quotes")
            
            # Parse JSON
            creds_dict = json.loads(creds_raw)
            print("✓ Successfully parsed JSON")
            print(f"Keys in parsed JSON: {list(creds_dict.keys())}")
            
            # Create credentials
            print("\nCreating credentials object...")
            credentials = service_account.Credentials.from_service_account_info(
                creds_dict,
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            print("✓ Successfully created credentials")
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"Error position: {e.pos}")
            print(f"Line number: {e.lineno}")
            print(f"Column number: {e.colno}")
            return
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        print(f"Full error: {traceback.format_exc()}")

if __name__ == "__main__":
    test_drive_access()
