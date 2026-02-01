from woocommerce import API

class WoocommercePublisher:
    def __init__(self, url, consumer_key, consumer_secret, wp_user=None, wp_app_pass=None):
        self.url = url.rstrip('/')
        self.consumer_key = consumer_key.strip()
        self.consumer_secret = consumer_secret.strip()
        # WordPress Application Password thường có khoảng trắng để dễ đọc, nhưng khi gửi BasicAuth cần xóa đi
        self.wp_user = wp_user.strip() if wp_user else None
        self.wp_app_pass = wp_app_pass.replace(' ', '').strip() if wp_app_pass else None
        
        self.wcapi = API(
            url=self.url,
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret,
            version="wc/v3",
            timeout=30
        )

    def get_categories(self):
        """Lấy danh sách category từ WooCommerce"""
        try:
            res = self.wcapi.get("products/categories", params={"per_page": 100})
            if res.status_code == 200:
                return {"success": True, "data": res.json()}
            return {"success": False, "error": res.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_product(self, data):
        """
        Tạo sản phẩm mới trên WooCommerce.
        """
        try:
            res = self.wcapi.post("products", data)
            if res.status_code in [200, 201]:
                return {"success": True, "data": res.json()}
            return {"success": False, "error": res.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def upload_media_bytes(self, image_bytes, filename, content_type='image/jpeg'):
        """
        Upload bytes trực tiếp lên WordPress Media Library.
        """
        import requests
        from requests.auth import HTTPBasicAuth

        try:
            media_endpoint = f"{self.url}/wp-json/wp/v2/media"
            
            headers = {
                'Content-Type': content_type,
                'Content-Disposition': f'attachment; filename={filename}'
            }

            # Ưu tiên sử dụng WP Application Password nếu có
            auth = None
            if self.wp_user and self.wp_app_pass:
                auth = HTTPBasicAuth(self.wp_user, self.wp_app_pass)
            else:
                auth = HTTPBasicAuth(self.consumer_key, self.consumer_secret)

            upload_res = requests.post(
                media_endpoint,
                data=image_bytes,
                headers=headers,
                auth=auth,
                timeout=30
            )

            if upload_res.status_code in [200, 201]:
                media_info = upload_res.json()
                return {"success": True, "media_id": media_info.get("id"), "url": media_info.get("source_url")}
            
            return {"success": False, "error": f"WordPress Media API Error: {upload_res.text}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def upload_media_binary(self, image_url, filename):
        """
        Tải ảnh từ URL về local và upload thẳng lên WordPress Media Library qua REST API.
        Giúp vượt qua lỗi 'Ảnh không hợp lệ' khi sideload URL từ xa.
        """
        import requests
        try:
            # 1. Tải ảnh về memory
            resp = requests.get(image_url, timeout=20)
            if resp.status_code != 200:
                return {"success": False, "error": f"Không thể tải ảnh từ URL (HTTP {resp.status_code})"}
            
            image_data = resp.content
            content_type = resp.headers.get('Content-Type', 'image/jpeg')

            # 2. Upload lên WordPress Media Library sử dụng hàm byte
            return self.upload_media_bytes(image_data, filename, content_type)

        except Exception as e:
            return {"success": False, "error": str(e)}
