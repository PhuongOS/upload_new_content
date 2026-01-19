import requests
import json
import sys
import os

# Thêm đường dẫn để import model
sys.path.append(os.getcwd())
from models.media_calendar import MediaCalendarModel

def test_show_real_data():
    print("--- ĐANG LẤY DỮ LIỆU THỰC TẾ TỪ GOOGLE SHEETS ---\n")

    # Cấu hình
    SHEET_ID = MediaCalendarModel.SPREADSHEET_ID
    SHEET_NAME = MediaCalendarModel.SHEET_NAME
    API_URL = f"http://localhost:3000/api/sheets/single-data?sheetId={SHEET_ID}&sheetName={SHEET_NAME}"

    try:
        # 1. Gọi API để lấy dữ liệu
        print(f"Bưới 1: Đang gọi API: {API_URL}...")
        response = requests.get(API_URL)
        response.raise_for_status()
        data = response.json()
        
        values = data.get("values", [])
        if len(values) < 2:
            print("❌ Không tìm thấy dữ liệu hoặc chỉ có dòng tiêu đề.")
            return

        # 2. Xử lý dữ liệu bằng Model
        # Bỏ qua dòng tiêu đề (values[0])
        headers = values[0]
        data_rows = values[1:]

        print(f"Bước 2: Tìm thấy {len(data_rows)} hàng dữ liệu. Dưới đây là 2 hàng đầu tiên được ánh xạ qua Model:\n")

        for i, row in enumerate(data_rows[:2]): # Lấy tối đa 2 hàng để hiển thị
            print(f"--- HÀNG SỐ {i+1} ---")
            
            # Chuyển đổi sang các dạng khác nhau để test
            full_dict = MediaCalendarModel.to_dict(row)
            yt_dict = MediaCalendarModel.to_youtube_dict(row)
            
            print(f"[THÔNG TIN CHUNG]")
            print(f" - STT: {full_dict['stt']}")
            print(f" - ID: {full_dict['id']}")
            print(f" - Tên: {full_dict['name']}")
            print(f" - Link Drive: {full_dict['link_on_drive']}")
            
            print(f"\n[DỮ LIỆU YOUTUBE (Qua hàm to_youtube_dict)]")
            print(json.dumps(yt_dict["youtube"], indent=4, ensure_ascii=False))
            
            print(f"\n[DỮ LIỆU FACEBOOK & TIKTOK (Qua hàm to_dict)]")
            print(f" - FB Page: {full_dict['facebook']['pages']}")
            print(f" - TikTok Acc: {full_dict['tiktok']['accounts']}")
            print("\n" + "="*40 + "\n")

    except Exception as e:
        print(f"❌ LỖI KHI LẤY DỮ LIỆU: {e}")
        print("Mẹo: Đảm bảo bạn đã khởi chạy server (npm start hoặc gunicorn) và đã đăng nhập Google.")

if __name__ == "__main__":
    test_show_real_data()
