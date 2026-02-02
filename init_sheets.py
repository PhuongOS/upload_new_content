from googleapiclient.discovery import build
from logic import get_creds
from models.History_db import HistoryDbModel
from models.Haravan_db import HaravanDbModel
from models.Haravan_Config import HaravanConfModel

def init_sheets():
    """Khởi tạo các tab cần thiết."""
    creds = get_creds()
    service = build('sheets', 'v4', credentials=creds)
    spreadsheet_id = HistoryDbModel.SPREADSHEET_ID # Sử dụng chung ID

    tabs_to_create = [
        {
            "title": HistoryDbModel.SHEET_NAME,
            "headers": ["STT", "Platform", "Post_ID", "Title", "Publish_Date", "Direct_Link", "Thumbnail_URL", "Status", "Raw_Data"]
        },
        {
            "title": HaravanDbModel.SHEET_NAME,
            "headers": ["STT", "Product Title", "Regular Price", "Sale Price", "Description", "Short Description", "Product Type", "Vendor", "Tags", "Images URL", "Status", "Haravan ID", "Haravan Link"]
        },
        {
            "title": HaravanConfModel.SHEET_NAME,
            "headers": ["Shop URL", "Access Token"]
        }
    ]

    for tab in tabs_to_create:
        try:
            body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': tab["title"],
                            'gridProperties': {'rowCount': 1000, 'columnCount': 20}
                        }
                    }
                }]
            }
            service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
            print(f"✅ Đã tạo tab {tab['title']}.")
        except Exception as e:
            print(f"ℹ️ Tab {tab['title']} đã tồn tại hoặc có lỗi: {e}")

        # Cập nhật tiêu đề
        try:
             service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{tab['title']}!A1",
                valueInputOption="USER_ENTERED",
                body={"values": [tab["headers"]]}
            ).execute()
             print(f"✅ Đã cập nhật header cho {tab['title']}.")
        except Exception as e:
             print(f"❌ Lỗi cập nhật header {tab['title']}: {e}")

if __name__ == "__main__":
    init_sheets()
