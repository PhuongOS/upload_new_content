from googleapiclient.discovery import build
from logic import get_creds
from models.History_db import HistoryDbModel

def init_history_sheet():
    """Tạo tab Published_History và thêm dòng tiêu đề."""
    creds = get_creds()
    service = build('sheets', 'v4', credentials=creds)
    spreadsheet_id = HistoryDbModel.SPREADSHEET_ID
    
    # 1. Tạo Tab mới (nếu chưa có - cái này có thể lỗi nếu tab đã tồn tại, nên dùng try-except)
    try:
        body = {
            'requests': [{
                'addSheet': {
                    'properties': {
                        'title': 'Published_History',
                        'gridProperties': {'rowCount': 1000, 'columnCount': 10}
                    }
                }
            }]
        }
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
        print("Đã tạo tab Published_History.")
    except Exception as e:
        print("Tab Published_History đã tồn tại hoặc có lỗi:", e)

    # 2. Thêm tiêu đề
    headers = ["STT", "Platform", "Post_ID", "Title", "Publish_Date", "Direct_Link", "Thumbnail_URL", "Status", "Raw_Data"]
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="Published_History!A1",
        valueInputOption="USER_ENTERED",
        body={"values": [headers]}
    ).execute()
    print("Đã cập nhật tiêu đề cho bảng Lịch sử.")

if __name__ == "__main__":
    init_history_sheet()
