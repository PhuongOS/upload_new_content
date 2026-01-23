import os
import re
import uuid
import threading
from flask import Blueprint, request, jsonify, redirect
from googleapiclient.discovery import build
from logic import get_creds, tasks, background_upload, delete_drive_file, TOKEN_FILE
from services.sheet_service import SheetService
from services.account_service import AccountService

# Khởi tạo Blueprint cho các API
api_bp = Blueprint('api', __name__)

# --- API XÁC THỰC (AUTHENTICATION) ---

@api_bp.route('/api/auth/login')
def login():
    try:
        get_creds(interactive=True)
        return redirect('/')
    except Exception as e:
        return f"Lỗi đăng nhập: {e}", 500

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
    """Thêm tài khoản Google mới (mở browser để xác thực)."""
    try:
        result = AccountService.add_account_interactive()
        return jsonify(result)
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
            'topic': request.form.get('topic')
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
        if "429" in error_msg or "Too Many Requests" in error_msg:
            status_code = 429
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
