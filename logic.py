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
    "https://www.googleapis.com/auth/spreadsheets", # Quyền chỉnh sửa Google Sheets
    "https://www.googleapis.com/auth/youtube.upload", # Quyền upload video lên YouTube
    "https://www.googleapis.com/auth/youtube.force-ssl" # Quyền quản lý video (set thumbnail, metadata...)
]
UPLOAD_FOLDER = 'uploads_temp'  # Thư mục tạm để lưu file trước khi đẩy lên Drive

# Đảm bảo thư mục tạm luôn tồn tại
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Biến toàn cục lưu trữ trạng thái các tác vụ upload (task_id -> status)
# Lưu ý: Trong môi trường thực tế, nên dùng Database hoặc Redis thay vì biến memory.
tasks = {}

def get_creds(interactive=False):
    """
    Hàm xử lý xác thực Google API.
    :param interactive: Nếu True, sẽ mở trình duyệt để đăng nhập nếu token không hợp lệ.
    """
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            try:
                creds.refresh(Request())
            except Exception:
                # Nếu refresh thất bại, coi như không có creds hợp lệ
                if not interactive: return None
        
        if not creds or not creds.valid:
            if not interactive:
                raise PermissionError("Vui lòng đăng nhập lại Google để tiếp tục.")
                
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(f"Không tìm thấy file credentials tại {CREDENTIALS_FILE}")
            
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            try:
                # Thử mở browser local (chỉ hoạt động trên máy cá nhân)
                creds = flow.run_local_server(port=8080, host='localhost', open_browser=True)
            except Exception as e:
                # Fallback hoặc thông báo lỗi rõ ràng trên server
                err_msg = (
                    f"Không thể mở trình duyệt để xác thực (Lỗi: {e}). "
                    "Nếu bạn đang chạy trên Server/Docker, vui lòng upload file 'token.json' "
                    "đã xác thực từ máy local lên thư mục gốc của server."
                )
                print(f"[Auth Error] {err_msg}")
                raise RuntimeError(err_msg)
        
        # Lưu lại token
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

        # CẬP NHẬT DỮ LIỆU VÀO GOOGLE SHEETS (Media_Calendar)
        tasks[task_id]["progress"] = "Đang cập nhật link vào Media Calendar..."
        
        # Sử dụng ID bảng tính từ yêu cầu của người dùng nếu có, hoặc dùng từ form
        TARGET_SHEET_ID = "1zFzHePIcOHXiWyAQRN7YOxIkE3kpDKwCuKMsdEe-snU"
        target_id = TARGET_SHEET_ID if TARGET_SHEET_ID else sheet_id
        
        # Bước A: Lấy số lượng hàng hiện tại để tính STT
        try:
            res = sheet_service.spreadsheets().values().get(spreadsheetId=target_id, range='Media_Calendar!A:A').execute()
            current_rows_count = len(res.get('values', []))
        except:
            current_rows_count = 0
            
        next_stt = current_rows_count if current_rows_count > 0 else 1

        all_new_rows = []
        
        # ID của nội dung đã upload lên drive (Dùng Folder ID của Video hoặc Image tùy nội dung)
        # Người dùng yêu cầu Id => Id của nội dung đã upload lên drive
        # Chúng ta sẽ dùng folder_id tổng quát hơn hoặc video_folder_id/image_folder_id tùy hàng
        
        # Bước B: Tạo dữ liệu hàng cho từng Video
        for v_link in uploaded_links['videos']:
            # Cấu trúc Media_Calendar: [STT, Id, Name, Link_on_drive, Category, ..., Thumbnail]
            # Padding lên 20 cột (Thumbnail ở index 19)
            row = [next_stt, video_folder_id, folder_name, v_link, "Video"] + [""] * 14 + [uploaded_links['thumb']]
            all_new_rows.append(row)
            next_stt += 1

        # Bước C: Tạo dữ liệu hàng cho mảng Ảnh
        if uploaded_links['images']:
            # Nếu là hình ảnh sẽ là một mảng chứa nhiều link hình ảnh (JSON string)
            img_links_json = json.dumps(uploaded_links['images'])
            row = [next_stt, image_folder_id, folder_name, img_links_json, "Images"] + [""] * 14 + [uploaded_links['thumb']]
            all_new_rows.append(row)
            next_stt += 1

        # Bước D: Ghi toàn bộ hàng mới xuống Sheet (Media_Calendar)
        if all_new_rows:
            sheet_service.spreadsheets().values().append(
                spreadsheetId=target_id,
                range='Media_Calendar!A:A',
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

def delete_drive_file(file_id):
    """Xóa hoàn toàn một file hoặc thư mục trên Google Drive"""
    if not file_id:
        return False
    try:
        creds = get_creds()
        service = build('drive', 'v3', credentials=creds)
        # Sử dụng trash=False để xóa vĩnh viễn, hoặc trash=True để chuyển vào thùng rác
        # Người dùng yêu cầu xoá hẳn nên ta dùng delete
        service.files().delete(fileId=file_id).execute()
        print(f"Drive: Đã xóa vĩnh viễn file {file_id}")
        return True
    except Exception as e:
        print(f"Drive Error: Lỗi khi xóa file {file_id}: {e}")
        return False
