import json
import sys
import os

# Thêm đường dẫn để có thể import từ thư mục hiện tại
sys.path.append(os.getcwd())

from models.Youtube_db import YoutubeDbModel

def test_youtube_db_model():
    print("--- ĐANG KIỂM TRA YOUTUBE DB MODEL ---\n")

    # 1. Giả lập một hàng dữ liệu thô (21 cột)
    raw_row = [
        "1",                                       # STT
        "Drive_VID_777",                           # Id_media_on_drive
        "YouTube Tutorial Video",                  # Name_video
        "http://drive.com/yt-video1",              # Video_url
        "Vlog",                                    # Type_conten
        "Hook Youtube cực cháy",                   # Hook
        "Nội dung mô tả video",                    # Body_content
        "Đăng ký ngay",                            # CTA_text
        "#tutorial #yt",                           # Product_hashtag
        "#lamphat",                                # Brand_hashtag
        "contact@gmail.com",                       # Contact_me
        "Lâm Phát Studio",                         # Channel_name
        "CH_ID_001",                               # Page_Id
        "lamphat@gmail.com",                       # Gmail_channel
        "Video",                                   # Post_type
        "2026-03-01",                              # Calendar
        "2026-03-01 15:00",                        # Completion_time
        "http://youtube.com/watch?v=1",            # Link_post_on_youtube
        "YT_ID_555",                               # Post_Id
        "Uploaded",                                # Curent_Status
        "Script_YT"                                # Scrip_action
    ]

    print("Step 1: Raw row data length:", len(raw_row))
    print("\n-------------------\n")

    # 2. Test to_dict
    print("Step 2: Testing to_dict()...")
    data_dict = YoutubeDbModel.to_dict(raw_row)
    print("Resulting Dictionary (JSON):")
    print(json.dumps(data_dict, indent=2, ensure_ascii=False))
    
    # Kiểm tra một số giá trị then chốt
    assert data_dict["video_name"] == "YouTube Tutorial Video"
    assert data_dict["channel"]["name"] == "Lâm Phát Studio"
    assert data_dict["channel"]["gmail"] == "lamphat@gmail.com"
    assert data_dict["yt_video_id"] == "YT_ID_555"
    assert data_dict["scrip_action"] == "Script_YT"
    print("\n✅ to_dict() thành công!")

    print("\n-------------------\n")

    # 3. Test from_dict
    print("Step 3: Testing from_dict()...")
    converted_row = YoutubeDbModel.from_dict(data_dict)
    
    print("Resulting Row Array (to save back to Sheets):")
    print(converted_row)

    # Kiểm tra xem mảng mới có khớp với mảng cũ không
    assert len(converted_row) == 21
    assert converted_row == raw_row
    print("\n✅ from_dict() thành công! Dữ liệu khớp 21/21 cột.")

    print("\n-------------------\n")
    print("🎉 TẤT CẢ CÁC BÀI TEST YOUTUBE DB ĐÃ VƯỢT QUA!")

if __name__ == "__main__":
    try:
        test_youtube_db_model()
    except Exception as e:
        print(f"❌ LỖI KHI TEST: {e}")
        sys.exit(1)
