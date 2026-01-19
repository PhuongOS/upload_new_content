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

    @classmethod
    def to_dict(cls, row_values):
        """Chuyển đổi một hàng từ Sheets sang Dictionary"""
        data = row_values + [""] * (3 - len(row_values))
        return {
            "channel_name": data[cls.COL_CHANNEL_NAME],
            "channel_id": data[cls.COL_CHANNEL_ID],
            "gmail_channel": data[cls.COL_GMAIL_CHANNEL]
        }

    @classmethod
    def from_dict(cls, data_dict):
        """Chuyển đổi Dictionary ngược lại thành mảng Row"""
        row = [""] * 3
        row[cls.COL_CHANNEL_NAME] = data_dict.get("channel_name", "")
        row[cls.COL_CHANNEL_ID] = data_dict.get("channel_id", "")
        row[cls.COL_GMAIL_CHANNEL] = data_dict.get("gmail_channel", "")
        return row
