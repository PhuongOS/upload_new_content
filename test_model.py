import json
import sys
import os

# Thêm đường dẫn để có thể import từ thư mục hiện tại
sys.path.append(os.getcwd())

from models.media_calendar import MediaCalendarModel

def test_media_calendar_model():
    print("--- ĐANG KIỂM TRA MEDIA CALENDAR MODEL ---\n")

    # 1. Giả lập một hàng dữ liệu thô từ Google Sheets
    raw_row = [
        "1",                                       # STT
        "ID_001",                                  # Id
        "Video Test Model",                        # Name
        "https://drive.google.com/test",           # Link_on_drive
        "Video",                                   # Category
        "Youtube Channel 1",                       # Youtube_channels
        "UC_123",                                  # Channel_Id
        "2026-01-01",                              # Youtube_calendar
        "Shorts",                                  # YT_Post_type
        "FB Page 1",                               # Facebook_pages
        "FB_456",                                  # Page_Id
        "2026-01-02",                              # Facebook_calendar
        "Video",                                   # POST_TYPE (Facebook)
        "TikTok Acc 1",                            # Tiktok_accounts
        "TK_789",                                  # Account_Id
        "2026-01-03",                              # Tiktok_calendar
        "Video",                                   # Tik_Post_type
        "2026-01-04",                              # Calendar
        "Run Script"                               # Scrip_action
    ]

    print("Step 1: Raw row data:")
    print(raw_row)
    print("\n-------------------\n")

    # 2. Test to_dict (Chuyển sang Dictionary đầy đủ)
    print("Step 2: Testing to_dict()...")
    data_dict = MediaCalendarModel.to_dict(raw_row)
    assert data_dict["name"] == "Video Test Model"
    assert "youtube" in data_dict and "facebook" in data_dict and "tiktok" in data_dict
    print("✅ to_dict() thành công (Đầy đủ dữ liệu)")

    # 3. Test to_youtube_dict
    print("\nStep 3: Testing to_youtube_dict()...")
    yt_dict = MediaCalendarModel.to_youtube_dict(raw_row)
    assert "youtube" in yt_dict
    assert "facebook" not in yt_dict
    assert yt_dict["youtube"]["post_type"] == "Shorts"
    print("✅ to_youtube_dict() thành công (Chỉ có Youtube)")

    # 4. Test to_facebook_dict
    print("\nStep 4: Testing to_facebook_dict()...")
    fb_dict = MediaCalendarModel.to_facebook_dict(raw_row)
    assert "facebook" in fb_dict
    assert "tiktok" not in fb_dict
    assert fb_dict["facebook"]["page_id"] == "FB_456"
    print("✅ to_facebook_dict() thành công (Chỉ có Facebook)")

    # 5. Test to_tiktok_dict
    print("\nStep 5: Testing to_tiktok_dict()...")
    tk_dict = MediaCalendarModel.to_tiktok_dict(raw_row)
    assert "tiktok" in tk_dict
    assert "youtube" not in tk_dict
    assert tk_dict["tiktok"]["account_id"] == "TK_789"
    print("✅ to_tiktok_dict() thành công (Chỉ có Tiktok)")

    print("\n-------------------\n")

    # 6. Test from_dict (Chuyển ngược lại sang Array)
    print("Step 6: Testing from_dict()...")
    converted_row = MediaCalendarModel.from_dict(data_dict)
    print("Resulting Array:")
    print(converted_row)

    # Kiểm tra xem mảng mới có khớp với mảng cũ không
    assert converted_row == raw_row
    print("\n✅ from_dict() thành công! Dữ liệu khớp hoàn toàn.")

    print("\n-------------------\n")
    print("🎉 TẤT CẢ CÁC BÀI TEST ĐÃ VƯỢT QUA!")

if __name__ == "__main__":
    try:
        test_media_calendar_model()
    except Exception as e:
        print(f"❌ LỖI KHI TEST: {e}")
        sys.exit(1)
