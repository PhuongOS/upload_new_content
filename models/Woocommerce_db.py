# FILE: models/Woocommerce_db.py
# Ánh xạ cấu trúc của tab "Woocommerce_db"

class WoocommerceDbModel:
    # Spreadsheet Information
    SPREADSHEET_ID = "1zFzHePIcOHXiWyAQRN7YOxIkE3kpDKwCuKMsdEe-snU"
    SHEET_NAME = "Woocommerce_db"
    TAB_ID = 1456760713

    # Column Index Mapping (0-indexed)
    COL_STT = 0
    COL_PRODUCT_TITLE = 1
    COL_REGULAR_PRICE = 2
    COL_SALE_PRICE = 3
    COL_DESCRIPTION = 4
    COL_SHORT_DESCRIPTION = 5
    COL_CATEGORIES = 6
    COL_IMAGES_URL = 7
    COL_STATUS = 8 # SCHEDULED, SUCCESS, ERROR
    COL_CALENDAR = 9
    COL_COMPLETION_TIME = 10
    COL_WC_PRODUCT_ID = 11
    COL_WC_LINK = 12
    COL_SOURCE_URL = 13

    @classmethod
    def to_dict(cls, row_values):
        """Chuyển đổi một hàng sang Dictionary"""
        data = row_values + [""] * (14 - len(row_values))
        return {
            "stt": data[cls.COL_STT],
            "title": data[cls.COL_PRODUCT_TITLE],
            "regular_price": data[cls.COL_REGULAR_PRICE],
            "sale_price": data[cls.COL_SALE_PRICE],
            "description": data[cls.COL_DESCRIPTION],
            "short_description": data[cls.COL_SHORT_DESCRIPTION],
            "categories": data[cls.COL_CATEGORIES],
            "images": data[cls.COL_IMAGES_URL],
            "status": data[cls.COL_STATUS],
            "calendar": data[cls.COL_CALENDAR],
            "completion_time": data[cls.COL_COMPLETION_TIME],
            "wc_id": data[cls.COL_WC_PRODUCT_ID],
            "wc_link": data[cls.COL_WC_LINK],
            "source_url": data[cls.COL_SOURCE_URL]
        }

    @classmethod
    def from_dict(cls, d):
        """Chuyển đổi Dictionary sang mảng hàng"""
        row = [""] * 14
        row[cls.COL_STT] = d.get("stt", "")
        row[cls.COL_PRODUCT_TITLE] = d.get("title", "")
        row[cls.COL_REGULAR_PRICE] = d.get("regular_price", "")
        row[cls.COL_SALE_PRICE] = d.get("sale_price", "")
        row[cls.COL_DESCRIPTION] = d.get("description", "")
        row[cls.COL_SHORT_DESCRIPTION] = d.get("short_description", "")
        row[cls.COL_CATEGORIES] = d.get("categories", "")
        row[cls.COL_IMAGES_URL] = d.get("images", "")
        row[cls.COL_STATUS] = d.get("status", "")
        row[cls.COL_CALENDAR] = d.get("calendar", "")
        row[cls.COL_COMPLETION_TIME] = d.get("completion_time", "")
        row[cls.COL_WC_PRODUCT_ID] = d.get("wc_id", "")
        row[cls.COL_WC_LINK] = d.get("wc_link", "")
        row[cls.COL_SOURCE_URL] = d.get("source_url", "")
        return row
