import os
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1' # Lờ đi cảnh báo scope thay đổi nếu các scope chính vẫn đủ
import json
import uuid
import threading
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from werkzeug.utils import secure_filename
import time

# --- CÁC HẰNG SỐ CẤU HÌNH ---
TOKEN_FILE = 'token.json'  # File lưu trữ token đăng nhập sau khi xác thực thành công
CREDENTIALS_FILE = 'assect/AouthGoogle.json'  # File cấu hình Client ID/Secret từ Google Console
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl"
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
    :param interactive: Nếu True, sẽ trả về Credentials hoặc raise lỗi nếu không có.
    """
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            try:
                creds.refresh(Request())
                # Lưu lại token đã refresh
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
                return creds
            except Exception:
                # Nếu refresh thất bại, coi như không có creds hợp lệ
                if not interactive:
                    raise PermissionError("Phiên đăng nhập Google đã hết hạn. Vui lòng đăng nhập lại.")
        
        if not creds or not creds.valid:
            if not interactive:
                # Bản fix: Raise lỗi thay vì return None để tránh lỗi ADC (Application Default Credentials)
                raise PermissionError("Chưa kết nối tài khoản Google hoặc phiên làm việc đã hết hạn.")
                
            raise PermissionError("Vui lòng đăng nhập Google để tiếp tục.")
            
    return creds

def _is_desktop_creds():
    """Kiểm tra xem file credentials là loại Desktop hay Web."""
    try:
        if not os.path.exists(CREDENTIALS_FILE):
            return True # Mặc định là Desktop nếu chưa có file
        with open(CREDENTIALS_FILE, 'r') as f:
            data = json.load(f)
            return "installed" in data
    except:
        return True

def get_auth_url_main(host_url=None):
    """Tạo URL xác thực cho tài khoản chính."""
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(f"Không tìm thấy file credentials tại {CREDENTIALS_FILE}")
        
    is_desktop = _is_desktop_creds()
    if is_desktop:
        # Desktop App: Nếu có host_url (truy cập từ web), dùng port thực tế của web.
        # Nếu không (môi trường khác), fallback về 8080 chuẩn.
        if host_url and ('localhost' in host_url or '127.0.0.1' in host_url):
            redirect_uri = f"{host_url.rstrip('/')}/api/auth/callback"
        else:
            redirect_uri = 'http://localhost:8080/api/auth/callback'
    else:
        # Web App: Luôn dùng domain thực tế
        redirect_uri = f"{host_url.rstrip('/')}/api/auth/callback" if host_url else 'http://localhost:8080/api/auth/callback'

    flow = InstalledAppFlow.from_client_secrets_file(
        CREDENTIALS_FILE, 
        SCOPES,
        redirect_uri=redirect_uri
    )
    
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
        state='main'
    )
    return auth_url, redirect_uri

def fetch_and_save_token(code, redirect_uri):
    """Lấy token từ code và lưu lại. redirect_uri phải khớp với lúc gọi auth_url."""
    flow = InstalledAppFlow.from_client_secrets_file(
        CREDENTIALS_FILE, 
        SCOPES,
        redirect_uri=redirect_uri
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    
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
        
        # WordPress Integration
        upload_to_wp = form_data.get('uploadToWp', False)
        wp_publisher = None
        if upload_to_wp:
            try:
                # Manual fetch to avoid circular imports
                TARGET_SPREADSHEET_ID = "1zFzHePIcOHXiWyAQRN7YOxIkE3kpDKwCuKMsdEe-snU"
                wp_res = sheet_service.spreadsheets().values().get(
                    spreadsheetId=TARGET_SPREADSHEET_ID,
                    range='Woocommerce_Config!A2:E2' # Only first row of config
                ).execute()
                wp_vals = wp_res.get('values', [])
                if wp_vals:
                    row = wp_vals[0]
                    # Format: site_url, consumer_key, consumer_secret, wp_user, wp_app_pass
                    from post_service.woocommerce_publisher import WoocommercePublisher
                    wp_publisher = WoocommercePublisher(
                        row[0] if len(row)>0 else "", 
                        row[1] if len(row)>1 else "", 
                        row[2] if len(row)>2 else "",
                        wp_user=row[3] if len(row)>3 else None,
                        wp_app_pass=row[4] if len(row)>4 else None
                    )
                    tasks[task_id]["progress"] = "Đã cấu hình WordPress Media..."
                else:
                    upload_to_wp = False
            except Exception as e:
                print(f"[Logic] WP Config Init Error: {e}")
                upload_to_wp = False
        
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
            
            if upload_to_wp and t['content_type'].startswith('image/'):
                tasks[task_id]["progress"] = "Đang đưa Thumbnail lên WordPress..."
                wp_res = wp_publisher.upload_media_bytes(t['content'], f"thumb_{int(time.time())}_{t['filename']}", t['content_type'])
                if wp_res.get('success'):
                    # Lưu link WP vào index 18 (SCRIP_ACTION) sau này
                    uploaded_links['thumb_wp'] = wp_res.get('url')

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
                
            if upload_to_wp and f['content_type'].startswith('image/'):
                tasks[task_id]["progress"] = f"Đang đưa ảnh {i+1} lên WordPress..."
                wp_res = wp_publisher.upload_media_bytes(f['content'], f"file_{i+1}_{int(time.time())}_{f['filename']}", f['content_type'])
                if wp_res.get('success'):
                    if 'images_wp' not in uploaded_links: uploaded_links['images_wp'] = []
                    uploaded_links['images_wp'].append(wp_res.get('url'))

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
            row = [next_stt, video_folder_id, folder_name, v_link, "Video"] + [""] * 13 + ["", uploaded_links['thumb']]
            # Index 18: Scrip_Action -> Lưu link WP nếu có
            if 'thumb_wp' in uploaded_links:
                row[18] = f"WP-Thumb: {uploaded_links['thumb_wp']}"
            
            all_new_rows.append(row)
            next_stt += 1

        # Bước C: Tạo dữ liệu hàng cho mảng Ảnh
        if uploaded_links['images']:
            # Nếu là hình ảnh sẽ là một mảng chứa nhiều link hình ảnh (JSON string)
            img_links_json = json.dumps(uploaded_links['images'])
            row = [next_stt, image_folder_id, folder_name, img_links_json, "Images"] + [""] * 13 + ["", uploaded_links['thumb']]
            
            if 'images_wp' in uploaded_links:
                row[18] = f"WP-Images: {','.join(uploaded_links['images_wp'])}"
            elif 'thumb_wp' in uploaded_links:
                row[18] = f"WP-Thumb: {uploaded_links['thumb_wp']}"

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

def convert_drive_link_to_direct(link, filename=None):
    """
    Chuyển đổi link Google Drive sang link direct lh3 sạch hơn cho WordPress.
    Cố gắng giữ lại phần mở rộng file (extension) để tránh lỗi MIME type mismatch.
    """
    if not link:
        return link
        
    file_id = ""
    if 'drive.google.com' in link:
        if 'id=' in link:
            file_id = link.split('id=')[-1].split('&')[0]
        elif '/d/' in link:
            file_id = link.split('/d/')[-1].split('/')[0]
    elif 'lh3.googleusercontent.com/d/' in link:
        file_id = link.split('/d/')[-1].split('=')[0].split('?')[0].split('#')[0]
    
    if file_id:
        ext = ".jpg" # Mặc định
        if filename:
            import os
            _, fext = os.path.splitext(filename)
            if fext and len(fext) > 1:
                ext = fext.lower()
        elif '?ext=' in link:
            ext = link.split('?ext=')[-1].split('&')[0].split('#')[0]
            
        # [SENTINEL-FIX-v3] Sử dụng cả query param và fragment để WP nhận diện tốt nhất
        # Fragment (#) giúp WP nhận diện nhưng Google bỏ qua. 
        # Query param (?ext=) là dự phòng.
        return f"https://lh3.googleusercontent.com/d/{file_id}=s1600?ext={ext}#{ext}"
    return link

def upload_product_images_to_drive(folder_name, files_data, parent_id="root"):
    """
    Upload danh sách ảnh sản phẩm lên Drive VÀ WordPress Media nếu có thể.
    Trả về danh sách các Direct Links (Drive) để lưu vào Sheet.
    """
    try:
        creds = get_creds()
        drive_service = build('drive', 'v3', credentials=creds)
        sheet_service = build('sheets', 'v4', credentials=creds)
        
        def create_folder(name, pid):
            pid = pid or "root"
            meta = {'name': name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [pid]}
            f = drive_service.files().create(body=meta, fields='id').execute()
            return f.get('id')

        # Load WP Config for dual upload
        wp_publisher = None
        try:
            TARGET_SPREADSHEET_ID = "1zFzHePIcOHXiWyAQRN7YOxIkE3kpDKwCuKMsdEe-snU"
            res = sheet_service.spreadsheets().values().get(spreadsheetId=TARGET_SPREADSHEET_ID, range='Woocommerce_Config!A2:E2').execute()
            rows = res.get('values', [])
            if rows:
                r = rows[0]
                from post_service.woocommerce_publisher import WoocommercePublisher
                wp_publisher = WoocommercePublisher(r[0], r[1], r[2], wp_user=r[3] if len(r)>3 else None, wp_app_pass=r[4] if len(r)>4 else None)
        except: pass

        # Tạo thư mục chính cho sản phẩm
        product_folder_id = create_folder(folder_name, parent_id)
        
        final_links = []
        for i, f in enumerate(files_data):
            # 1. Drive Upload
            temp_name = f"temp_{uuid.uuid4()}_{secure_filename(f['filename'])}"
            filepath = os.path.join(UPLOAD_FOLDER, temp_name)
            with open(filepath, 'wb') as tmp:
                tmp.write(f['content'])
            
            meta = {'name': f['filename'], 'parents': [product_folder_id]}
            media = MediaFileUpload(filepath, mimetype=f['content_type'], resumable=True)
            drive_file = drive_service.files().create(body=meta, media_body=media, fields='id,webViewLink').execute()
            
            drive_service.permissions().create(fileId=drive_file.get('id'), body={'type': 'anyone', 'role': 'reader'}).execute()
            os.remove(filepath)
            
            drive_direct_url = convert_drive_link_to_direct(drive_file.get('webViewLink'), f['filename'])
            
            # 2. WordPress Upload (Automatic for products if configured)
            if wp_publisher and f['content_type'].startswith('image/'):
                print(f"[Logic] Dual-Uploading Product Image {i+1} to WP...")
                wp_res = wp_publisher.upload_media_bytes(f['content'], f"woo_{int(time.time())}_{f['filename']}", f['content_type'])
                if wp_res.get('success'):
                    # Trả về link WP để WooCommerce dùng luôn, tránh sideload Drive lỗi sau này
                    wp_url = wp_res.get('url')
                    print(f"[Logic] Dual-Upload Success: {wp_url}")
                    final_links.append(wp_url) # Ưu tiên link WP cho WooCommerce Db
                    continue 

            final_links.append(drive_direct_url)
            
        return final_links
    except Exception as e:
        print(f"[Drive-Upload] Lỗi: {e}")
        return []

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
