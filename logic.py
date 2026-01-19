import os
import json
import uuid
import threading
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from werkzeug.utils import secure_filename

# --- CÁC HẰNG SỐ CẤU HÌNH ---
TOKEN_FILE = 'token.json'  # File lưu trữ token đăng nhập sau khi xác thực thành công
CREDENTIALS_FILE = 'assect/AouthGoogle.json'  # File cấu hình Client ID/Secret từ Google Console
SCOPES = [
    "https://www.googleapis.com/auth/drive",      # Quyền quản lý file trên Drive
    "https://www.googleapis.com/auth/spreadsheets" # Quyền chỉnh sửa Google Sheets
]
UPLOAD_FOLDER = 'uploads_temp'  # Thư mục tạm để lưu file trước khi đẩy lên Drive

# Đảm bảo thư mục tạm luôn tồn tại
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Biến toàn cục lưu trữ trạng thái các tác vụ upload (task_id -> status)
# Lưu ý: Trong môi trường thực tế, nên dùng Database hoặc Redis thay vì biến memory.
tasks = {}

def get_creds():
    """
    Hàm xử lý xác thực Google API.
    1. Kiểm tra xem đã có file token.json chưa.
    2. Nếu chưa hoặc token hết hạn, sẽ thực hiện refresh hoặc yêu cầu đăng nhập mới.
    3. Trả về đối tượng credentials để sử dụng cho các dịch vụ Google.
    """
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(f"Không tìm thấy file credentials tại {CREDENTIALS_FILE}")
                
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            # Khởi chạy server xác thực tại port 5001
            creds = flow.run_local_server(port=5001, host='localhost')
        
        # Lưu lại token để lần sau không cần đăng nhập lại
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            
    return creds

def background_upload(task_id, form_data, files_data):
    """
    Hàm xử lý logic upload chính, chạy ngầm trong một luồng (thread) riêng.
    Quy trình:
    1. Tạo thư mục ảnh và video trên Drive.
    2. Upload Thumbnail (nếu có).
    3. Upload mảng file lên các thư mục tương ứng.
    4. Ghi thông tin link đã upload vào Google Sheets.
    """
    try:
        tasks[task_id] = {"status": "processing", "progress": "Bắt đầu xử lý..."}
        
        creds = get_creds()
        drive_service = build('drive', 'v3', credentials=creds)
        sheet_service = build('sheets', 'v4', credentials=creds)

        parent_id = form_data.get('parentId') # Thư mục gốc trên Drive
        sheet_id = form_data.get('sheetId')   # ID bảng tính cần cập nhật
        folder_name = form_data.get('folderName') # Tên thư mục mới (cũng dùng làm chủ đề)
        
        # Hàm con hỗ trợ tạo thư mục trên Google Drive
        def create_folder(name, pid):
            meta = {'name': name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [pid]}
            f = drive_service.files().create(body=meta, fields='id').execute()
            return f.get('id')

        tasks[task_id]["progress"] = "Đang tạo các thư mục lưu trữ..."
        image_folder_id = create_folder(f"{folder_name}-image", parent_id)
        video_folder_id = create_folder(f"{folder_name}-video", parent_id)

        uploaded_links = {'videos': [], 'images': [], 'thumb': ''}
        
        # Hàm con hỗ trợ upload một file cụ thể lên Drive
        def upload_to_drive(file_bytes, filename, content_type, folder_id):
            # Lưu tạm file ra đĩa để Google client có thể đọc theo dạng stream
            temp_name = f"{task_id}_{secure_filename(filename)}"
            filepath = os.path.join(UPLOAD_FOLDER, temp_name)
            with open(filepath, 'wb') as f:
                f.write(file_bytes)
            
            meta = {'name': filename, 'parents': [folder_id]}
            media = MediaFileUpload(filepath, mimetype=content_type, resumable=True)
            f = drive_service.files().create(body=meta, media_body=media, fields='id,webViewLink').execute()
            
            # Xóa file tạm sau khi upload xong
            os.remove(filepath)
            return f.get('webViewLink')

        # Xử lý upload Thumbnail
        if 'thumbnail' in files_data:
            tasks[task_id]["progress"] = "Đang upload ảnh bìa..."
            t = files_data['thumbnail']
            link = upload_to_drive(t['content'], t['filename'], t['content_type'], image_folder_id)
            uploaded_links['thumb'] = link

        # Xử lý upload danh sách Files
        for i, f in enumerate(files_data.get('files', [])):
            tasks[task_id]["progress"] = f"Đang upload file {i+1}/{len(files_data['files'])}..."
            is_video = f['content_type'].startswith('video/')
            target_id = video_folder_id if is_video else image_folder_id
            
            link = upload_to_drive(f['content'], f['filename'], f['content_type'], target_id)
            if is_video:
                uploaded_links['videos'].append(link)
            else:
                uploaded_links['images'].append(link)

        # CẬP NHẬT DỮ LIỆU VÀO GOOGLE SHEETS
        tasks[task_id]["progress"] = "Đang cập nhật link vào Google Sheets..."
        
        # Bước A: Lấy số lượng hàng hiện tại để tính STT (Số thứ tự) tiếp theo
        res = sheet_service.spreadsheets().values().get(spreadsheetId=sheet_id, range='Content!A:A').execute()
        current_rows_count = len(res.get('values', []))
        next_stt = current_rows_count if current_rows_count > 0 else 1

        all_new_rows = []
        thumb_link = uploaded_links['thumb']

        # Bước B: Tạo dữ liệu hàng cho từng Video (mỗi video một hàng riêng)
        for v_link in uploaded_links['videos']:
            # Cấu trúc: [STT, ..., Status, ..., Chủ đề, ..., Video Link, Thumb Link, Image Link]
            row = [next_stt, "", "", "Chờ Đăng", "", "Có", "", folder_name, "", "", "", "", v_link, thumb_link, ""]
            all_new_rows.append(row)
            next_stt += 1

        # Bước C: Tạo dữ liệu hàng cho mảng Ảnh (tất cả ảnh chung một hàng, trải ngang)
        if uploaded_links['images']:
            img_links = uploaded_links['images'][:9] # Giới hạn tối đa 9 ảnh theo cấu trúc sheet
            row = [next_stt, "", "", "Chờ Đăng", "", "Có", "", folder_name, "", "", "", "", "", thumb_link, *img_links]
            all_new_rows.append(row)
            next_stt += 1

        # Bước D: Ghi toàn bộ hàng mới xuống Sheet cùng một lúc (append)
        if all_new_rows:
            sheet_service.spreadsheets().values().append(
                spreadsheetId=sheet_id,
                range='Content!A:A',
                valueInputOption='USER_ENTERED',
                body={"values": all_new_rows}
            ).execute()

        # Đánh dấu tác vụ hoàn thành
        tasks[task_id] = {
            "status": "success", 
            "progress": "Hoàn tất!", 
            "message": f"Đã tạo thành công {len(all_new_rows)} hàng dữ liệu cho nội dung '{folder_name}'."
        }

    except Exception as e:
        print(f"Lỗi Tác vụ ngầm: {e}")
        tasks[task_id] = {"status": "error", "progress": "Thất bại", "message": str(e)}
