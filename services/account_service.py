# FILE: services/account_service.py
# Service quản lý Multi-Account cho YouTube

import os
import json
import uuid
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# --- CONSTANTS ---
TOKENS_DIR = 'tokens'
ACCOUNTS_FILE = os.path.join(TOKENS_DIR, 'accounts.json')
CREDENTIALS_FILE = 'assect/AouthGoogle.json'

# Scopes cần thiết cho YouTube và User Info
YOUTUBE_SCOPES = [
    "openid",  # Required when using userinfo scopes
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]

# Đảm bảo thư mục tokens tồn tại
os.makedirs(TOKENS_DIR, exist_ok=True)


class AccountService:
    """Service quản lý nhiều tài khoản Google cho YouTube."""

    @staticmethod
    def _load_accounts():
        """Load danh sách tài khoản từ file JSON."""
        if os.path.exists(ACCOUNTS_FILE):
            with open(ACCOUNTS_FILE, 'r') as f:
                return json.load(f)
        return {}

    @staticmethod
    def _save_accounts(accounts):
        """Lưu danh sách tài khoản vào file JSON."""
        with open(ACCOUNTS_FILE, 'w') as f:
            json.dump(accounts, f, indent=2, ensure_ascii=False)

    @staticmethod
    def list_accounts():
        """Liệt kê tất cả tài khoản đã kết nối."""
        accounts = AccountService._load_accounts()
        result = []
        for acc_id, info in accounts.items():
            result.append({
                "id": acc_id,
                "email": info.get("email"),
                "name": info.get("name"),
                "picture": info.get("picture"),
                "channels": info.get("channels", [])
            })
        return result

    @staticmethod
    def get_account(account_id):
        """Lấy thông tin một tài khoản."""
        accounts = AccountService._load_accounts()
        return accounts.get(account_id)

    @staticmethod
    def add_account_start():
        """
        Bắt đầu flow OAuth để thêm tài khoản mới.
        Trả về URL để redirect user đến consent screen.
        """
        if not os.path.exists(CREDENTIALS_FILE):
            raise FileNotFoundError(f"Không tìm thấy file credentials tại {CREDENTIALS_FILE}")

        # Tạo account_id tạm để tracking
        temp_id = str(uuid.uuid4())[:8]
        
        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE, 
            YOUTUBE_SCOPES,
            redirect_uri='http://localhost:8080/'  # Hoặc URL callback của bạn
        )
        
        # Lưu state để verify callback
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'  # Force consent để luôn nhận refresh_token
        )
        
        return {
            "auth_url": auth_url,
            "state": state,
            "temp_id": temp_id
        }

    @staticmethod
    def add_account_interactive():
        """
        Thêm tài khoản mới bằng flow interactive (mở browser).
        Dùng cho môi trường local.
        """
        if not os.path.exists(CREDENTIALS_FILE):
            raise FileNotFoundError(f"Không tìm thấy file credentials tại {CREDENTIALS_FILE}")

        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, YOUTUBE_SCOPES)
        
        try:
            creds = flow.run_local_server(port=8080, host='localhost', open_browser=True)
        except Exception as e:
            raise RuntimeError(f"Không thể mở trình duyệt để xác thực: {e}")

        # Lấy thông tin user
        user_info = AccountService._fetch_user_info(creds)
        channels = AccountService._fetch_youtube_channels(creds)

        # Tạo account ID từ email
        account_id = user_info.get("email", str(uuid.uuid4())[:8]).replace("@", "_at_").replace(".", "_")

        # Lưu token
        token_file = os.path.join(TOKENS_DIR, f"{account_id}.json")
        with open(token_file, 'w') as f:
            f.write(creds.to_json())

        # Lưu metadata
        accounts = AccountService._load_accounts()
        accounts[account_id] = {
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "picture": user_info.get("picture"),
            "channels": channels
        }
        AccountService._save_accounts(accounts)

        # [NEW] Sync channels to Youtube_Config sheet
        sync_result = AccountService._sync_channels_to_sheet(
            channels, 
            user_info.get("email", ""), 
            account_id
        )
        print(f"[AccountService] Synced {sync_result.get('added', 0)} channels to Youtube_Config")

        return {
            "success": True,
            "account_id": account_id,
            "email": user_info.get("email"),
            "channels": channels,
            "synced_to_sheet": sync_result.get('added', 0)
        }

    @staticmethod
    def remove_account(account_id):
        """Xóa tài khoản và token liên quan."""
        accounts = AccountService._load_accounts()
        
        if account_id not in accounts:
            return {"success": False, "error": "Tài khoản không tồn tại"}

        # Xóa token file
        token_file = os.path.join(TOKENS_DIR, f"{account_id}.json")
        if os.path.exists(token_file):
            os.remove(token_file)

        # Xóa khỏi accounts.json
        del accounts[account_id]
        AccountService._save_accounts(accounts)

        return {"success": True}

    @staticmethod
    def get_credentials(account_id):
        """
        Lấy Credentials cho một tài khoản cụ thể.
        Tự động refresh nếu token hết hạn.
        """
        token_file = os.path.join(TOKENS_DIR, f"{account_id}.json")
        
        if not os.path.exists(token_file):
            raise FileNotFoundError(f"Token không tồn tại cho account: {account_id}")

        creds = Credentials.from_authorized_user_file(token_file, YOUTUBE_SCOPES)

        # Refresh nếu cần
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Lưu lại token mới
                with open(token_file, 'w') as f:
                    f.write(creds.to_json())
            except Exception as e:
                raise RuntimeError(f"Lỗi refresh token cho account {account_id}: {e}")

        if not creds or not creds.valid:
            raise PermissionError(f"Token không hợp lệ cho account: {account_id}")

        return creds

    @staticmethod
    def _fetch_user_info(creds):
        """Lấy thông tin user từ Google."""
        try:
            service = build('oauth2', 'v2', credentials=creds)
            user_info = service.userinfo().get().execute()
            return {
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "picture": user_info.get("picture")
            }
        except Exception as e:
            print(f"[AccountService] Lỗi lấy user info: {e}")
            return {}

    @staticmethod
    def _fetch_youtube_channels(creds):
        """Lấy danh sách kênh YouTube của user."""
        try:
            youtube = build('youtube', 'v3', credentials=creds)
            response = youtube.channels().list(
                part='snippet,statistics',
                mine=True
            ).execute()

            channels = []
            for item in response.get('items', []):
                channels.append({
                    "id": item['id'],
                    "title": item['snippet']['title'],
                    "thumbnail": item['snippet']['thumbnails'].get('default', {}).get('url'),
                    "subscribers": item['statistics'].get('subscriberCount', '0')
                })
            return channels
        except Exception as e:
            print(f"[AccountService] Lỗi lấy YouTube channels: {e}")
            return []

    @staticmethod
    def refresh_channels(account_id):
        """Refresh danh sách kênh cho một tài khoản."""
        try:
            creds = AccountService.get_credentials(account_id)
            channels = AccountService._fetch_youtube_channels(creds)

            accounts = AccountService._load_accounts()
            if account_id in accounts:
                accounts[account_id]["channels"] = channels
                AccountService._save_accounts(accounts)

            return {"success": True, "channels": channels}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def _sync_channels_to_sheet(channels, email, account_id):
        """
        Đồng bộ danh sách kênh YouTube vào Google Sheet Youtube_Config.
        - Thêm các kênh chưa tồn tại (dựa trên channel_id)
        - Cập nhật account_id cho các kênh đã tồn tại nhưng chưa có account_id
        """
        from services.sheet_service import SheetService
        
        added_count = 0
        updated_count = 0
        try:
            # Lấy danh sách kênh đã có trong Sheet
            existing_configs = SheetService.get_all_rows("Youtube_Config")
            
            # Tạo map channel_id -> (index, config)
            existing_map = {}
            for idx, config in enumerate(existing_configs):
                cid = config.get("channel_id")
                if cid:
                    existing_map[cid] = (idx, config)
            
            # Xử lý từng kênh
            for channel in channels:
                channel_id = channel.get("id")
                if not channel_id:
                    continue
                    
                if channel_id in existing_map:
                    # Kênh đã tồn tại - kiểm tra xem cần cập nhật account_id không
                    row_idx, existing_config = existing_map[channel_id]
                    existing_account_id = existing_config.get("account_id", "").strip()
                    
                    if not existing_account_id:
                        # Cập nhật account_id cho kênh đã tồn tại
                        updated_config = {
                            "channel_name": existing_config.get("channel_name", channel.get("title", "")),
                            "channel_id": channel_id,
                            "gmail_channel": email or existing_config.get("gmail_channel", ""),
                            "account_id": account_id
                        }
                        try:
                            SheetService.update_row("Youtube_Config", row_idx, updated_config)
                            updated_count += 1
                            print(f"[AccountService] Updated account_id for channel: {channel.get('title')}")
                        except Exception as e:
                            print(f"[AccountService] Error updating channel {channel.get('title')}: {e}")
                else:
                    # Kênh mới - thêm vào Sheet
                    new_row = {
                        "channel_name": channel.get("title", ""),
                        "channel_id": channel_id,
                        "gmail_channel": email,
                        "account_id": account_id
                    }
                    try:
                        SheetService.append_row("Youtube_Config", new_row)
                        added_count += 1
                        print(f"[AccountService] Added channel to Sheet: {channel.get('title')}")
                    except Exception as e:
                        print(f"[AccountService] Error adding channel {channel.get('title')}: {e}")
            
            return {"success": True, "added": added_count, "updated": updated_count}
        except Exception as e:
            print(f"[AccountService] Error syncing channels to sheet: {e}")
            return {"success": False, "added": 0, "updated": 0, "error": str(e)}
