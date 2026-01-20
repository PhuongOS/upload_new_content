import json
import datetime
import os
from googleapiclient.discovery import build
from .facebook_publisher import FacebookPublisher
from .youtube_publisher import YoutubePublisher
from services.sheet_service import SheetService
from logic import get_creds

class PostManager:
    """
    Quản lý luồng công việc đăng bài: 
    1. Lấy dữ liệu từ Sheet (Facebook_db hoặc Youtube_db)
    2. Gọi Publisher tương ứng
    3. Lưu kết quả vào tab Published_History
    """
    
    HISTORY_SHEET = "Published_History"

    def extract_drive_id(self, url):
        """Trích xuất ID file từ link Google Drive."""
        if not url: return None
        
        # Xử lý trường hợp URL là chuỗi JSON list (VD: ["link1", "link2"])
        if isinstance(url, str) and url.strip().startswith('[') and url.strip().endswith(']'):
            try:
                urls = json.loads(url)
                if urls and isinstance(urls, list):
                    url = urls[0] # Lấy link đầu tiên
            except Exception:
                pass # Nếu lỗi parse JSON, coi như string thường

        import re
        patterns = [
            r'[-\w]{25,}', # General ID
            r'id=([-\w]+)', # id=...
            r'd/([-\w]+)',  # /d/...
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(0) if pattern == patterns[0] else match.group(1)
        return None

    def download_from_drive(self, drive_id, output_path):
        """Tải file từ Drive về máy chủ."""
        from googleapiclient.http import MediaIoBaseDownload
        import io
        try:
            creds = get_creds()
            service = build('drive', 'v3', credentials=creds)
            request = service.files().get_media(fileId=drive_id)
            fh = io.FileIO(output_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            fh.close()
            return True
        except Exception as e:
            print(f"Lỗi tải Drive {drive_id}: {e}")
            return False

    def publish_item(self, sheet_name, index):
        """
        Thực hiện đăng bài cho một dòng cụ thể trong Sheet.
        """
        try:
            rows = SheetService.get_all_rows(sheet_name)
            if not rows or index >= len(rows):
                return {"success": False, "error": f"Không tìm thấy dữ liệu tại dòng {index} trong {sheet_name}."}
            
            item = rows[index]
            
            if "Facebook" in sheet_name:
                return self._handle_facebook_publish(item, sheet_name, index)
            elif "Youtube" in sheet_name:
                return self._handle_youtube_publish(item, sheet_name, index)
                
            return {"success": False, "error": "Nền tảng không được hỗ trợ."}
        except Exception as e:
            return {"success": False, "error": f"Lỗi hệ thống: {str(e)}"}

    def _handle_facebook_publish(self, item, sheet_name, index):
        """Xử lý đăng bài lên Facebook và ghi lịch sử."""
        page = item.get('page', {})
        page_id = page.get('id')
        token = page.get('access_token')
        
        message = item.get('hook', '')
        video_title = item.get('video_name', '')
            
        video_url = item.get('video_url')
        post_type = item.get('post_type', 'Status')
        
        if not page_id or not token:
            return {"success": False, "error": "Thiếu Facebook Page ID hoặc Access Token."}

        publisher = FacebookPublisher(page_id, token)
        
        # Flow xử lý Video/Reels: Tải về -> Upload
        if post_type in ["Video", "Reels"] and video_url:
            drive_id = self.extract_drive_id(video_url)
            if not drive_id:
                return {"success": False, "error": "Không lấy được ID video từ link Drive."}
            
            os.makedirs('uploads_temp', exist_ok=True)
            temp_path = os.path.join('uploads_temp', f"fb_{post_type.lower()}_{index}.mp4")
            
            if not self.download_from_drive(drive_id, temp_path):
                return {"success": False, "error": f"Lỗi tải video ID {drive_id} từ Drive."}
                
            try:
                if post_type == "Reels":
                    res = publisher.publish_reel(video_path=temp_path, description=message)
                else:
                    res = publisher.publish_video(video_path=temp_path, title=video_title, description=message)
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        elif post_type in ["Image", "Album"]:
            # Xử lý Album (Nhiều ảnh) hoặc Ảnh đơn
            # Ưu tiên lấy từ Video_url trước (vì tool upload có thể lưu list ảnh vào đây)
            raw_input = item.get('video_url')
            image_urls = []
            
            # Helper parse JSON
            def parse_list(s):
                if isinstance(s, str) and s.strip().startswith('[') and s.strip().endswith(']'):
                    try:
                        parsed = json.loads(s)
                        if isinstance(parsed, list): return parsed
                    except: pass
                return None
            
            # 1. Try video_url
            parsed_video = parse_list(raw_input)
            if parsed_video:
                image_urls = parsed_video
            
            # 2. If empty, try thumbnail_url
            if not image_urls:
                raw_thumb = item.get('thumbnail_url')
                parsed_thumb = parse_list(raw_thumb)
                if parsed_thumb:
                    image_urls = parsed_thumb
                elif raw_thumb:
                    image_urls = [raw_thumb]
            
            # 3. If still empty, but video_url has a single string
            if not image_urls and raw_input:
                image_urls = [raw_input]

            local_paths = []
            os.makedirs('uploads_temp', exist_ok=True)
            
            # 2. Tải ảnh về
            for idx, url in enumerate(image_urls):
                drive_id = self.extract_drive_id(url)
                if drive_id:
                    path = os.path.join('uploads_temp', f"fb_img_{index}_{idx}.jpg")
                    if self.download_from_drive(drive_id, path):
                        local_paths.append(path)
                    else:
                        print(f"Failed to download image: {url}")
                else:
                    # Nếu là URL thường, giữ nguyên để Publisher xử lý
                    pass 

            try:
                if local_paths:
                    if len(local_paths) > 1 or post_type == "Album":
                        res = publisher.publish_album(image_paths=local_paths, message=message)
                    else:
                        # Ảnh đơn
                        res = publisher.publish_image(local_paths[0], caption=message) # Cần update publish_image hỗ trợ path
                        # Fallback nếu publish_image chưa hỗ trợ path -> dùng publish_album với 1 ảnh cũng OK
                        if not res.get("success"):
                             res = publisher.publish_album(image_paths=local_paths, message=message)

                elif image_urls and not local_paths:
                     # Trường hợp 100% là URL public (không phải Drive)
                     if len(image_urls) > 1:
                         res = publisher.publish_album(image_urls=image_urls, message=message)
                     else:
                         res = publisher.publish_image(image_urls[0], caption=message)
                else:
                    return {"success": False, "error": "Không tìm thấy ảnh hợp lệ để đăng."}
            finally:
                # Dọn dẹp
                for p in local_paths:
                    if os.path.exists(p):
                        os.remove(p)

        else:
            res = publisher.publish_status(message)

        if res["success"]:
            post_id = res["data"].get("id") or res["data"].get("video_id")
            
            history_data = {
                "Id_media_on_drive": item.get('media_drive_id'),
                "Name_video": item.get('video_name'),
                "Type_conten": post_type,
                "Page_name": page.get('name'),
                "Page_Id": page_id,
                "Access_token": token,
                "Facebook_Post_Id": post_id,
                "Thumbnail": item.get('thumbnail_url'),
                "Link_On_Platfrom": f"https://facebook.com/{post_id}",
                "Status": "SUCCESS"
            }
            
            self._log_history(history_data)
            
            item['status'] = 'PUBLISHED'
            item['fb_post_id'] = post_id
            SheetService.update_row(sheet_name, index, item)
            
            return {"success": True, "post_id": post_id}
        
        return res

    def _handle_youtube_publish(self, item, sheet_name, index):
        """Xử lý đăng bài lên YouTube và ghi lịch sử."""
        try:
            creds = get_creds()
            publisher = YoutubePublisher(creds)
            
            channel = item.get('channel', {})
            channel_id = channel.get('id')
            
            drive_url = item.get('video_url') or item.get('Link_on_drive')
            drive_id = self.extract_drive_id(drive_url)
            
            if not drive_id:
                return {"success": False, "error": "Không thể lấy ID file từ link Drive."}

            os.makedirs('uploads_temp', exist_ok=True)
            temp_path = os.path.join('uploads_temp', f"yt_upload_{index}.mp4")
            
            if not self.download_from_drive(drive_id, temp_path):
                return {"success": False, "error": "Lỗi khi tải video từ Drive về server."}

            res = publisher.upload_video(
                file_path=temp_path,
                title=item.get('video_name', 'No Title'),
                description=item.get('hook', '')
            )

            if os.path.exists(temp_path):
                os.remove(temp_path)

            if res["success"]:
                video_id = res["data"].get("id")
                
                thumb_url = item.get('thumbnail_url') 
                thumb_drive_id = self.extract_drive_id(thumb_url)
                if thumb_drive_id:
                    thumb_path = os.path.join('uploads_temp', f"yt_thumb_{index}.jpg")
                    if self.download_from_drive(thumb_drive_id, thumb_path):
                        publisher.set_thumbnail(video_id, thumb_path)
                        if os.path.exists(thumb_path):
                            os.remove(thumb_path)
                
                history_data = {
                    "Id_media_on_drive": item.get('media_drive_id') or drive_id,
                    "Name_video": item.get('video_name'),
                    "Type_conten": "Video",
                    "Channel_name": channel.get('name'),
                    "Channel_Id": channel_id,
                    "Gmail_channel": channel.get('gmail'),
                    "Youtube_Post_Id": video_id,
                    "Thumbnail": thumb_url,
                    "Link_On_Platfrom": f"https://youtube.com/watch?v={video_id}",
                    "Status": "SUCCESS"
                }
                
                self._log_history(history_data)
                
                item['status'] = 'SUCCESS' 
                item['yt_video_id'] = video_id 
                SheetService.update_row(sheet_name, index, item)
                
                return {"success": True, "post_id": video_id}
            return res
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _log_history(self, history_data):
        """Ghi nhật ký bài đăng thành công vào tab Published_History."""
        try:
            SheetService.append_row(self.HISTORY_SHEET, history_data)
        except Exception as e:
            print(f"Lỗi ghi lịch sử: {e}")
