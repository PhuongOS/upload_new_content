
import sys
import os
import requests
from services.sheet_service import SheetService
from models.Haravan_Config import HaravanConfModel

# Hack to allow imports from parent directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_connection():
    print("--- Haravan Connection Test ---")
    
    # 1. Read Config from Sheet
    print("Reading configuration from Google Sheet...")
    try:
        # Assuming SheetService can generic read by Sheet Name
        # We need to ensure SheetService is importable and working.
        # Based on previous context, SheetService.get_all_rows(sheet_name) works.
        rows = SheetService.get_all_rows(HaravanConfModel.SHEET_NAME)
        
        if not rows:
            print("❌ Error: Configuration sheet is empty.")
            return

        # Get first row of config
        config = rows[0]
        shop_url = config.get("shop_url")
        access_token = config.get("access_token") # Assuming to_dict maps this key

        # If to_dict logic in SheetService uses the Model, check keys.
        # Actually SheetService usually returns list of dicts based on internal mapping 
        # OR returns raw values. Let's check how SheetService works quickly or assume Model mapping?
        # Let's debug print first.
        
        print(f"Shop URL found: {shop_url}")
        print(f"Token found: {'*' * 5}{access_token[-5:] if access_token else 'None'}")

        if not shop_url or not access_token:
            print("❌ Error: Missing Shop URL or Access Token in the first row.")
            return

        # 2. Call Haravan API (Get Shop Info)
        # Endpoint: https://{shop}.myharavan.com/admin/shop.json
        # Headers: Authorization: Bearer {access_token} ?? 
        # Check Haravan Doc: Usually X-Haravan-Access-Token or Bearer.
        # Most Shopify-like uses X-Shopify-Access-Token, let's try standard Bearer first or header specific.
        # Haravan often uses Bearer.
        
        # Clean URL
        shop_url = shop_url.rstrip('/')
        if not shop_url.startswith('https://'):
            shop_url = f'https://{shop_url}'
            
        endpoint = f"{shop_url}/admin/shop.json"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        print(f"Connecting to {endpoint}...")
        response = requests.get(endpoint, headers=headers, timeout=10)
        
        if response.status_code == 200:
            shop_data = response.json().get('shop', {})
            print("✅ Connection Successful!")
            print(f"Shop Name: {shop_data.get('name')}")
            print(f"Email: {shop_data.get('email')}")
            print(f"Domain: {shop_data.get('domain')}")
        else:
            print(f"❌ Connection Failed. Status Code: {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"❌ Exception occurred: {e}")

if __name__ == "__main__":
    test_connection()
