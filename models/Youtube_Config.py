# FILE: models/Youtube_Config.py
# Ánh xạ cấu trúc của tab "Youtube_Config" (Thông tin Kênh)

class YoutubeConfModel:
    # Spreadsheet Information
    SPREADSHEET_ID = "1zFzHePIcOHXiWyAQRN7YOxIkE3kpDKwCuKMsdEe-snU"
    SHEET_NAME = "Youtube_Config"
    TAB_ID = 661049598

    # Column Index Mapping (0-indexed)
    COL_CHANNEL_NAME = 0
    COL_CHANNEL_ID = 1
    COL_GMAIL_CHANNEL = 2
    COL_ACCOUNT_ID = 3  # [NEW] ID tài khoản Google liên kết

    @classmethod
    def to_dict(cls, row_values):
        """Chuyển đổi một hàng từ Sheets sang Dictionary"""
        data = row_values + [""] * (4 - len(row_values))
        return {
            "channel_name": data[cls.COL_CHANNEL_NAME],
            "channel_id": data[cls.COL_CHANNEL_ID],
            "gmail_channel": data[cls.COL_GMAIL_CHANNEL],
            "account_id": data[cls.COL_ACCOUNT_ID]  # [NEW]
        }

    @classmethod
    def from_dict(cls, data_dict):
        """Chuyển đổi Dictionary ngược lại thành mảng Row"""
        row = [""] * 4
        row[cls.COL_CHANNEL_NAME] = data_dict.get("channel_name", "")
        row[cls.COL_CHANNEL_ID] = data_dict.get("channel_id", "")
        row[cls.COL_GMAIL_CHANNEL] = data_dict.get("gmail_channel", "")
        row[cls.COL_ACCOUNT_ID] = data_dict.get("account_id", "")  # [NEW]
        return row

