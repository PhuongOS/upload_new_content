# FILE: models/media_calendar.py
# Ánh xạ cấu trúc của tab "Media_Calendar" trong Google Sheets

class MediaCalendarModel:
    # Spreadsheet Information
    SPREADSHEET_ID = "1zFzHePIcOHXiWyAQRN7YOxIkE3kpDKwCuKMsdEe-snU"
    SHEET_NAME = "Media_Calendar"
    TAB_ID = 2134289557

    # Column Index Mapping (0-indexed)
    COL_STT = 0
    COL_ID = 1
    COL_NAME = 2
    COL_LINK_ON_DRIVE = 3
    COL_CATEGORY = 4
    COL_YOUTUBE_CHANNELS = 5
    COL_CHANNEL_ID = 6
    COL_YOUTUBE_CALENDAR = 7
    COL_YT_POST_TYPE = 8
    COL_FACEBOOK_PAGES = 9
    COL_PAGE_ID = 10
    COL_FACEBOOK_CALENDAR = 11
    COL_POST_TYPES = 12
    COL_TIKTOK_ACCOUNTS = 13
    COL_ACCOUNT_ID = 14
    COL_TIKTOK_CALENDAR = 15
    COL_TIK_POST_TYPE = 16
    COL_CALENDAR = 17
    COL_SCRIP_ACTION = 18

    @classmethod
    def to_youtube_dict(cls, row_values):
        """Chuyển đổi dữ liệu sang định dạng tập trung vào Youtube"""
        data = row_values + [""] * (19 - len(row_values))
        return {
            "stt": data[cls.COL_STT],
            "id": data[cls.COL_ID],
            "name": data[cls.COL_NAME],
            "link_on_drive": data[cls.COL_LINK_ON_DRIVE],
            "category": data[cls.COL_CATEGORY],
            "youtube": {
                "channels": data[cls.COL_YOUTUBE_CHANNELS],
                "channel_id": data[cls.COL_CHANNEL_ID],
                "calendar": data[cls.COL_YOUTUBE_CALENDAR],
                "post_type": data[cls.COL_YT_POST_TYPE],
            },
            "general_calendar": data[cls.COL_CALENDAR],
            "scrip_action": data[cls.COL_SCRIP_ACTION]
        }

    @classmethod
    def to_facebook_dict(cls, row_values):
        """Chuyển đổi dữ liệu sang định dạng tập trung vào Facebook"""
        data = row_values + [""] * (19 - len(row_values))
        return {
            "stt": data[cls.COL_STT],
            "id": data[cls.COL_ID],
            "name": data[cls.COL_NAME],
            "link_on_drive": data[cls.COL_LINK_ON_DRIVE],
            "category": data[cls.COL_CATEGORY],
            "facebook": {
                "pages": data[cls.COL_FACEBOOK_PAGES],
                "page_id": data[cls.COL_PAGE_ID],
                "calendar": data[cls.COL_FACEBOOK_CALENDAR],
                "post_type": data[cls.COL_POST_TYPES],
            },
            "general_calendar": data[cls.COL_CALENDAR],
            "scrip_action": data[cls.COL_SCRIP_ACTION]
        }

    @classmethod
    def to_tiktok_dict(cls, row_values):
        """Chuyển đổi dữ liệu sang định dạng tập trung vào Tiktok"""
        data = row_values + [""] * (19 - len(row_values))
        return {
            "stt": data[cls.COL_STT],
            "id": data[cls.COL_ID],
            "name": data[cls.COL_NAME],
            "link_on_drive": data[cls.COL_LINK_ON_DRIVE],
            "category": data[cls.COL_CATEGORY],
            "tiktok": {
                "accounts": data[cls.COL_TIKTOK_ACCOUNTS],
                "account_id": data[cls.COL_ACCOUNT_ID],
                "calendar": data[cls.COL_TIKTOK_CALENDAR],
                "post_type": data[cls.COL_TIK_POST_TYPE],
            },
            "general_calendar": data[cls.COL_CALENDAR],
            "scrip_action": data[cls.COL_SCRIP_ACTION]
        }

    @classmethod
    def to_dict(cls, row_values):
        """Chuyển đổi toàn bộ dữ liệu trang tính sang Dictionary đầy đủ"""
        data = row_values + [""] * (19 - len(row_values))
        
        return {
            "stt": data[cls.COL_STT],
            "id": data[cls.COL_ID],
            "name": data[cls.COL_NAME],
            "link_on_drive": data[cls.COL_LINK_ON_DRIVE],
            "category": data[cls.COL_CATEGORY],
            "youtube": {
                "channels": data[cls.COL_YOUTUBE_CHANNELS],
                "channel_id": data[cls.COL_CHANNEL_ID],
                "calendar": data[cls.COL_YOUTUBE_CALENDAR],
                "post_type": data[cls.COL_YT_POST_TYPE],
            },
            "facebook": {
                "pages": data[cls.COL_FACEBOOK_PAGES],
                "page_id": data[cls.COL_PAGE_ID],
                "calendar": data[cls.COL_FACEBOOK_CALENDAR],
                "post_type": data[cls.COL_POST_TYPES],
            },
            "tiktok": {
                "accounts": data[cls.COL_TIKTOK_ACCOUNTS],
                "account_id": data[cls.COL_ACCOUNT_ID],
                "calendar": data[cls.COL_TIKTOK_CALENDAR],
                "post_type": data[cls.COL_TIK_POST_TYPE],
            },
            "general_calendar": data[cls.COL_CALENDAR],
            "scrip_action": data[cls.COL_SCRIP_ACTION]
        }

    @classmethod
    def from_dict(cls, data_dict):
        """Chuyển đổi một Dictionary ngược lại thành mảng để ghi xuống Sheets"""
        row = [""] * 19
        row[cls.COL_STT] = data_dict.get("stt", "")
        row[cls.COL_ID] = data_dict.get("id", "")
        row[cls.COL_NAME] = data_dict.get("name", "")
        row[cls.COL_LINK_ON_DRIVE] = data_dict.get("link_on_drive", "")
        row[cls.COL_CATEGORY] = data_dict.get("category", "")
        
        yt = data_dict.get("youtube", {})
        row[cls.COL_YOUTUBE_CHANNELS] = yt.get("channels", "")
        row[cls.COL_CHANNEL_ID] = yt.get("channel_id", "")
        row[cls.COL_YOUTUBE_CALENDAR] = yt.get("calendar", "")
        row[cls.COL_YT_POST_TYPE] = yt.get("post_type", "")
        
        fb = data_dict.get("facebook", {})
        row[cls.COL_FACEBOOK_PAGES] = fb.get("pages", "")
        row[cls.COL_PAGE_ID] = fb.get("page_id", "")
        row[cls.COL_FACEBOOK_CALENDAR] = fb.get("calendar", "")
        row[cls.COL_POST_TYPES] = fb.get("post_type", "")
        
        tk = data_dict.get("tiktok", {})
        row[cls.COL_TIKTOK_ACCOUNTS] = tk.get("accounts", "")
        row[cls.COL_ACCOUNT_ID] = tk.get("account_id", "")
        row[cls.COL_TIKTOK_CALENDAR] = tk.get("calendar", "")
        row[cls.COL_TIK_POST_TYPE] = tk.get("post_type", "")
        
        row[cls.COL_CALENDAR] = data_dict.get("general_calendar", "")
        row[cls.COL_SCRIP_ACTION] = data_dict.get("scrip_action", "")
        
        return row
