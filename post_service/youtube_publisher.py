from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os

class YoutubePublisher:
    """
    Service xử lý upload và quản lý video trên YouTube.
    Hỗ trợ: Upload (Video/Shorts), Xóa, Sửa Metadata và Thumbnail.
    """

    def __init__(self, credentials):
        self.youtube = build('youtube', 'v3', credentials=credentials)

    def upload_video(self, file_path, title, description, category_id="22", tags=None, privacy_status="public", scheduled_time=None):
        """
        Tải video lên YouTube.
        :param scheduled_time: ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)
        """
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags or [],
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False
            }
        }

        # Xử lý đặt lịch đăng bài
        if scheduled_time:
            body['status']['privacyStatus'] = 'private'
            body['status']['publishAt'] = scheduled_time

        media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
        
        try:
            request = self.youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            response = request.execute()
            return {"success": True, "data": response}
        except Exception as e:
            print(f"YouTube Upload Error: {e}")
            return {"success": False, "error": str(e)}

    def update_metadata(self, video_id, title=None, description=None, category_id=None):
        """Cập nhật thông tin cơ bản của video."""
        # 1. Lấy thông tin hiện tại trước (YouTube yêu cầu gửi lại toàn bộ snippet khi update)
        try:
            res = self.youtube.videos().list(part="snippet,status", id=video_id).execute()
            if not res['items']:
                return {"success": False, "error": "Video not found"}
            
            video = res['items'][0]
            snippet = video['snippet']
            
            # 2. Cập nhật các trường mới
            if title: snippet['title'] = title
            if description: snippet['description'] = description
            if category_id: snippet['categoryId'] = category_id
            
            # 3. Thực hiện update
            update_res = self.youtube.videos().update(
                part="snippet",
                body={
                    "id": video_id,
                    "snippet": snippet
                }
            ).execute()
            return {"success": True, "data": update_res}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_thumbnail(self, video_id, thumbnail_path):
        """Cập nhật ảnh thu nhỏ (Thumbnail) cho video."""
        try:
            request = self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            )
            response = request.execute()
            return {"success": True, "data": response}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_video(self, video_id):
        """Xóa video khỏi kênh YouTube."""
        try:
            self.youtube.videos().delete(id=video_id).execute()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
