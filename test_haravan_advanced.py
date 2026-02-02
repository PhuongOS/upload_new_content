
from services.sheet_service import SheetService
from post_service.haravan_publisher import HaravanPublisher
import os

# Mock Config or Load from Sheet
def test_advanced_features():
    print("--- Testing Haravan Advanced Features ---")
    
    # 1. Load Config
    print("Loading config from Haravan_Config sheet...")
    try:
        data = SheetService.get_all_rows("Haravan_Config")
        if not data:
            print("RED: No config found in Haravan_Config.")
            return

        config = data[0]
        shop_url = config.get("shop_url")
        access_token = config.get("access_token")

        if not shop_url or not access_token:
            print("RED: Missing Shop URL or Access Token.")
            return

        print(f"Config Loaded: {shop_url}")
        publisher = HaravanPublisher(shop_url, access_token)

        # 2. Test Get Collections
        print("\n--- Testing Get Custom Collections ---")
        res = publisher.get_custom_collections()
        if res["success"]:
            collections = res["data"].get("custom_collections", [])
            print(f"GREEN: Found {len(collections)} custom collections.")
            for c in collections[:3]:
                print(f" - {c['title']} (ID: {c['id']})")
        else:
            print(f"RED: Failed to get custom collections: {res.get('error')}")

        print("\n--- Testing Get Smart Collections ---")
        res = publisher.get_smart_collections()
        if res["success"]:
            collections = res["data"].get("smart_collections", [])
            print(f"GREEN: Found {len(collections)} smart collections.")
            for c in collections[:3]:
                print(f" - {c['title']} (ID: {c['id']})")
        else:
            print(f"RED: Failed to get smart collections: {res.get('error')}")

        # 3. Test Get Product Types
        print("\n--- Testing Get Product Types (Scanning products) ---")
        res = publisher.get_product_types()
        if res["success"]:
            print(f"GREEN: Found Types: {res['types']}")
            print(f"GREEN: Found Vendors: {res['vendors']}")
        else:
            print(f"RED: Failed to get product types: {res.get('error')}")

        # 4. (Optional) Test Image Upload needs a Product ID
        # We can fetch the first product to test
        # res_prod = publisher._make_request("products.json", method="GET", params={"limit": 1})
        # if res_prod["success"] and res_prod["data"]["products"]:
        #    p_id = res_prod["data"]["products"][0]["id"]
        #    print(f"\n--- Testing Image Upload on Product {p_id} ---")
        #    # simple 1x1 pixel red dot base64
        #    b64 = "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
        #    res_img = publisher.upload_image_base64(p_id, b64, "pixel_test.gif")
        #    if res_img["success"]:
        #        print(f"GREEN: Image Uploaded: {res_img['data']['image']['src']}")
        #    else:
        #        print(f"RED: Image Upload Failed: {res_img.get('error')}")

    except Exception as e:
        print(f"RED: Exception occurred: {e}")

if __name__ == "__main__":
    test_advanced_features()
