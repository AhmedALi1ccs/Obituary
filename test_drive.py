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
        print("Processing credentials string...")
        
        # Remove any wrapping quotes and unescape the JSON
        if creds_raw.startswith('"') and creds_raw.endswith('"'):
            creds_raw = creds_raw[1:-1]
        
        # Create test DataFrame
        test_data = pd.DataFrame({
            'test_column': ['test_value1', 'test_value2']
        })
        
        # Save test file
        test_filename = 'test_file.csv'
        test_data.to_csv(test_filename, index=False)
        
        try:
            # Parse the processed JSON string
            creds_dict = json.loads(creds_raw)
            print("✓ Successfully parsed JSON")
            
            print("\nCreating credentials object...")
            credentials = service_account.Credentials.from_service_account_info(
                creds_dict,
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            print("✓ Successfully created credentials")
            
            # Create Drive service
            print("\nCreating Drive service...")
            drive_service = build('drive', 'v3', credentials=credentials)
            print("✓ Drive service created")
            
            # Test folder access
            folder_id = "1Vn02sVpKU9fGLGG3fo-ZgngWXKhntNvb"
            print(f"\nTesting access to folder {folder_id}...")
            folder = drive_service.files().get(fileId=folder_id).execute()
            print(f"✓ Successfully accessed folder: {folder.get('name', 'unknown')}")
            
            # Upload test file
            print("\nAttempting to upload test file...")
            file_metadata = {
                'name': 'test_upload.csv',
                'parents': [folder_id]
            }
            
            media = MediaFileUpload(
                test_filename,
                mimetype='text/csv',
                resumable=True
            )
            
            file = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,webViewLink'
            ).execute()
            
            print("\n=== Upload Successful ===")
            print(f"File Name: {file.get('name')}")
            print(f"File ID: {file.get('id')}")
            print(f"Web Link: {file.get('webViewLink')}")
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"Error position: {e.pos}")
            print(f"Line number: {e.lineno}")
            print(f"Column number: {e.colno}")
            print("\nTrying to diagnose the issue...")
            print(f"Characters around error position: {creds_raw[max(0, e.pos-10):e.pos+10]}")
            return
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        print(f"Full error: {traceback.format_exc()}")
        
    finally:
        # Cleanup
        if os.path.exists(test_filename):
            os.remove(test_filename)
            print("\n✓ Cleaned up test file")

if __name__ == "__main__":
    test_drive_access()
