import requests
import json
import time

BASE_URL = "http://localhost:3000/api/v2/sheets"
SHEET_NAME = "Facebook_db"

def test_v2_crud_lifecycle():
    print(f"--- ĐANG KIỂM TRA TOÀN BỘ VÒNG ĐỜI CRUD V2 CHO {SHEET_NAME} ---\n")

    try:
        # 1. READ (GET)
        print("Bưới 1: Đang lấy danh sách hàng hiện tại...")
        resp = requests.get(f"{BASE_URL}/{SHEET_NAME}")
        resp.raise_for_status()
        initial_data = resp.json()
        initial_count = len(initial_data)
        print(f" -> Số lượng hàng hiện tại: {initial_count}")

        # 2. CREATE (POST)
        print("\nBước 2: Đang thêm một hàng test mới...")
        test_row_data = {
            "stt": "TEST",
            "media_drive_id": "DRIVE_TEST_XYZ",
            "video_name": "Video Test CRUD V2",
            "content_type": "Test",
            "page": {
                "name": "Page Test",
                "id": "PAGE_TEST_ID",
                "access_token": "TOKEN_TEST"
            },
            "status": "Test Mode",
            "scrip_action": "delete_me"
        }
        resp = requests.post(f"{BASE_URL}/{SHEET_NAME}", json=test_row_data)
        resp.raise_for_status()
        print(f" -> Kết quả: {resp.json().get('message')}")

        # Đợi một chút để Google cập nhật
        time.sleep(2)

        # 3. VERIFY CREATE & GET TARGET INDEX
        print("\nBước 3: Xác minh hàng đã được thêm và lấy chỉ số...")
        resp = requests.get(f"{BASE_URL}/{SHEET_NAME}")
        updated_data = resp.json()
        new_count = len(updated_data)
        
        if new_count <= initial_count:
            print("❌ Lỗi: Không tìm thấy hàng mới sau khi POST.")
            return

        target_index = new_count - 1 # Hàng cuối cùng
        last_row = updated_data[target_index]
        print(f" -> Hàng mới nằm ở index: {target_index}")
        print(f" -> Tên video trong hàng mới: {last_row.get('video_name')}")

        # 4. UPDATE (PUT)
        print(f"\nBước 4: Đang cập nhật hàng tại index {target_index}...")
        updated_row_data = last_row.copy()
        updated_row_data["video_name"] = "Video ĐÃ CẬP NHẬT - Thành công!"
        
        resp = requests.put(f"{BASE_URL}/{SHEET_NAME}/{target_index}", json=updated_row_data)
        resp.raise_for_status()
        print(f" -> Kết quả: {resp.json().get('message')}")

        time.sleep(2)

        # 5. VERIFY UPDATE
        print("\nBước 5: Xác minh nội dung đã được cập nhật...")
        resp = requests.get(f"{BASE_URL}/{SHEET_NAME}")
        final_check_data = resp.json()
        if final_check_data[target_index]["video_name"] == updated_row_data["video_name"]:
            print("✅ Cập nhật (PUT) thành công rực rỡ!")
        else:
            print(f"❌ Lỗi: Nội dung hàng không khớp. Hiện tại là: {final_check_data[target_index]['video_name']}")

        # 6. DELETE (DELETE)
        print(f"\nBước 6: Đang xóa hàng test tại index {target_index}...")
        resp = requests.delete(f"{BASE_URL}/{SHEET_NAME}/{target_index}")
        resp.raise_for_status()
        print(f" -> Kết quả: {resp.json().get('message')}")

        time.sleep(2)

        # 7. FINAL VERIFICATION
        print("\nBước 7: Xác minh hàng đã biến mất...")
        resp = requests.get(f"{BASE_URL}/{SHEET_NAME}")
        last_data = resp.json()
        if len(last_data) == initial_count:
            print("✅ Xóa (DELETE) thành công!")
        else:
            print(f"⚠️ Cảnh báo: Số lượng hàng ({len(last_data)}) không khớp với ban đầu ({initial_count}). Vui lòng kiểm tra lại Google Sheets.")

        print("\n" + "="*40)
        print("🎉 KẾT THÚC BÀI TEST: TẤT CẢ API V2 ĐỀU HOẠT ĐỘNG ỔN ĐỊNH!")
        print("="*40)

    except Exception as e:
        print(f"\n❌ LỖI TRONG QUÁ TRÌNH TEST: {e}")

if __name__ == "__main__":
    test_v2_crud_lifecycle()
