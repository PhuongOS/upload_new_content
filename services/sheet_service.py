from googleapiclient.discovery import build
from models.media_calendar import MediaCalendarModel
from models.Facebook_db import FacebookDbModel
from models.Youtube_db import YoutubeDbModel
from models.Facebook_Config import FacebookConfModel
from models.Youtube_Config import YoutubeConfModel
from models.History_db import HistoryDbModel
from logic import get_creds

class SheetService:
    @staticmethod
    def get_model_by_name(name):
        """Trả về lớp Model tương ứng với tên bảng tính"""
        models = {
            "Media_Calendar": MediaCalendarModel,
            "Facebook_db": FacebookDbModel,
            "Youtube_db": YoutubeDbModel,
            "Facebook_Config": FacebookConfModel,
            "Youtube_Config": YoutubeConfModel,
            "Published_History": HistoryDbModel
        }
        return models.get(name)

    @classmethod
    def get_all_rows(cls, sheet_name):
        """Lấy toàn bộ hàng từ một bảng tính và ánh xạ qua Model"""
        model = cls.get_model_by_name(sheet_name)
        if not model:
            raise ValueError(f"Không tìm thấy model cho bảng tính: {sheet_name}")

        creds = get_creds()
        service = build('sheets', 'v4', credentials=creds)
        
        result = service.spreadsheets().values().get(
            spreadsheetId=model.SPREADSHEET_ID,
            range=f"{sheet_name}!A:Z"
        ).execute()
        
        values = result.get('values', [])
        if not values:
            return []

        # Bỏ qua dòng tiêu đề, chuyển đổi các hàng còn lại thành dictionary
        headers = values[0]
        rows = values[1:]
        
        return [model.to_dict(row) for row in rows]

    @classmethod
    def update_row(cls, sheet_name, row_index, data_dict):
        """Cập nhật một hàng dựa trên dữ liệu Dictionary gửi từ Frontend"""
        model = cls.get_model_by_name(sheet_name)
        if not model:
            raise ValueError(f"Không tìm thấy model cho bảng tính: {sheet_name}")

        creds = get_creds()
        service = build('sheets', 'v4', credentials=creds)
        
        # Chuyển đổi từ Dict ngược lại thành mảng Row chuẩn
        row_array = model.from_dict(data_dict)
        
        # Google Sheets index bắt đầu từ 1, và hàng 1 là tiêu đề -> hàng data bắt đầu từ 2
        range_name = f"{sheet_name}!A{row_index + 2}"
        
        service.spreadsheets().values().update(
            spreadsheetId=model.SPREADSHEET_ID,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body={'values': [row_array]}
        ).execute()
        
        return True

    @classmethod
    def append_row(cls, sheet_name, data_dict):
        """Thêm một hàng mới vào cuối bảng tính"""
        model = cls.get_model_by_name(sheet_name)
        if not model:
            raise ValueError(f"Không tìm thấy model cho bảng tính: {sheet_name}")

        creds = get_creds()
        service = build('sheets', 'v4', credentials=creds)
        
        row_array = model.from_dict(data_dict)
        
        service.spreadsheets().values().append(
            spreadsheetId=model.SPREADSHEET_ID,
            range=f"{sheet_name}!A:A",
            valueInputOption='USER_ENTERED',
            body={'values': [row_array]}
        ).execute()
        
        return True

    @classmethod
    def delete_row(cls, sheet_name, row_index):
        """Xóa hẳn một hàng khỏi trang tính"""
        model = cls.get_model_by_name(sheet_name)
        if not model:
            raise ValueError(f"Không tìm thấy model cho bảng tính: {sheet_name}")

        creds = get_creds()
        service = build('sheets', 'v4', credentials=creds)
        
        # Google Sheets startIndex bắt đầu từ 0. Hàng tiêu đề là 0. 
        # Nếu người dùng muốn xóa hàng dữ liệu số 0 (index 0), thì thực tế là hàng số 1 trên Google Sheets.
        actual_index = row_index + 1 
        
        body = {
            'requests': [{
                'deleteDimension': {
                    'range': {
                        'sheetId': model.TAB_ID,
                        'dimension': 'ROWS',
                        'startIndex': actual_index,
                        'endIndex': actual_index + 1
                    }
                }
            }]
        }
        
        service.spreadsheets().batchUpdate(
            spreadsheetId=model.SPREADSHEET_ID,
            body=body
        ).execute()
        
        return True
