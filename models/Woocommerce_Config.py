# FILE: models/Woocommerce_Config.py
# Ánh xạ cấu trúc của tab "Woocommerce_Config"

class WoocommerceConfModel:
    # Spreadsheet Information (Dùng chung bộ với FB/YT)
    SPREADSHEET_ID = "1zFzHePIcOHXiWyAQRN7YOxIkE3kpDKwCuKMsdEe-snU"
    SHEET_NAME = "Woocommerce_Config"
    TAB_ID = 809605027
    
    # Column Index Mapping
    COL_SITE_URL = 0
    COL_CONSUMER_KEY = 1
    COL_CONSUMER_SECRET = 2

    @classmethod
    def to_dict(cls, row_values):
        """Chuyển đổi một hàng từ Sheets sang Dictionary"""
        data = row_values + [""] * (3 - len(row_values))
        return {
            "site_url": data[cls.COL_SITE_URL],
            "consumer_key": data[cls.COL_CONSUMER_KEY],
            "consumer_secret": data[cls.COL_CONSUMER_SECRET]
        }

    @classmethod
    def from_dict(cls, data_dict):
        """Chuyển đổi Dictionary ngược lại thành mảng Row"""
        row = [""] * 3
        row[cls.COL_SITE_URL] = data_dict.get("site_url", "")
        row[cls.COL_CONSUMER_KEY] = data_dict.get("consumer_key", "")
        row[cls.COL_CONSUMER_SECRET] = data_dict.get("consumer_secret", "")
        return row
