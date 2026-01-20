class HistoryDbModel:
    """
    Model ánh xạ cho bảng Published_History trên Google Sheets.
    Cấu trúc bảng: [
        "Id_media_on_drive", "Name_video", "Type_conten", "Page name", "Page Id", 
        "Access Token", "Facebook_Post_Id", "Channel_name", "Channel Id", "Gmail_channel", 
        "Youtube_Post_Id", "Thumbnail", "Link_On_Platfrom", "Status"
    ]
    """
    
    SPREADSHEET_ID = "1zFzHePIcOHXiWyAQRN7YOxIkE3kpDKwCuKMsdEe-snU"
    TAB_ID = 1820788510  # Đã cập nhật đúng GID từ hệ thống

    @staticmethod
    def to_dict(row):
        """Chuyển đổi từ mảng hàng (row) sang dictionary"""
        return {
            "Id_media_on_drive": row[0] if len(row) > 0 else "",
            "Name_video": row[1] if len(row) > 1 else "",
            "Type_conten": row[2] if len(row) > 2 else "",
            "Page_name": row[3] if len(row) > 3 else "",
            "Page_Id": row[4] if len(row) > 4 else "",
            "Access_token": row[5] if len(row) > 5 else "",
            "Facebook_Post_Id": row[6] if len(row) > 6 else "",
            "Channel_name": row[7] if len(row) > 7 else "",
            "Channel_Id": row[8] if len(row) > 8 else "",
            "Gmail_channel": row[9] if len(row) > 9 else "",
            "Youtube_Post_Id": row[10] if len(row) > 10 else "",
            "Thumbnail": row[11] if len(row) > 11 else "",
            "Link_On_Platfrom": row[12] if len(row) > 12 else "",
            "Status": row[13] if len(row) > 13 else ""
        }

    @staticmethod
    def from_dict(data):
        """Chuyển đổi từ dictionary sang mảng hàng (row) để lưu vào Sheets"""
        return [
            data.get("Id_media_on_drive", ""),
            data.get("Name_video", ""),
            data.get("Type_conten", ""),
            data.get("Page_name", ""),
            data.get("Page_Id", ""),
            data.get("Access_token", ""),
            data.get("Facebook_Post_Id", ""),
            data.get("Channel_name", ""),
            data.get("Channel_Id", ""),
            data.get("Gmail_channel", ""),
            data.get("Youtube_Post_Id", ""),
            data.get("Thumbnail", ""),
            data.get("Link_On_Platfrom", ""),
            data.get("Status", "SUCCESS")
        ]
