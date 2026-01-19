# FILE: models/Facebook_db.py
# Ánh xạ cấu trúc của tab "Facebook_db" trong Google Sheets

class FacebookDbModel:
    # Spreadsheet Information
    SPREADSHEET_ID = "1zFzHePIcOHXiWyAQRN7YOxIkE3kpDKwCuKMsdEe-snU"
    SHEET_NAME = "Facebook_db"
    TAB_ID = 1309972772

    # Column Index Mapping (0-indexed)
    COL_STT = 0
    COL_ID_MEDIA_ON_DRIVE = 1
    COL_NAME_VIDEO = 2
    COL_VIDEO_URL = 3
    COL_TYPE_CONTEN = 4
    COL_HOOK = 5
    COL_BODY_CONTENT = 6
    COL_CTA_TEXT = 7
    COL_CONTACT_ME = 8
    COL_PRODUCT_HASHTAG = 9
    COL_BRAND_HASHTAG = 10
    COL_THUMBNAIL_URL = 11
    COL_PAGE_NAME = 12
    COL_PAGE_ID = 13
    COL_ACCESS_TOKEN = 14
    COL_POST_TYPE = 15
    COL_CALENDAR = 16
    COL_COMPLETION_TIME = 17
    COL_LINK_POST_ON_FACEBOOK = 18
    COL_POST_ID = 19
    COL_CURRENT_STATUS = 20
    COL_SCRIP_ACTION = 21

    @classmethod
    def to_dict(cls, row_values):
        """Chuyển đổi một hàng (mảng) từ Google Sheets sang dạng Dictionary"""
        # Đảm bảo mảng đủ độ dài (22 cột)
        data = row_values + [""] * (22 - len(row_values))
        
        return {
            "stt": data[cls.COL_STT],
            "media_drive_id": data[cls.COL_ID_MEDIA_ON_DRIVE],
            "video_name": data[cls.COL_NAME_VIDEO],
            "video_url": data[cls.COL_VIDEO_URL],
            "content_type": data[cls.COL_TYPE_CONTEN],
            "hook": data[cls.COL_HOOK],
            "body": data[cls.COL_BODY_CONTENT],
            "cta": data[cls.COL_CTA_TEXT],
            "contact": data[cls.COL_CONTACT_ME],
            "product_hashtags": data[cls.COL_PRODUCT_HASHTAG],
            "brand_hashtags": data[cls.COL_BRAND_HASHTAG],
            "thumbnail_url": data[cls.COL_THUMBNAIL_URL],
            "page": {
                "name": data[cls.COL_PAGE_NAME],
                "id": data[cls.COL_PAGE_ID],
                "access_token": data[cls.COL_ACCESS_TOKEN]
            },
            "post_type": data[cls.COL_POST_TYPE],
            "calendar": data[cls.COL_CALENDAR],
            "completion_time": data[cls.COL_COMPLETION_TIME],
            "fb_link": data[cls.COL_LINK_POST_ON_FACEBOOK],
            "fb_post_id": data[cls.COL_POST_ID],
            "status": data[cls.COL_CURRENT_STATUS],
            "scrip_action": data[cls.COL_SCRIP_ACTION]
        }

    @classmethod
    def from_dict(cls, data_dict):
        """Chuyển đổi một Dictionary ngược lại thành mảng để ghi xuống Sheets"""
        row = [""] * 22
        row[cls.COL_STT] = data_dict.get("stt", "")
        row[cls.COL_ID_MEDIA_ON_DRIVE] = data_dict.get("media_drive_id", "")
        row[cls.COL_NAME_VIDEO] = data_dict.get("video_name", "")
        row[cls.COL_VIDEO_URL] = data_dict.get("video_url", "")
        row[cls.COL_TYPE_CONTEN] = data_dict.get("content_type", "")
        row[cls.COL_HOOK] = data_dict.get("hook", "")
        row[cls.COL_BODY_CONTENT] = data_dict.get("body", "")
        row[cls.COL_CTA_TEXT] = data_dict.get("cta", "")
        row[cls.COL_CONTACT_ME] = data_dict.get("contact", "")
        row[cls.COL_PRODUCT_HASHTAG] = data_dict.get("product_hashtags", "")
        row[cls.COL_BRAND_HASHTAG] = data_dict.get("brand_hashtags", "")
        row[cls.COL_THUMBNAIL_URL] = data_dict.get("thumbnail_url", "")
        
        page = data_dict.get("page", {})
        row[cls.COL_PAGE_NAME] = page.get("name", "")
        row[cls.COL_PAGE_ID] = page.get("id", "")
        row[cls.COL_ACCESS_TOKEN] = page.get("access_token", "")
        
        row[cls.COL_POST_TYPE] = data_dict.get("post_type", "")
        row[cls.COL_CALENDAR] = data_dict.get("calendar", "")
        row[cls.COL_COMPLETION_TIME] = data_dict.get("completion_time", "")
        row[cls.COL_LINK_POST_ON_FACEBOOK] = data_dict.get("fb_link", "")
        row[cls.COL_POST_ID] = data_dict.get("fb_post_id", "")
        row[cls.COL_CURRENT_STATUS] = data_dict.get("status", "")
        row[cls.COL_SCRIP_ACTION] = data_dict.get("scrip_action", "")
        
        return row