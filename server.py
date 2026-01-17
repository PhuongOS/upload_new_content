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

@app.route('/api/upload', methods=['POST'])
def upload_files():
    try:
        creds = get_creds()
        drive_service = build('drive', 'v3', credentials=creds)
        sheet_service = build('sheets', 'v4', credentials=creds)

        parent_id = request.form.get('parentId')
        sheet_id = request.form.get('sheetId')
        folder_name = request.form.get('folderName')
        
        # 1. Create Subfolders
        def create_folder(name, pid):
            meta = {'name': name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [pid]}
            f = drive_service.files().create(body=meta, fields='id').execute()
            return f.get('id')

        image_folder_id = create_folder(f"{folder_name}-image", parent_id)
        video_folder_id = create_folder(f"{folder_name}-video", parent_id)

        uploaded_links = {'videos': [], 'images': [], 'thumb': ''}
        
        # Helper to upload
        def upload_to_drive(file_storage, folder_id):
            filename = secure_filename(file_storage.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file_storage.save(filepath)
            
            meta = {'name': file_storage.filename, 'parents': [folder_id]}
            media = MediaFileUpload(filepath, resumable=True)
            
            f = drive_service.files().create(body=meta, media_body=media, fields='id,webViewLink').execute()
            
            # Cleanup
            os.remove(filepath)
            return f.get('webViewLink')

        # 2. Upload Thumbnail
        if 'thumbnail' in request.files:
            thumb = request.files['thumbnail']
            if thumb.filename != '':
                link = upload_to_drive(thumb, image_folder_id)
                uploaded_links['thumb'] = link

        # 3. Upload Files
        files = request.files.getlist('files')
        for f in files:
            if f.filename == '': continue
            
            is_video = f.content_type.startswith('video/')
            target_id = video_folder_id if is_video else image_folder_id
            
            link = upload_to_drive(f, target_id)
            if is_video:
                uploaded_links['videos'].append(link)
            else:
                uploaded_links['images'].append(link)

        # 4. Update Sheet
        # Get next STT
        res = sheet_service.spreadsheets().values().get(spreadsheetId=sheet_id, range='Content!A:A').execute()
        num_rows = len(res.get('values', []))
        next_stt = num_rows if num_rows > 0 else 1
        
        # Determine image links (slice to max 9)
        img_links = uploaded_links['images'][:9]
        # Pad with empty strings if less than 9
        while len(img_links) < 9:
            img_links.append("")

        row = [
            next_stt, "", "", "Chờ Đăng", "", "Có", "", "", "", "", "", "",
            uploaded_links['videos'][0] if uploaded_links['videos'] else "",
            uploaded_links['thumb'],
            *img_links
        ]

        sheet_service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range='Content!A:A',
            valueInputOption='USER_ENTERED',
            body={"values": [row]}
        ).execute()

        return jsonify({"status": "success", "message": "Upload Completed!"})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    print(f"Backend Server running on http://localhost:{PORT}")
    app.run(port=PORT, debug=True)
