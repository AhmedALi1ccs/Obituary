import os
import json

def get_google_credentials():
    """Get Google credentials from environment variable"""
    try:
        creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
        if creds_json:
            return json.loads(creds_json)
        else:
            print("No Google credentials found in environment")
            return None
    except Exception as e:
        print(f"Error parsing Google credentials: {e}")
        return None
