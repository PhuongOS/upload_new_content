# FILE: models/Facebook_Config.py
# Ánh xạ cấu trúc của tab "Facebook_Config" (Thông tin Page)

class FacebookConfModel:
    # Spreadsheet Information
    SPREADSHEET_ID = "1zFzHePIcOHXiWyAQRN7YOxIkE3kpDKwCuKMsdEe-snU"
    SHEET_NAME = "Facebook_Config"
    TAB_ID = 865071638

    # Column Index Mapping (0-indexed)
    COL_PAGE_NAME = 0
    COL_PAGE_ID = 1
    COL_ACCESS_TOKEN = 2

    @classmethod
    def to_dict(cls, row_values):
        """Chuyển đổi một hàng từ Sheets sang Dictionary"""
        data = row_values + [""] * (3 - len(row_values))
        return {
            "page_name": data[cls.COL_PAGE_NAME],
            "page_id": data[cls.COL_PAGE_ID],
            "access_token": data[cls.COL_ACCESS_TOKEN]
        }

    @classmethod
    def from_dict(cls, data_dict):
        """Chuyển đổi Dictionary ngược lại thành mảng Row"""
        row = [""] * 3
        row[cls.COL_PAGE_NAME] = data_dict.get("page_name", "")
        row[cls.COL_PAGE_ID] = data_dict.get("page_id", "")
        row[cls.COL_ACCESS_TOKEN] = data_dict.get("access_token", "")
        return row