from flasgger import Swagger
from flask import Flask, request, jsonify, send_from_directory, redirect
import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from werkzeug.utils import secure_filename

app = Flask(__name__, static_url_path='', static_folder='.')
swagger = Swagger(app)

# CONSTANTS
PORT = 3000
TOKEN_FILE = 'token.json'
CREDENTIALS_FILE = 'assect/AouthGoogle.json'
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets"
]
UPLOAD_FOLDER = 'uploads_temp'

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_creds():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(f"Could not find credentials file at {CREDENTIALS_FILE}")
                
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            # Use port 5001 to avoid common Mac port conflicts (like 8080 AirPlay)
            creds = flow.run_local_server(port=5001, host='localhost')
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            
    return creds

@app.route('/')
def root():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def send_static(path):
    return send_from_directory('.', path)

@app.route('/api/auth/login')
def login():
    """
    Initiate Google OAuth login flow.
    ---
    responses:
      302:
        description: Redirect to Google Auth or Home
    """
    try:
        get_creds()
        return redirect('/')
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/api/auth/status')
def auth_status():
    """
    Check if the user is authenticated with Google.
    ---
    responses:
      200:
        description: Authentication status and user email
    """
    if os.path.exists(TOKEN_FILE):
        try:
            creds = get_creds()
            service = build('drive', 'v3', credentials=creds)
            about = service.about().get(fields="user").execute()
            return jsonify({
                "connected": True, 
                "email": about['user']['emailAddress']
            })
        except Exception as e:
            return jsonify({"connected": False, "error": str(e)})
    return jsonify({"connected": False})

import threading
import uuid

# Storage for task status
tasks = {}

@app.route('/api/tasks')
def get_tasks():
    return jsonify(tasks)

@app.route('/api/sheets/full-data')
def get_full_sheet_data():
    """
    Fetch all data from every tab in a Google Spreadsheet.
    ---
    parameters:
      - name: sheetId
        in: query
        type: string
        required: true
        description: The ID of the Google Spreadsheet
    responses:
      200:
        description: Success - Returns title and data for all sheets
      400:
        description: Missing sheetId
      500:
        description: Server error
    """
    sheet_id = request.args.get('sheetId')
    if not sheet_id:
        return jsonify({"error": "Missing sheetId parameter"}), 400
    
    try:
        creds = get_creds()
        service = build('sheets', 'v4', credentials=creds)
        
        # 1. Get Spreadsheet metadata to find all sheet names
        spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheets_metadata = spreadsheet.get('sheets', [])
        
        full_data = {
            "title": spreadsheet.get('properties', {}).get('title', 'Unknown'),
            "sheets": []
        }
        
        # 2. Fetch data for each sheet
        for sheet in sheets_metadata:
            props = sheet.get('properties', {})
            title = props.get('title')
            sheet_id_val = props.get('sheetId')
            
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id, 
                range=title
            ).execute()
            
            full_data["sheets"].append({
                "title": title,
                "sheetId": sheet_id_val,
                "values": result.get('values', [])
            })
            
        return jsonify(full_data)
        
    except Exception as e:
        print(f"Error fetching sheet data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/sheets/single-data')
def get_single_sheet_data():
    """
    Fetch data from a specific tab (sheet name) in a Google Spreadsheet.
    ---
    parameters:
      - name: sheetId
        in: query
        type: string
        required: true
        description: The ID of the Google Spreadsheet
      - name: sheetName
        in: query
        type: string
        required: true
        description: The name/title of the tab (e.g., 'Sheet1')
    responses:
      200:
        description: Success - Returns data for the specified sheet
      400:
        description: Missing parameters
      500:
        description: Server error
    """
    sheet_id = request.args.get('sheetId')
    sheet_name = request.args.get('sheetName')
    
    if not sheet_id or not sheet_name:
        return jsonify({"error": "Missing sheetId or sheetName parameter"}), 400
    
    try:
        creds = get_creds()
        service = build('sheets', 'v4', credentials=creds)
        
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id, 
            range=sheet_name
        ).execute()
        
        return jsonify({
            "sheetName": sheet_name,
            "values": result.get('values', [])
        })
        
    except Exception as e:
        print(f"Error fetching single sheet data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/sheets/tabs', methods=['POST'])
def create_sheet_tab():
    """
    Create a new tab in the spreadsheet.
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
        description: Tab created successfully
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

@app.route('/api/sheets/tabs', methods=['DELETE'])
def delete_sheet_tab():
    """
    Delete a tab from the spreadsheet.
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
        description: Tab deleted successfully
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

@app.route('/api/sheets/rows', methods=['PUT'])
def update_sheet_row():
    """
    Update a specific row in a spreadsheet.
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
        description: Row updated successfully
    """
    data = request.json
    sheet_id = data.get('sheetId')
    sheet_name = data.get('sheetName')
    row_index = data.get('rowIndex') # 0-indexed
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

@app.route('/api/sheets/rows', methods=['DELETE'])
def delete_sheet_row():
    """
    Delete a specific row from a spreadsheet.
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
        description: Row deleted successfully
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

def background_upload(task_id, form_data, files_data):
    try:
        tasks[task_id] = {"status": "processing", "progress": "Starting upload..."}
        
        creds = get_creds()
        drive_service = build('drive', 'v3', credentials=creds)
        sheet_service = build('sheets', 'v4', credentials=creds)

        parent_id = form_data.get('parentId')
        sheet_id = form_data.get('sheetId')
        folder_name = form_data.get('folderName')
        topic = form_data.get('topic', '')
        
        # 1. Create Subfolders
        def create_folder(name, pid):
            meta = {'name': name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [pid]}
            f = drive_service.files().create(body=meta, fields='id').execute()
            return f.get('id')

        tasks[task_id]["progress"] = "Creating folders..."
        image_folder_id = create_folder(f"{folder_name}-image", parent_id)
        video_folder_id = create_folder(f"{folder_name}-video", parent_id)

        uploaded_links = {'videos': [], 'images': [], 'thumb': ''}
        
        # Helper to upload
        def upload_to_drive(file_bytes, filename, content_type, folder_id):
            temp_name = f"{task_id}_{secure_filename(filename)}"
            filepath = os.path.join(UPLOAD_FOLDER, temp_name)
            with open(filepath, 'wb') as f:
                f.write(file_bytes)
            
            meta = {'name': filename, 'parents': [folder_id]}
            media = MediaFileUpload(filepath, mimetype=content_type, resumable=True)
            
            f = drive_service.files().create(body=meta, media_body=media, fields='id,webViewLink').execute()
            
            os.remove(filepath)
            return f.get('webViewLink')

        # 2. Upload Thumbnail
        if 'thumbnail' in files_data:
            tasks[task_id]["progress"] = "Uploading thumbnail..."
            t = files_data['thumbnail']
            link = upload_to_drive(t['content'], t['filename'], t['content_type'], image_folder_id)
            uploaded_links['thumb'] = link

        # 3. Upload Files
        for i, f in enumerate(files_data.get('files', [])):
            tasks[task_id]["progress"] = f"Uploading file {i+1}/{len(files_data['files'])}..."
            is_video = f['content_type'].startswith('video/')
            target_id = video_folder_id if is_video else image_folder_id
            
            link = upload_to_drive(f['content'], f['filename'], f['content_type'], target_id)
            if is_video:
                uploaded_links['videos'].append(link)
            else:
                uploaded_links['images'].append(link)

        # 4. Update Sheet
        tasks[task_id]["progress"] = "Updating Google Sheet..."
        
        # Get starting STT
        res = sheet_service.spreadsheets().values().get(spreadsheetId=sheet_id, range='Content!A:A').execute()
        current_rows_count = len(res.get('values', []))
        next_stt = current_rows_count if current_rows_count > 0 else 1

        all_new_rows = []
        thumb_link = uploaded_links['thumb']

        # - Each Video gets its own row
        for v_link in uploaded_links['videos']:
            row = [
                next_stt,   # A: STT
                "",         # B
                "",         # C
                "Chờ Đăng", # D: Status
                "",         # E
                "Có",       # F: "Có"
                "",         # G
                folder_name,# H: Chủ đề
                "",         # I
                "",         # J
                "",         # K
                "",         # L
                v_link,     # M: Video Link
                thumb_link, # N: Thumbnail
                ""          # O: Image Link (Empty)
            ]
            all_new_rows.append(row)
            next_stt += 1

        # - All Images together in one row
        if uploaded_links['images']:
            # Max 9 images horizontally as per typical sheet structure O-W
            img_links = uploaded_links['images'][:9]
            row = [
                next_stt,   # A: STT
                "",         # B
                "",         # C
                "Chờ Đăng", # D: Status
                "",         # E
                "Có",       # F: "Có"
                "",         # G
                folder_name,# H: Chủ đề
                "",         # I
                "",         # J
                "",         # K
                "",         # L
                "",         # M: Video Link (Empty)
                thumb_link, # N: Thumbnail
                *img_links  # O, P, Q...: All Image Links
            ]
            all_new_rows.append(row)
            next_stt += 1

        if all_new_rows:
            sheet_service.spreadsheets().values().append(
                spreadsheetId=sheet_id,
                range='Content!A:A',
                valueInputOption='USER_ENTERED',
                body={"values": all_new_rows}
            ).execute()

        tasks[task_id] = {"status": "success", "progress": "Completed!", "message": f"Created {len(all_new_rows)} rows for '{folder_name}'."}

    except Exception as e:
        print(f"Task Error: {e}")
        tasks[task_id] = {"status": "error", "progress": "Failed", "message": str(e)}

@app.route('/api/upload', methods=['POST'])
def upload_files():
    try:
        # We must read files now as the request context will be lost in thread
        form_data = {
            'parentId': request.form.get('parentId'),
            'sheetId': request.form.get('sheetId'),
            'folderName': request.form.get('folderName'),
            'topic': request.form.get('topic')
        }
        
        files_data = {'files': []}
        if 'thumbnail' in request.files:
            t = request.files['thumbnail']
            files_data['thumbnail'] = {
                'content': t.read(),
                'filename': t.filename,
                'content_type': t.content_type
            }
        
        files = request.files.getlist('files')
        for f in files:
            if f.filename != '':
                files_data['files'].append({
                    'content': f.read(),
                    'filename': f.filename,
                    'content_type': f.content_type
                })

        task_id = str(uuid.uuid4())
        tasks[task_id] = {"status": "queued", "progress": "Initializing..."}
        
        thread = threading.Thread(target=background_upload, args=(task_id, form_data, files_data))
        thread.start()

        return jsonify({"status": "queued", "task_id": task_id, "message": "Upload started in background. You can continue or leave."})

    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Use environment variables for port to support various deployment platforms
    run_port = int(os.environ.get("PORT", PORT))
    print(f"Backend Server running on http://0.0.0.0:{run_port}")
    app.run(host='0.0.0.0', port=run_port, debug=False)
