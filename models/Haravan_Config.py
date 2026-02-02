# FILE: models/Haravan_Config.py
# Ánh xạ cấu trúc của tab "Haravan_Config"

class HaravanConfModel:
    # Spreadsheet Information
    SPREADSHEET_ID = "1zFzHePIcOHXiWyAQRN7YOxIkE3kpDKwCuKMsdEe-snU"
    SHEET_NAME = "Haravan_Config"
    TAB_ID = 172995929

    # Column Index Mapping (0-indexed)
    COL_SHOP_URL = 0          # URL của cửa hàng (VD: https://shop.myharavan.com)
    COL_ACCESS_TOKEN = 1      # Access Token (Private App)

    @classmethod
    def to_dict(cls, row_values):
        """Chuyển đổi một hàng sang Dictionary"""
        # Padding nếu thiếu cột
        data = row_values + [""] * (2 - len(row_values))
        return {
            "shop_url": data[cls.COL_SHOP_URL],
            "access_token": data[cls.COL_ACCESS_TOKEN]
        }
