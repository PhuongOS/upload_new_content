from flask import Flask, request, jsonify, send_from_directory, redirect
import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from werkzeug.utils import secure_filename

app = Flask(__name__, static_url_path='', static_folder='.')

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
    try:
        get_creds()
        return redirect('/')
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/api/auth/status')
def auth_status():
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
    print(f"Backend Server running on http://localhost:{PORT}")
    app.run(port=PORT, debug=True)
