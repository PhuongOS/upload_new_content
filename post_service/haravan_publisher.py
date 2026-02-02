import requests
import json
import base64

class HaravanPublisher:
    """
    Service to interact with Haravan API for Product Management.
    """
    def __init__(self, shop_url, access_token):
        self.shop_url = shop_url.rstrip('/')
        if not self.shop_url.startswith('https://'):
            self.shop_url = f'https://{self.shop_url}'
        
        self.access_token = access_token
        self.base_url = f"{self.shop_url}/admin"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def _make_request(self, endpoint, method="POST", data=None, params=None):
        url = f"{self.base_url}/{endpoint}"
        try:
            if method == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=30)
            elif method == "GET":
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
            elif method == "PUT":
                response = requests.put(url, headers=self.headers, json=data, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers, timeout=30)
            
            # Haravan returns 200 or 201 for success
            if response.status_code in [200, 201]:
                return {"success": True, "data": response.json()}
            
            return {"success": False, "error": f"{response.status_code} - {response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_product(self, product_data):
        """
        Create a new product on Haravan.
        Payload structure matches Haravan Product API.
        """
        payload = {"product": product_data}
        return self._make_request("products.json", method="POST", data=payload)

    def upload_image_from_url(self, product_id, image_url):
        """
        Add an image to a product via URL.
        """
        payload = {
            "image": {
                "src": image_url
            }
        }
        return self._make_request(f"products/{product_id}/images.json", method="POST", data=payload)
    
    def get_product(self, product_id):
        return self._make_request(f"products/{product_id}.json", method="GET")

    # --- ADVANCED METHODS ---

    def get_custom_collections(self):
        """Fetch custom collections (Nhóm sản phẩm thủ công)"""
        return self._make_request("custom_collections.json", method="GET")

    def get_smart_collections(self):
        """Fetch smart collections (Nhóm sản phẩm tự động)"""
        return self._make_request("smart_collections.json", method="GET")

    def get_product_types(self):
        """
        Fetch list of product types and vendors from recent products.
        Haravan does not have a dedicated endpoint for this, so we scan recent 50 products.
        """
        res = self._make_request("products.json", method="GET", params={"limit": 50, "fields": "product_type,vendor"})
        if res["success"]:
            products = res["data"].get("products", [])
            types = list(set([p.get("product_type") for p in products if p.get("product_type")]))
            vendors = list(set([p.get("vendor") for p in products if p.get("vendor")]))
            return {"success": True, "types": sorted(types), "vendors": sorted(vendors)}
        return res

    def upload_image_base64(self, product_id, image_bytes_or_base64, filename="image.jpg"):
        """
        Upload image using Base64 attachment.
        If image_bytes_or_base64 is bytes, it converts to base64 string.
        """
        if isinstance(image_bytes_or_base64, bytes):
            b64_str = base64.b64encode(image_bytes_or_base64).decode('utf-8')
        else:
            b64_str = image_bytes_or_base64

        payload = {
            "image": {
                "attachment": b64_str,
                "filename": filename
            }
        }
        return self._make_request(f"products/{product_id}/images.json", method="POST", data=payload)

    def add_product_to_collection(self, product_id, collection_id):
        """Add a product to a custom collection"""
        payload = {
            "collect": {
                "product_id": product_id,
                "collection_id": collection_id
            }
        }
        return self._make_request("collects.json", method="POST", data=payload)
