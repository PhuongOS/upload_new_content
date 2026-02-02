# FILE: models/Haravan_db.py
# Ánh xạ cấu trúc của tab "Haravan_db"

class HaravanDbModel:
    # Spreadsheet Information
    SPREADSHEET_ID = "1zFzHePIcOHXiWyAQRN7YOxIkE3kpDKwCuKMsdEe-snU"
    SHEET_NAME = "Haravan_db"
    TAB_ID = 151755428

    # Column Index Mapping (0-indexed)
    COL_STT = 0
    COL_PRODUCT_TITLE = 1
    COL_REGULAR_PRICE = 2
    COL_SALE_PRICE = 3
    COL_DESCRIPTION = 4
    COL_SHORT_DESCRIPTION = 5
    COL_PRODUCT_TYPE = 6   # Loại sản phẩm
    COL_VENDOR = 7         # Nhà cung cấp
    COL_TAGS = 8           # Tags (ngăn cách dấu phẩy)
    COL_IMAGES_URL = 9     # Link ảnh (Drive hoặc Direct)
    COL_STATUS = 10        # PENDING, SUCCESS, ERROR
    COL_HARAVAN_ID = 11    # ID sản phẩm sau khi tạo
    COL_HARAVAN_LINK = 12  # Link sản phẩm trên Haravan

    @classmethod
    def to_dict(cls, row_values):
        """Chuyển đổi một hàng sang Dictionary"""
        data = row_values + [""] * (13 - len(row_values))
        return {
            "stt": data[cls.COL_STT],
            "title": data[cls.COL_PRODUCT_TITLE],
            "regular_price": data[cls.COL_REGULAR_PRICE],
            "sale_price": data[cls.COL_SALE_PRICE],
            "description": data[cls.COL_DESCRIPTION],
            "short_description": data[cls.COL_SHORT_DESCRIPTION],
            "product_type": data[cls.COL_PRODUCT_TYPE],
            "vendor": data[cls.COL_VENDOR],
            "tags": data[cls.COL_TAGS],
            "images": data[cls.COL_IMAGES_URL],
            "status": data[cls.COL_STATUS],
            "haravan_id": data[cls.COL_HARAVAN_ID],
            "haravan_link": data[cls.COL_HARAVAN_LINK]
        }

    @classmethod
    def from_dict(cls, data):
        """Chuyển đổi từ Dictionary (Frontend gửi lên) thành Row Array (để lưu vào Sheet)"""
        row = [""] * 13
        row[cls.COL_STT] = data.get("stt", "")
        # Support both 'product_title' (from JS) and 'title' (standard)
        row[cls.COL_PRODUCT_TITLE] = data.get("product_title", "") or data.get("title", "")
        row[cls.COL_REGULAR_PRICE] = data.get("regular_price", "")
        row[cls.COL_SALE_PRICE] = data.get("sale_price", "")
        
        # Support 'description_html' (from JS) and 'description'
        row[cls.COL_DESCRIPTION] = data.get("description_html", "") or data.get("description", "")
        row[cls.COL_SHORT_DESCRIPTION] = data.get("short_description", "")
        
        row[cls.COL_PRODUCT_TYPE] = data.get("product_type", "")
        row[cls.COL_VENDOR] = data.get("vendor", "")
        row[cls.COL_TAGS] = data.get("tags", "")
        
        # 'source_url' from JS might be intended for reference, mapping it to images if it's an image link
        # or separate column if we had one. For now, map generic 'images' key or 'source_url' if appropriate?
        # Actually Haravan_db logic usually puts uploaded images here.
        # Let's just map 'images' key.
        row[cls.COL_IMAGES_URL] = data.get("images", "")
        
        row[cls.COL_STATUS] = data.get("status", "PENDING")
        row[cls.COL_HARAVAN_ID] = data.get("haravan_id", "")
        
        # Often we want to save the source link somewhere.
        # If 'source_url' is passed and 'haravan_link' is empty, maybe store it there temporarily?
        # Or just rely on 'haravan_link'
        row[cls.COL_HARAVAN_LINK] = data.get("haravan_link", "") or data.get("source_url", "")
        
        return row
