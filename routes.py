import os
import re
import uuid
import threading
from flask import Blueprint, request, jsonify, redirect
from googleapiclient.discovery import build
from logic import get_creds, tasks, background_upload, delete_drive_file, TOKEN_FILE
from services.sheet_service import SheetService

# Khởi tạo Blueprint cho các API
api_bp = Blueprint('api', __name__)

# --- API XÁC THỰC (AUTHENTICATION) ---

@api_bp.route('/api/auth/login')
def login():
    """
    Kích hoạt luồng đăng nhập Google OAuth.
    ---
    responses:
      302:
        description: Chuyển hướng đến Google Auth hoặc Trang chủ
    """
    try:
        get_creds()
        return redirect('/')
    except Exception as e:
        return f"Lỗi đăng nhập: {e}", 500

@api_bp.route('/api/auth/status')
def auth_status():
    """
    Kiểm tra trạng thái kết nối với tài khoản Google.
    ---
    responses:
      200:
        description: Trạng thái kết nối và email người dùng
    """
    if os.path.exists(TOKEN_FILE):
        try:
            creds = get_creds()
            service = build('drive', 'v3', credentials=creds)
            # Lấy thông tin tài khoản từ Google Drive API
            about = service.about().get(fields="user").execute()
            return jsonify({
                "connected": True, 
                "email": about['user']['emailAddress']
            })
        except Exception as e:
            return jsonify({"connected": False, "error": str(e)})
    return jsonify({"connected": False})

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
