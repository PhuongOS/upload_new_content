import json
import sys
import os

# Thêm đường dẫn để có thể import từ thư mục hiện tại
sys.path.append(os.getcwd())

from models.Facebook_db import FacebookDbModel

def test_facebook_db_model():
    print("--- ĐANG KIỂM TRA FACEBOOK DB MODEL ---\n")

    # 1. Giả lập một hàng dữ liệu thô (22 cột)
    raw_row = [
        "1",                                       # STT
        "Drive_ID_555",                            # Id_media_on_drive
        "FB Video Marketing",                      # Name_video
        "http://drive.com/video1",                 # Video_url
        "Reels",                                   # Type_conten
        "Mở đầu cực hay",                          # Hook
        "Nội dung chi tiết",                       # Body_content
        "Mua ngay",                                # CTA_text
        "0909xxxxxx",                              # Contact_me
        "#product",                                # Product_hashtag
        "#brand",                                  # Brand_hashtag
        "http://drive.com/thumb1",                 # Thumbnail_url
        "Page My Business",                        # Page_name
        "PAGE_12345",                              # Page_Id
        "EAAG...",                                 # Access_token
        "Video",                                   # Post_type
        "2026-02-01",                              # Calendar
        "2026-02-01 10:00",                        # Completion_time
        "http://fb.com/post/1",                    # Link_post_on_facebook
        "POST_ID_999",                             # Post_Id
        "Published",                               # Curent_Status
        "Script_ABC"                               # Scrip_action
    ]

    print("Step 1: Raw row data length:", len(raw_row))
    print("\n-------------------\n")

    # 2. Test to_dict
    print("Step 2: Testing to_dict()...")
    data_dict = FacebookDbModel.to_dict(raw_row)
    print("Resulting Dictionary (JSON):")
    print(json.dumps(data_dict, indent=2, ensure_ascii=False))
    
    # Kiểm tra một số giá trị then chốt
    assert data_dict["video_name"] == "FB Video Marketing"
    assert data_dict["page"]["id"] == "PAGE_12345"
    assert data_dict["page"]["access_token"] == "EAAG..."
    assert data_dict["fb_post_id"] == "POST_ID_999"
    assert data_dict["scrip_action"] == "Script_ABC"
    print("\n✅ to_dict() thành công!")

    print("\n-------------------\n")

    # 3. Test from_dict
    print("Step 3: Testing from_dict()...")
    converted_row = FacebookDbModel.from_dict(data_dict)
    print("Resulting Row Array (to save back to Sheets):")
    print(converted_row)
    
    # Kiểm tra xem mảng mới có khớp với mảng cũ không
    assert len(converted_row) == 22
    assert converted_row == raw_row
    print("\n✅ from_dict() thành công! Dữ liệu khớp 22/22 cột.")

    print("\n-------------------\n")
    print("🎉 TẤT CẢ CÁC BÀI TEST FACEBOOK DB ĐÃ VƯỢT QUA!")

if __name__ == "__main__":
    try:
        test_facebook_db_model()
    except Exception as e:
        print(f"❌ LỖI KHI TEST: {e}")
        sys.exit(1)
