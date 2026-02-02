import os
import re
import uuid
import threading
import csv
import io
from flask import Blueprint, request, jsonify, redirect
from googleapiclient.discovery import build
from logic import (
    get_creds, tasks, background_upload, delete_drive_file, 
    TOKEN_FILE, get_auth_url_main, fetch_and_save_token, _is_desktop_creds
)
from services.sheet_service import SheetService
from services.account_service import AccountService
from models.Woocommerce_Config import WoocommerceConfModel
from models.Woocommerce_db import WoocommerceDbModel
from post_service.woocommerce_publisher import WoocommercePublisher
from services.url_analyzer import URLAnalyzer

# Khởi tạo Blueprint cho các API
api_bp = Blueprint('api', __name__)

@api_bp.route('/api/auth/login')
def login():
    """Bắt đầu flow đăng nhập Google."""
    try:
        # Tự động nhận diện host/protocol (Đã fix: Không ép 8080 để chạy được trên port 3000 local)
        protocol = request.headers.get('X-Forwarded-Proto', 'http')
        host = request.headers.get('Host', request.host)
        host_url = f"{protocol}://{host}"

        # Tính toán auth_url (Hàm này tự nhận diện Desktop vs Web App)
        auth_url, _ = get_auth_url_main(host_url=host_url)
        
        # Nếu là request từ frontend (AJAX), trả về JSON
        if request.args.get('format') == 'json':
            return jsonify({
                "success": False,
                "needs_manual_auth": True,
                "auth_url": auth_url,
                "message": "Vui lòng mở URL này để xác thực nếu trình duyệt không tự mở."
            })
            
        return redirect(auth_url)
    except Exception as e:
        return f"Lỗi khởi tạo đăng nhập: {e}", 500

@api_bp.route('/api/auth/callback')
def auth_callback():
    """Xử lý callback từ Google sau khi user xác thực thành công."""
    code = request.args.get('code')
    if not code:
        return "Thiếu mã xác thực (code)", 400
    
    try:
        # Re-construct redirect_uri (Phải khớp chính xác với lúc bắt đầu)
        is_desktop = _is_desktop_creds()
        protocol = request.headers.get('X-Forwarded-Proto', 'http')
        host = request.headers.get('Host', request.host)
        
        if is_desktop:
            # Desktop App: Nếu đang chạy local, dùng đúng port đang chạy thay vì ép 8080
            if 'localhost' in host or '127.0.0.1' in host:
                redirect_uri = f"http://{host}/api/auth/callback"
            else:
                redirect_uri = 'http://localhost:8080/api/auth/callback'
        else:
            # Web App: Dùng domain thực tế
            redirect_uri = f"{protocol}://{host}/api/auth/callback"
            
        print(f"[Auth] Callback received. Exchange with redirect_uri: {redirect_uri}")
            
        state = request.args.get('state', 'main')
        
        if state == 'account':
            # Xử lý cho Multi-Account YouTube
            AccountService.fetch_and_save_account_token(code, redirect_uri=redirect_uri)
            header_text = "Thêm tài khoản thành công!"
            message_text = "Tài khoản YouTube đã được liên kết."
        else:
            # Xử lý cho tài khoản chính (Drive/Sheets)
            fetch_and_save_token(code, redirect_uri=redirect_uri)
            header_text = "Xác thực thành công!"
            message_text = "Tài khoản chính đã được kết nối."

        return f"""
            <html>
                <body style="font-family: sans-serif; text-align: center; padding: 50px; background: #121212; color: white;">
                    <h1 style="color: #4CAF50;">{header_text}</h1>
                    <p>{message_text}</p>
                    <p>Bạn có thể đóng cửa sổ này và quay lại ứng dụng.</p>
                    <button onclick="window.close()" style="padding: 10px 20px; cursor: pointer; background: #333; color: white; border: 1px solid #444; border-radius: 4px;">Đóng cửa sổ</button>
                    <script>setTimeout(() => window.close(), 3000);</script>
                </body>
            </html>
        """
    except Exception as e:
        return f"Lỗi lưu token: {e}", 500

@api_bp.route('/api/auth/status')
def auth_status():
    if os.path.exists(TOKEN_FILE):
        try:
            creds = get_creds(interactive=False)
            if not creds:
                return jsonify({"connected": False, "reason": "token_invalid"})
            
            service = build('drive', 'v3', credentials=creds)
            about = service.about().get(fields="user").execute()
            return jsonify({
                "connected": True, 
                "email": about['user']['emailAddress']
            })
        except Exception as e:
            return jsonify({"connected": False, "error": str(e)})
    return jsonify({"connected": False})

# --- API QUẢN LÝ TÀI KHOẢN YOUTUBE (MULTI-ACCOUNT) ---

@api_bp.route('/api/auth/accounts', methods=['GET'])
def list_accounts():
    """Liệt kê tất cả tài khoản Google đã kết nối."""
    try:
        accounts = AccountService.list_accounts()
        return jsonify({"success": True, "accounts": accounts})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route('/api/auth/accounts/add', methods=['POST'])
def add_account():
    """
    Thêm tài khoản Google mới.
    Nếu đang truy cập từ localhost, mở browser trực tiếp.
    Nếu từ remote, trả về URL để user tự mở.
    """
    try:
        # Kiểm tra xem có phải truy cập từ localhost không
        is_local = request.remote_addr in ['127.0.0.1', 'localhost', '::1']
        
        if is_local:
            # Mở browser trực tiếp trên máy server
            result = AccountService.add_account_interactive()
            return jsonify(result)
        else:
            # Remote access: Trả về URL để user tự mở
            protocol = request.headers.get('X-Forwarded-Proto', 'http')
            host = request.headers.get('Host', request.host)
            host_url = f"{protocol}://{host}"

            auth_info = AccountService.add_account_start(host_url=host_url)
            return jsonify({
                "success": False, 
                "needs_manual_auth": True,
                "auth_url": auth_info["auth_url"],
                "message": "Vui lòng mở URL này trong trình duyệt để xác thực."
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route('/api/auth/accounts/<account_id>', methods=['DELETE'])
def remove_account(account_id):
    """Xóa một tài khoản đã kết nối."""
    try:
        result = AccountService.remove_account(account_id)
        if result["success"]:
            return jsonify(result)
        return jsonify(result), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route('/api/auth/accounts/<account_id>/channels', methods=['GET'])
def get_account_channels(account_id):
    """Lấy danh sách kênh YouTube của một tài khoản."""
    try:
        result = AccountService.refresh_channels(account_id)
        if result["success"]:
            return jsonify(result)
        return jsonify(result), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# --- API QUẢN LÝ TÁC VỤ (TASK MANAGEMENT) ---

@api_bp.route('/api/tasks')
def get_tasks():
    """
    Lấy danh sách các tác vụ upload đang chạy ngầm.
    ---
    responses:
      200:
        description: Danh sách các task và tiến độ
    """
    return jsonify(tasks)

# --- API DỮ LIỆU GOOGLE SHEETS ---

@api_bp.route('/api/sheets/full-data')
def get_full_sheet_data():
    """
    Lấy toàn bộ dữ liệu từ TẤT CẢ các tab.
    ---
    parameters:
      - name: sheetId
        in: query
        type: string
        required: true
        description: ID của Google Spreadsheet
    responses:
      200:
        description: Thành công
    """
    sheet_id = request.args.get('sheetId')
    if not sheet_id:
        return jsonify({"error": "Thiếu tham số sheetId"}), 400
    
    try:
        creds = get_creds()
        service = build('sheets', 'v4', credentials=creds)
        spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheets_metadata = spreadsheet.get('sheets', [])
        
        full_data = {
            "title": spreadsheet.get('properties', {}).get('title', 'Unknown'),
            "sheets": []
        }
        
        for sheet in sheets_metadata:
            props = sheet.get('properties', {})
            title = props.get('title')
            sheet_id_val = props.get('sheetId')
            result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=title).execute()
            full_data["sheets"].append({
                "title": title,
                "sheetId": sheet_id_val,
                "values": result.get('values', [])
            })
        return jsonify(full_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/sheets/single-data')
def get_single_sheet_data():
    """
    Lấy dữ liệu từ một tab cụ thể.
    ---
    parameters:
      - name: sheetId
        in: query
        type: string
        required: true
      - name: sheetName
        in: query
        type: string
        required: true
    responses:
      200:
        description: Thành công
    """
    sheet_id = request.args.get('sheetId')
    sheet_name = request.args.get('sheetName')
    if not sheet_id or not sheet_name:
        return jsonify({"error": "Thiếu tham số"}), 400
    
    try:
        creds = get_creds()
        service = build('sheets', 'v4', credentials=creds)
        result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=sheet_name).execute()
        return jsonify({
            "sheetName": sheet_name,
            "values": result.get('values', [])
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- API THAY ĐỔI CẤU TRÚC SHEETS (CRUD TABS) ---

@api_bp.route('/api/sheets/tabs', methods=['POST'])
def create_sheet_tab():
    """
    Tạo một tab mới.
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          properties:
            sheetId:
              type: string
            title:
              type: string
    responses:
      200:
        description: Tạo thành công
    """
    data = request.json
    sheet_id = data.get('sheetId')
    title = data.get('title')
    try:
        creds = get_creds()
        service = build('sheets', 'v4', credentials=creds)
        body = {'requests': [{'addSheet': {'properties': {'title': title}}}]}
        res = service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=body).execute()
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/sheets/tabs', methods=['DELETE'])
def delete_sheet_tab():
    """
    Xóa một tab.
    ---
    parameters:
      - name: sheetId
        in: query
        type: string
        required: true
      - name: tabId
        in: query
        type: integer
        required: true
    responses:
      200:
        description: Xóa thành công
    """
    sheet_id = request.args.get('sheetId')
    tab_id = request.args.get('tabId', type=int)
    try:
        creds = get_creds()
        service = build('sheets', 'v4', credentials=creds)
        body = {'requests': [{'deleteSheet': {'sheetId': tab_id}}]}
        res = service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=body).execute()
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- API THAY ĐỔI DỮ LIỆU HÀNG (CRUD ROWS) ---

@api_bp.route('/api/sheets/rows', methods=['PUT'])
def update_sheet_row():
    """
    Cập nhật nội dung hàng.
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          properties:
            sheetId:
              type: string
            sheetName:
              type: string
            rowIndex:
              type: integer
            values:
              type: array
              items:
                type: string
    responses:
      200:
        description: Cập nhật thành công
    """
    data = request.json
    sheet_id = data.get('sheetId')
    sheet_name = data.get('sheetName')
    row_index = data.get('rowIndex')
    values = data.get('values')
    try:
        creds = get_creds()
        service = build('sheets', 'v4', credentials=creds)
        range_name = f"{sheet_name}!A{row_index + 1}"
        res = service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body={'values': [values]}
        ).execute()
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/sheets/rows', methods=['DELETE'])
def delete_sheet_row():
    """
    Xóa hàng khỏi trang tính.
    ---
    parameters:
      - name: sheetId
        in: query
        type: string
        required: true
      - name: tabId
        in: query
        type: integer
        required: true
      - name: rowIndex
        in: query
        type: integer
        required: true
    responses:
      200:
        description: Xóa thành công
    """
    sheet_id = request.args.get('sheetId')
    tab_id = request.args.get('tabId', type=int)
    row_index = request.args.get('rowIndex', type=int)
    try:
        creds = get_creds()
        service = build('sheets', 'v4', credentials=creds)
        body = {
            'requests': [{
                'deleteDimension': {
                    'range': {
                        'sheetId': tab_id,
                        'dimension': 'ROWS',
                        'startIndex': row_index,
                        'endIndex': row_index + 1
                    }
                }
            }]
        }
        res = service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=body).execute()
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- API UPLOAD FILE ---

@api_bp.route('/api/upload', methods=['POST'])
def upload_files():
    """
    Tải file lên Drive và cập nhật Sheets ngầm.
    ---
    parameters:
      - name: parentId
        in: formData
        type: string
        required: true
      - name: sheetId
        in: formData
        type: string
        required: true
      - name: folderName
        in: formData
        type: string
        required: true
      - name: topic
        in: formData
        type: string
      - name: thumbnail
        in: formData
        type: file
      - name: files
        in: formData
        type: file
        required: true
    responses:
      200:
        description: Đã thêm vào hàng đợi
    """
    try:
        form_data = {
            'parentId': request.form.get('parentId'),
            'sheetId': request.form.get('sheetId'),
            'folderName': request.form.get('folderName'),
            'topic': request.form.get('topic'),
            'uploadToWp': request.form.get('uploadToWp') == 'true'
        }
        files_data = {'files': []}
        if 'thumbnail' in request.files:
            t = request.files['thumbnail']
            files_data['thumbnail'] = {'content': t.read(), 'filename': t.filename, 'content_type': t.content_type}
        
        files = request.files.getlist('files')
        for f in files:
            if f.filename != '':
                files_data['files'].append({'content': f.read(), 'filename': f.filename, 'content_type': f.content_type})

        task_id = str(uuid.uuid4())
        tasks[task_id] = {"status": "queued", "progress": "Đang khởi tạo..."}
        thread = threading.Thread(target=background_upload, args=(task_id, form_data, files_data))
        thread.start()
        return jsonify({"status": "queued", "task_id": task_id, "message": "Đã bắt đầu upload ở chế độ chạy ngầm."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- API TIỆN ÍCH (UTILITIES) ---

@api_bp.route('/api/utils/parse-url', methods=['POST'])
def parse_sheet_url():
    """
    Bóc tách ID từ link Google Sheets.
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          properties:
            url:
              type: string
    responses:
      200:
        description: Thành công
    """
    data = request.json
    url = data.get('url', '')
    sheet_id_match = re.search(r'/spreadsheets/d/([a-zA-Z0-9_-]+)', url)
    sheet_id = sheet_id_match.group(1) if sheet_id_match else None
    gid_match = re.search(r'[#&]gid=([0-9]+)', url)
    tab_id = gid_match.group(1) if gid_match else "0"
    if not sheet_id:
        return jsonify({"error": "Link không hợp lệ"}), 400
    return jsonify({"spreadsheetId": sheet_id, "tabId": tab_id})

# --- API CRUD DỰA TRÊN MODEL (NEW V2) ---

@api_bp.route('/api/v2/sheets/<sheet_name>', methods=['GET'])
def get_v2_sheet_data(sheet_name):
    """
    Lấy toàn bộ dữ liệu từ một bảng tính cụ thể (Media_Calendar, Facebook_db, Youtube_db).
    Dữ liệu trả về đã được ánh xạ qua Model tương ứng.
    ---
    parameters:
      - name: sheet_name
        in: path
        type: string
        required: true
        description: Tên của bảng tính (ví dụ Facebook_db)
    responses:
      200:
        description: Thành công
    """
    try:
        data = SheetService.get_all_rows(sheet_name)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@api_bp.route('/api/v2/sheets/<sheet_name>', methods=['POST'])
def append_v2_sheet_row(sheet_name):
    """
    Thêm một hàng mới vào bảng tính bằng cách gửi một Dictionary.
    ---
    parameters:
      - name: sheet_name
        in: path
        type: string
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
    responses:
      200:
        description: Thêm thành công
    """
    try:
        data = request.json
        SheetService.append_row(sheet_name, data)
        return jsonify({"message": "Thêm hàng thành công"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@api_bp.route('/api/v2/sheets/<sheet_name>/<int:row_index>', methods=['PUT'])
def update_v2_sheet_row(sheet_name, row_index):
    """
    Cập nhật nội dung một hàng.
    ---
    parameters:
      - name: sheet_name
        in: path
        type: string
        required: true
      - name: row_index
        in: path
        type: integer
        required: true
        description: Chỉ số hàng (bắt đầu từ 0, không tính tiêu đề)
      - name: body
        in: body
        required: true
    responses:
      200:
        description: Cập nhật thành công
    """
    try:
        data = request.json
        SheetService.update_row(sheet_name, row_index, data)
        return jsonify({"message": "Cập nhật hàng thành công"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@api_bp.route('/api/v2/sheets/<sheet_name>/<int:row_index>', methods=['DELETE'])
def delete_v2_sheet_row(sheet_name, row_index):
    """
    Xóa một hàng khỏi bảng tính.
    ---
    parameters:
      - name: sheet_name
        in: path
        type: string
        required: true
      - name: row_index
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Xóa thành công
    """
    try:
        # Nếu là Media_Calendar, cần lấy ID Drive trước khi xoá hàng
        delete_drive = request.args.get('delete_drive', 'false').lower() == 'true'
        
        if delete_drive and sheet_name == "Media_Calendar":
            rows = SheetService.get_all_rows(sheet_name)
            if row_index < len(rows):
                media_item = rows[row_index]
                drive_id = media_item.get('id')
                if drive_id:
                    delete_drive_file(drive_id)
                    print(f"API: Đã yêu cầu xóa Drive ID {drive_id} trước khi xóa hàng.")

        SheetService.delete_row(sheet_name, row_index)
        return jsonify({"message": "Xóa hàng thành công (kèm Drive nếu có)"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

from provider.gemini import GeminiProvider

@api_bp.route('/api/v2/ai/generate', methods=['POST'])
def ai_generate():
    """
    Sử dụng AI Gemini để tạo nội dung
    """
    data = request.json
    api_key = data.get('api_key')
    system_prompt = data.get('system_prompt')
    user_prompt = data.get('user_prompt')

    if not api_key:
        return jsonify({"error": "Vui lòng cung cấp Gemini API Key"}), 400
    if not user_prompt:
        return jsonify({"error": "Vui lòng nhập nội dung muốn tạo"}), 400

    try:
        provider = GeminiProvider(api_key, system_prompt)
        text = provider.generate_content(user_prompt)
        return jsonify({"result": text})
    except Exception as e:
        error_msg = str(e)
        status_code = 500
        if any(code in error_msg for code in ["429", "Too Many Requests", "exhausted"]):
            status_code = 429
        elif "503" in error_msg or "Service Unavailable" in error_msg:
            status_code = 503
        elif "403" in error_msg or "Permission denied" in error_msg:
            status_code = 403
        return jsonify({"error": error_msg}), status_code

# --- DỊCH VỤ ĐĂNG BÀI (POST SERVICE) ---
from post_service.manager import PostManager

post_manager = PostManager()

@api_bp.route('/api/v2/post/publish', methods=['POST'])
def post_publish():
    """Kích hoạt tiến trình đăng bài lên MXH (Async/Queue)."""
    data = request.json
    sheet_name = data.get('sheet_name')
    index = data.get('index')
    
    if not sheet_name or index is None:
        return jsonify({"error": "Thiếu thông tin bảng tính hoặc dòng"}), 400
    
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "status": "queued", 
        "message": f"Đang chuẩn bị đăng bài (Dòng {index} - {sheet_name})..."
    }
    
    def background_publish(tid, s_name, idx):
        try:
            tasks[tid]["status"] = "processing"
            tasks[tid]["message"] = "Đang tải video và xử lý..."
            
            # Gọi hàm xử lý chính (đồng bộ, mất thời gian tải)
            result = post_manager.publish_item(s_name, int(idx), tid)
            
            if result.get("success"):
                tasks[tid]["status"] = "success"
                tasks[tid]["message"] = "Đăng thành công!"
                tasks[tid]["result"] = result
            else:
                tasks[tid]["status"] = "error"
                tasks[tid]["message"] = result.get("error", "Lỗi không xác định")
        except Exception as e:
            tasks[tid]["status"] = "error"
            tasks[tid]["message"] = f"Lỗi hệ thống: {str(e)}"

    # Chạy thread ngầm
    threading.Thread(target=background_publish, args=(task_id, sheet_name, index)).start()
        
    return jsonify({
        "status": "queued", 
        "task_id": task_id, 
        "message": "Yêu cầu đã được tiếp nhận và xử lý ngầm."
    })

@api_bp.route('/api/v2/post/history', methods=['GET'])
def post_history():
    """Lấy danh sách lịch sử bài đã đăng."""
    try:
        data = SheetService.get_all_rows("Published_History")
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@api_bp.route('/api/v2/facebook/post/<int:index>', methods=['GET'])
def facebook_post_sync(index):
    """Đồng bộ thông tin bài viết từ Facebook."""
    res = post_manager.sync_facebook_post_info(index)
    if res["success"]:
        return jsonify(res)
    return jsonify(res), 400

@api_bp.route('/api/v2/facebook/post/<int:index>', methods=['POST'])
def facebook_post_edit(index):
    """Chỉnh sửa nội dung bài viết trên Facebook."""
    data = request.json
    new_message = data.get("message")
    if not new_message:
        return jsonify({"success": False, "error": "Thiếu nội dung tin nhắn mới."}), 400
        
    res = post_manager.edit_facebook_post(index, new_message)
    if res["success"]:
        return jsonify(res)
    return jsonify(res), 400

@api_bp.route('/api/v2/facebook/post/<int:index>', methods=['DELETE'])
def facebook_post_delete(index):
    """Xóa bài viết trên Facebook và trong lịch sử."""
    res = post_manager.delete_facebook_post(index)
    if res["success"]:
        return jsonify(res)
    return jsonify(res), 400

# --- UNIFIED POST MANAGEMENT API (Facebook & YouTube) ---

@api_bp.route('/api/v2/post/update/<int:index>', methods=['POST'])
def post_update(index):
    """
    Cập nhật nội dung bài viết (Title, Description, Privacy, Thumbnail) cho FB/YT.
    Payload: Multipart (nếu có file) hoặc JSON.
    """
    # Xử lý dữ liệu từ Form (Multipart) hoặc JSON
    if request.content_type.startswith('multipart/form-data'):
        data = request.form.to_dict()
        thumbnail = request.files.get('thumbnail')
    else:
        data = request.json
        thumbnail = None

    res = post_manager.update_post_content("Published_History", index, data, thumbnail_file=thumbnail)
    if res["success"]:
        return jsonify(res)
    return jsonify(res), 400

@api_bp.route('/api/v2/post/delete/<int:index>', methods=['DELETE'])
def post_delete_published(index):
    """Xóa bài viết đã đăng khỏi Platform và History."""
    res = post_manager.delete_published_post("Published_History", index)
    if res["success"]:
        return jsonify(res)
    return jsonify(res), 400

@api_bp.route('/api/v2/post/sync-thumbnail/<int:index>', methods=['POST'])
def post_sync_thumbnail(index):
    """Đồng bộ thumbnail từ Platform về Sheet."""
    res = post_manager.sync_thumbnail("Published_History", index)
    if res["success"]:
        return jsonify(res)
    return jsonify(res), 400

@api_bp.route('/api/v2/post/publish-now', methods=['POST'])
def post_publish_now():
    """
    Publish ngay lập tức một bài đang Scheduled.
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          properties:
            index:
              type: integer
    responses:
      200:
        description: Thành công
    """
    try:
        data = request.json
        index = data.get('index')
        manager = PostManager()
        res = manager.publish_now(index)
        return jsonify(res)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route('/api/v2/post/details/<int:index>', methods=['GET'])
def post_get_details(index):
    """Lấy thông tin chi tiết bài viết từ Platform."""
    res = post_manager.get_post_details("Published_History", index)
    if res["success"]:
        return jsonify(res)
    return jsonify(res), 400

# --- WOOCOMMERCE ENDPOINTS ---

@api_bp.route('/api/v2/woocommerce/config', methods=['GET', 'POST'])
def woocommerce_config():
    """Lấy hoặc lưu cấu hình WooCommerce."""
    if request.method == 'POST':
        data = request.json
        try:
            # SheetService.update_row tự gọi model.from_dict(data)
            SheetService.update_row(WoocommerceConfModel.SHEET_NAME, 0, data)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    else:
        try:
            rows = SheetService.get_all_rows(WoocommerceConfModel.SHEET_NAME)
            config = rows[0] if rows else {}
            return jsonify(config)
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route('/api/v2/woocommerce/categories', methods=['GET'])
def woocommerce_categories():
    """Lấy danh sách categories từ WooCommerce."""
    try:
        rows = SheetService.get_all_rows(WoocommerceConfModel.SHEET_NAME)
        if not rows:
            return jsonify({"error": "Chưa cấu hình WooCommerce"}), 400
        
        config = rows[0]
        publisher = WoocommercePublisher(
            config.get('site_url'), 
            config.get('consumer_key'), 
            config.get('consumer_secret'),
            wp_user=config.get('wp_user'),
            wp_app_pass=config.get('wp_app_pass')
        )
        res = publisher.get_categories()
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/v2/woocommerce/analyze', methods=['POST'])
def woocommerce_analyze():
    """Phân tích URL sản phẩm bằng AI."""
    data = request.json
    url = data.get('url')
    api_key = data.get('api_key')
    system_prompt = data.get('system_prompt')

    youtube_url = data.get('youtube_url')

    if not url or not api_key:
        return jsonify({"error": "Thiếu URL hoặc API Key"}), 400

    try:
        analyzer = URLAnalyzer(api_key, system_prompt)
        raw_info = analyzer.scrape_product_info(url)
        seo_content = analyzer.generate_seo_product(raw_info, youtube_url=youtube_url)
        return jsonify(seo_content)
    except Exception as e:
        error_msg = str(e)
        status_code = 500
        if any(code in error_msg for code in ["429", "Too Many Requests", "exhausted"]):
            status_code = 429
        elif "503" in error_msg or "Service Unavailable" in error_msg:
            status_code = 503
        elif "403" in error_msg or "Permission denied" in error_msg:
            status_code = 403
        return jsonify({"error": error_msg}), status_code

@api_bp.route('/api/v2/haravan/analyze', methods=['POST'])
def haravan_analyze():
    """Phân tích URL sản phẩm bằng AI (Dành cho Haravan)."""
    data = request.json
    url = data.get('url') # Can be passed as 'url' or inferred from prompt in frontend, but better explicit.
    # Frontend script currently sends system_prompt/user_prompt to ai/generate.
    # We will change frontend to send url/api_key like woo.
    
    api_key = data.get('api_key')
    system_prompt = data.get('system_prompt')
    youtube_url = data.get('youtube_url')

    if not url or not api_key:
        return jsonify({"error": "Thiếu URL hoặc API Key"}), 400

    try:
        # Reuse URLAnalyzer - it is generic enough for product scraping
        analyzer = URLAnalyzer(api_key, system_prompt)
        raw_info = analyzer.scrape_product_info(url)
        
        # We might want to customize the prompt for Haravan if needed, 
        # but the generic SEO product generation is likely fine.
        # The prompt usually instructs output format.
        seo_content = analyzer.generate_seo_product(raw_info, youtube_url=youtube_url)
        return jsonify(seo_content)
    except Exception as e:
        error_msg = str(e)
        status_code = 500
        if any(code in error_msg for code in ["429", "Too Many Requests", "exhausted"]):
            status_code = 429
        elif "503" in error_msg or "Service Unavailable" in error_msg:
            status_code = 503
        elif "403" in error_msg or "Permission denied" in error_msg:
            status_code = 403
        return jsonify({"error": error_msg}), status_code

@api_bp.route('/api/v2/haravan/collections', methods=['GET'])
def haravan_collections():
    """Lấy danh sách nhóm sản phẩm (Collections) từ Haravan."""
    from post_service.haravan_publisher import HaravanPublisher
    try:
        configs = SheetService.get_all_rows("Haravan_Config")
        if not configs:
            return jsonify({"error": "Chưa cấu hình Haravan"}), 400
        
        config = configs[0]
        shop_url = config.get("shop_url")
        token = config.get("access_token")
        
        if not shop_url or not token:
            return jsonify({"error": "Thiếu Shop URL hoặc Access Token"}), 400
        
        publisher = HaravanPublisher(shop_url, token)
        
        # Fetch both custom and smart collections
        custom_res = publisher.get_custom_collections()
        smart_res = publisher.get_smart_collections()
        
        result = {
            "custom_collections": custom_res.get("data", {}).get("custom_collections", []) if custom_res.get("success") else [],
            "smart_collections": smart_res.get("data", {}).get("smart_collections", []) if smart_res.get("success") else []
        }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/v2/haravan/product-types', methods=['GET'])
def haravan_product_types():
    """Lấy danh sách Product Types và Vendors từ Haravan."""
    from post_service.haravan_publisher import HaravanPublisher
    try:
        configs = SheetService.get_all_rows("Haravan_Config")
        if not configs:
            return jsonify({"error": "Chưa cấu hình Haravan"}), 400
        
        config = configs[0]
        shop_url = config.get("shop_url")
        token = config.get("access_token")
        
        if not shop_url or not token:
            return jsonify({"error": "Thiếu Shop URL hoặc Access Token"}), 400
        
        publisher = HaravanPublisher(shop_url, token)
        result = publisher.get_product_types()
        
        if result.get("success"):
            return jsonify({
                "product_types": result.get("types", []),
                "vendors": result.get("vendors", [])
            })
        return jsonify({"error": result.get("error", "Unknown error")}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/v2/woocommerce/db', methods=['GET'])
def woocommerce_db():
    """Lấy danh sách sản phẩm từ Woocommerce_db."""
    try:
        rows = SheetService.get_all_rows(WoocommerceDbModel.SHEET_NAME)
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/v2/woocommerce/import-csv', methods=['POST'])
def woocommerce_import_csv():
    """Import sản phẩm từ file CSV."""
    if 'file' not in request.files:
        return jsonify({"error": "Không tìm thấy file"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "File trống"}), 400

    try:
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        reader = csv.DictReader(stream)
        
        count = 0
        for row in reader:
            # Thu thập data với fallback cho nhiều loại header phổ biến
            def get_val(keys, default=''):
                for k in keys:
                    v = row.get(k)
                    if v is not None: return str(v).strip()
                return default

            product = {
                "title": get_val(['title', 'Title', 'Product Name', 'Name', 'product_name']),
                "regular_price": get_val(['regular_price', 'Regular price', 'Price', 'price', 'Gia']),
                "sale_price": get_val(['sale_price', 'Sale price', 'Gia sales', 'Gia khuyen mai']),
                "description": get_val(['description', 'Description', 'Mo ta', 'Content']),
                "short_description": get_val(['short_description', 'Short description', 'Mo ta ngan', 'Excerpt']),
                "categories": get_val(['categories', 'Categories', 'Danh muc', 'Category']),
                "images": get_val(['images', 'Images', 'Anh', 'Image URLs']),
                "post_status": get_val(['post_status', 'Status', 'Trang thai'], 'publish'),
                "status": "NEW"
            }
            if product["title"]:
                SheetService.append_row(WoocommerceDbModel.SHEET_NAME, product)
                count += 1
            
        return jsonify({"success": True, "imported": count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/v2/woocommerce/bulk-analyze', methods=['POST'])
def woocommerce_bulk_analyze():
    """Nhận file CSV chứa list link sản phẩm và bắt đầu phân tích hàng loạt."""
    if 'file' not in request.files:
        return jsonify({"error": "Không tìm thấy file"}), 400
    
    file = request.files['file']
    api_key = request.form.get('api_key')
    system_prompt = request.form.get('system_prompt')
    
    if not api_key:
        return jsonify({"error": "Thiếu Gemini API Key"}), 400

    try:
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        reader = csv.reader(stream)
        urls = []
        for row in reader:
            if row:
                # Giả định URL nằm ở cột đầu tiên nếu không có header, hoặc tìm link
                for cell in row:
                    if cell.startswith('http'):
                        urls.append(cell.strip())
                        break
        
        if not urls:
            return jsonify({"error": "Không tìm thấy URL nào trong file"}), 400
            
        task_id = str(uuid.uuid4())
        from logic import background_bulk_analyze
        import threading
        thread = threading.Thread(target=background_bulk_analyze, args=(task_id, urls, api_key, system_prompt))
        thread.start()
        
        return jsonify({"success": True, "task_id": task_id, "count": len(urls)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/v2/woocommerce/add-item', methods=['POST'])
def woocommerce_add_item():
    """
    Thêm một sản phẩm đơn lẻ vào hàng đợi đăng.
    Hỗ trợ cả JSON và Multipart Form Data (để upload ảnh lên Drive).
    """
    try:
        if request.is_json:
            data = request.json
        else:
            # Xử lý Multipart Form Data
            data = request.form.to_dict()
            uploaded_files = request.files.getlist('image_files')
            parent_id = data.get('parent_folder_id', 'root')
            
            if uploaded_files:
                from logic import upload_product_images_to_drive
                files_data = []
                for f in uploaded_files:
                    if f.filename:
                        files_data.append({
                            'filename': f.filename,
                            'content': f.read(),
                            'content_type': f.content_type
                        })
                
                if files_data:
                    drive_links = upload_product_images_to_drive(data.get('title', 'Product'), files_data, parent_id)
                    if drive_links:
                        # Ghép thêm vào danh sách ảnh hiện có (nếu AI đã cào được ảnh từ link)
                        existing_images = data.get('images', '')
                        new_images_list = [existing_images] if existing_images else []
                        new_images_list.extend(drive_links)
                        data['images'] = ",".join(filter(None, new_images_list))
                        
                        # [FIX] Chèn ảnh vào cuối bài viết để giải quyết yêu cầu của người dùng
                        added_imgs_html = "".join([f'<p style="text-align: center;"><img src="{url}" alt="{data.get("title")}" style="max-width:100%; height:auto;" /></p>' for url in drive_links])
                        data['description'] = data.get('description', '') + added_imgs_html
        
        if not data.get('title'):
            return jsonify({"error": "Thiếu tiêu đề sản phẩm"}), 400
        
        data["status"] = "NEW"
        # Đảm bảo có cột post_status (nếu chưa có từ data)
        if not data.get('post_status'):
            data['post_status'] = 'publish' 

        from services.sheet_service import SheetService
        from models.Woocommerce_db import WoocommerceDbModel
        SheetService.append_row(WoocommerceDbModel.SHEET_NAME, data)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/v2/woocommerce/update-item', methods=['POST'])
def woocommerce_update_item():
    """Cập nhật thông tin sản phẩm trong hàng đợi."""
    data = request.json
    index = data.get('index')
    update_data = data.get('data')
    try:
        from services.sheet_service import SheetService
        from models.Woocommerce_db import WoocommerceDbModel
        
        SheetService.update_row(WoocommerceDbModel.SHEET_NAME, index, update_data)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/v2/woocommerce/delete-item', methods=['POST'])
def woocommerce_delete_item():
    """Xóa sản phẩm khỏi hàng đợi."""
    data = request.json
    index = data.get('index')
    try:
        from services.sheet_service import SheetService
        from models.Woocommerce_db import WoocommerceDbModel
        
        SheetService.delete_row(WoocommerceDbModel.SHEET_NAME, index)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- HARAVAN ADVANCED API ---
from post_service.haravan_publisher import HaravanPublisher
from models.Haravan_Config import HaravanConfModel

def get_haravan_publisher():
    """Helper to get initialized HaravanPublisher locally"""
    configs = SheetService.get_all_rows("Haravan_Config")
    if not configs:
        return None
    conf = configs[0]
    return HaravanPublisher(conf.get("shop_url"), conf.get("access_token"))

@api_bp.route('/api/v2/haravan/collections', methods=['GET'])
def get_haravan_collections():
    """Fetch Custom and Smart collections"""
    publisher = get_haravan_publisher()
    if not publisher:
        return jsonify({"success": False, "error": "Haravan config missing"}), 400
    
    try:
        custom = publisher.get_custom_collections()
        smart = publisher.get_smart_collections()
        
        collections = []
        if custom.get("success"):
            collections.extend(custom["data"].get("custom_collections", []))
        if smart.get("success"):
            collections.extend(smart["data"].get("smart_collections", []))
            
        return jsonify({"success": True, "collections": collections})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route('/api/v2/haravan/metadata', methods=['GET'])
def get_haravan_metadata():
    """Fetch Product Types and Vendors"""
    publisher = get_haravan_publisher()
    if not publisher:
        return jsonify({"success": False, "error": "Haravan config missing"}), 400
        
    try:
        res = publisher.get_product_types()
        return jsonify(res)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route('/api/v2/haravan/upload-image', methods=['POST'])
def haravan_upload_image():
    """
    Upload local image to Haravan (Draft Product approach OR direct update if PID known).
    Wait, Haravan API requires a product_id to upload image.
    Strategy:
    1. If product_id provided, upload to it.
    2. If not, we cannot upload 'orphan' images easily like WP.
    
    ALTERNATIVE: We return base64 string to Frontend, and Frontend embeds it in the 'Create Product' payload.
    Haravan 'Create Product' API supports "images": [{"attachment": "base64"}] directly.
    
    So we don't necessarily need a standalone upload endpoint unless we want to host it somewhere.
    BUT, to support 'Preview' we might want to return the base64.
    
    Actually, let's keep this simple:
    Frontend converts file to Base64 -> Sends to Create/Update Product API.
    Backend 'publish_item' logic already exists.
    
    We might need an endpoint to "Test Upload" or similar?
    Let's stick to Metadata endpoints for now.
    """
    return jsonify({"message": "Use Create Product payload for images"}), 200
