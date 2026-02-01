from woocommerce import API

class WoocommercePublisher:
    def __init__(self, url, consumer_key, consumer_secret):
        self.wcapi = API(
            url=url,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
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
        data format: {
            "name": "...",
            "type": "simple",
            "regular_price": "...",
            "description": "...",
            "short_description": "...",
            "categories": [{"id": ...}],
            "images": [{"src": "..."}]
        }
        """
        try:
            res = self.wcapi.post("products", data)
            if res.status_code in [200, 201]:
                return {"success": True, "data": res.json()}
            return {"success": False, "error": res.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def upload_image_from_url(self, image_url):
        """
        WooCommerce tự động tải ảnh từ URL nếu truyền vào mảng images của products.
        Hàm này có thể dùng để kiểm tra hoặc xử lý riêng nếu cần.
        """
        pass
