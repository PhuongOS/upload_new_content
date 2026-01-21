import json
import datetime
import os
from googleapiclient.discovery import build
from .facebook_publisher import FacebookPublisher
from .youtube_publisher import YoutubePublisher
from services.sheet_service import SheetService
from logic import get_creds, tasks

class PostManager:
    """
    Quản lý luồng công việc đăng bài: 
    1. Lấy dữ liệu từ Sheet (Facebook_db hoặc Youtube_db)
    2. Gọi Publisher tương ứng
    3. Lưu kết quả vào tab Published_History
    """
    
    HISTORY_SHEET = "Published_History"

    def extract_drive_id(self, url):
        """Trích xuất ID file từ link Google Drive một cách mạnh mẽ."""
        if not url: return None
        
        # Xử lý trường hợp URL là chuỗi JSON list (VD: ["link1", "link2"])
        if isinstance(url, str) and url.strip().startswith('[') and url.strip().endswith(']'):
            try:
                urls = json.loads(url)
                if urls and isinstance(urls, list):
                    url = urls[0]
            except Exception:
                pass

        import re
        # Các pattern phổ biến cho Google Drive IDs
        patterns = [
            r'[-\w]{25,}',                  # 1. Chuỗi ID dài thông thường (chuẩn Drive)
            r'd/([-\w]{25,})',              # 2. Định dạng /d/ID/...
            r'id=([-\w]{25,})',             # 3. Định dạng id=ID
            r'folders/([-\w]{25,})'         # 4. Định dạng folders/ID
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                extracted_id = match.group(1) if '(' in pattern else match.group(0)
                # Đảm bảo không lấy nhầm các tham số URL dài khác
                if len(extracted_id) >= 25 and len(extracted_id) <= 50:
                    return extracted_id
        return None

    def download_from_drive(self, drive_id, output_path):
        """Tải file từ Drive về máy chủ với logging chi tiết."""
        from googleapiclient.http import MediaIoBaseDownload
        import io
        print(f"[PostManager] Đang tải file ID: {drive_id} về {output_path}...")
        try:
            creds = get_creds()
            service = build('drive', 'v3', credentials=creds)
            
            # Kiểm tra file có tồn tại và size trước
            file_meta = service.files().get(fileId=drive_id, fields='size,name').execute()
            file_size = int(file_meta.get('size', 0))
            print(f"[PostManager] Tên file: {file_meta.get('name')}, Kích thước: {file_size} bytes")

            request = service.files().get_media(fileId=drive_id)
            fh = io.FileIO(output_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                if status:
                    print(f"[PostManager] Tiến độ tải: {int(status.progress() * 100)}%")
            
            fh.close()
            
            # Kiểm tra sau khi tải
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print(f"[PostManager] Tải hoàn tất. File size thực tế: {os.path.getsize(output_path)}")
                return True
            else:
                print(f"[PostManager] ❌ Lỗi: File tải về trống hoặc không tồn tại.")
                return False
        except Exception as e:
            print(f"[PostManager] ❌ Lỗi tải Drive {drive_id}: {str(e)}")
            return False

    def publish_item(self, sheet_name, index, task_id=None):
        """
        Thực hiện đăng bài cho một dòng cụ thể trong Sheet.
        """
        print(f"\n[PostManager] === BẮT ĐẦU PUBLISH: {sheet_name} (Dòng {index}) ===")
        
        def update_task_msg(msg):
            if task_id and task_id in tasks:
                tasks[task_id]["message"] = msg
                print(f"[PostManager] Task Update: {msg}")

        try:
            rows = SheetService.get_all_rows(sheet_name)
            if not rows or index >= len(rows):
                err = f"Không tìm thấy dữ liệu tại dòng {index} trong {sheet_name}."
                print(f"[PostManager] ❌ {err}")
                return {"success": False, "error": err}
            
            item = rows[index]
            print(f"[PostManager] Dữ liệu dòng: {json.dumps(item)[:200]}...")
            
            if "Facebook" in sheet_name:
                return self._handle_facebook_publish(item, sheet_name, index, task_id)
            elif "Youtube" in sheet_name:
                return self._handle_youtube_publish(item, sheet_name, index, task_id)
                
            return {"success": False, "error": "Nền tảng không được hỗ trợ."}
        except Exception as e:
            return {"success": False, "error": f"Lỗi hệ thống: {str(e)}"}

    def _handle_facebook_publish(self, item, sheet_name, index, task_id=None):
        """Xử lý đăng bài lên Facebook và ghi lịch sử với logging chi tiết."""
        def update_task_msg(msg):
            if task_id and task_id in tasks:
                tasks[task_id]["message"] = msg

        page = item.get('page', {})
        page_id = page.get('id')
        token = page.get('access_token')
        
        message = item.get('hook', '')
        video_title = item.get('video_name', '')
            
        video_url = item.get('video_url')
        post_type = item.get('post_type', 'Status')
        
        print(f"[PostManager] FB Publish - Page ID: {page_id}, Type: {post_type}")
        
        if not page_id or not token:
            err = "Thiếu Facebook Page ID hoặc Access Token."
            print(f"[PostManager] ❌ {err}")
            return {"success": False, "error": err}

        publisher = FacebookPublisher(page_id, token)
        
        # Flow xử lý Video/Reels: Tải về -> Upload
        if post_type in ["Video", "Reels"] and video_url:
            update_task_msg(f"Đang chuẩn bị tải {post_type}...")
            drive_id = self.extract_drive_id(video_url)
            if not drive_id:
                return {"success": False, "error": "Không lấy được ID video từ link Drive."}
            
            os.makedirs('uploads_temp', exist_ok=True)
            temp_path = os.path.join('uploads_temp', f"fb_{post_type.lower()}_{index}.mp4")
            
            if not self.download_from_drive(drive_id, temp_path):
                return {"success": False, "error": f"Lỗi tải video ID {drive_id} từ Drive."}
                
            try:
                if post_type == "Reels":
                    update_task_msg("Đang upload Reels lên Facebook...")
                    res = publisher.publish_reel(video_path=temp_path, description=message)
                else:
                    update_task_msg("Đang upload Video lên Facebook...")
                    res = publisher.publish_video(video_path=temp_path, title=video_title, description=message)
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        elif post_type in ["Image", "Album"]:
            # Xử lý Album (Nhiều ảnh) hoặc Ảnh đơn
            update_task_msg(f"Đang chuẩn bị tải ảnh cho {post_type}...")
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
                update_task_msg(f"Đang tải ảnh {idx+1}/{len(image_urls)}...")
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
                        update_task_msg(f"Đang tạo Album với {len(local_paths)} ảnh...")
                        res = publisher.publish_album(image_paths=local_paths, message=message)
                    else:
                        # Ảnh đơn
                        update_task_msg("Đang upload ảnh đơn lên Facebook...")
                        res = publisher.publish_image(local_paths[0], caption=message) # Cần update publish_image hỗ trợ path
                        # Fallback nếu publish_image chưa hỗ trợ path -> dùng publish_album với 1 ảnh cũng OK
                        if not res.get("success"):
                             res = publisher.publish_album(image_paths=local_paths, message=message)

                elif image_urls and not local_paths:
                     # Trường hợp 100% là URL public (không phải Drive)
                     if len(image_urls) > 1:
                         update_task_msg(f"Đang tạo Album với {len(image_urls)} URLs...")
                         res = publisher.publish_album(image_urls=image_urls, message=message)
                     else:
                         update_task_msg("Đang đăng ảnh từ URL...")
                         res = publisher.publish_image(image_urls[0], caption=message)
                else:
                    return {"success": False, "error": "Không tìm thấy ảnh hợp lệ để đăng."}
            finally:
                # Dọn dẹp
                for p in local_paths:
                    if os.path.exists(p):
                        os.remove(p)

        else:
            update_task_msg("Đang đăng Status (Text)...")
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
            
            update_task_msg("Đang ghi lịch sử và cập nhật trạng thái...")
            self._log_history(history_data)
            
            item['status'] = 'PUBLISHED'
            item['fb_post_id'] = post_id
            SheetService.update_row(sheet_name, index, item)
            
            return {"success": True, "post_id": post_id}
        
        return res

    def _handle_youtube_publish(self, item, sheet_name, index, task_id=None):
        """Xử lý đăng bài lên YouTube và ghi lịch sử với logging chi tiết."""
        def update_task_msg(msg):
            if task_id and task_id in tasks:
                tasks[task_id]["message"] = msg

        print(f"[PostManager] YT Publish - Dòng {index}")
        try:
            update_task_msg("Đang chuẩn bị xác thực YouTube...")
            creds = get_creds()
            publisher = YoutubePublisher(creds)
            
            channel = item.get('channel', {})
            channel_id = channel.get('id')
            
            drive_url = item.get('video_url') or item.get('Link_on_drive')
            drive_id = self.extract_drive_id(drive_url)
            
            print(f"[PostManager] YT Publish - Channel ID: {channel_id}, Drive ID: {drive_id}")
            
            if not drive_id:
                err = "Không thể lấy ID file từ link Drive."
                print(f"[PostManager] ❌ {err}")
                return {"success": False, "error": err}

            os.makedirs('uploads_temp', exist_ok=True)
            temp_path = os.path.join('uploads_temp', f"yt_upload_{index}.mp4")
            
            update_task_msg("Đang tải video từ Drive...")
            if not self.download_from_drive(drive_id, temp_path):
                err = "Lỗi khi tải video từ Drive về server."
                print(f"[PostManager] ❌ {err}")
                return {"success": False, "error": err}

            update_task_msg("Đang upload video lên YouTube...")
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
                    update_task_msg("Đang upload thumbnail lên YouTube...")
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
                
                update_task_msg("Đang ghi lịch sử và cập nhật trạng thái...")
                self._log_history(history_data)
                
                item['status'] = 'PUBLISHED' 
                item['yt_video_id'] = video_id 
                SheetService.update_row(sheet_name, index, item)
                
                return {"success": True, "post_id": video_id}
            return res
        except Exception as e:
            return {"success": False, "error": str(e)}

    def sync_facebook_post_info(self, index):
        """
        Lấy thông tin mới nhất từ Facebook và cập nhật vào Published_History.
        """
        try:
            rows = SheetService.get_all_rows(self.HISTORY_SHEET)
            if not rows or index >= len(rows):
                return {"success": False, "error": "Không tìm thấy dòng lịch sử."}
            
            item = rows[index]
            post_id = item.get("Facebook_Post_Id")
            page_id = item.get("Page_Id")
            token = item.get("Access_token")

            if not post_id or not token:
                return {"success": False, "error": "Thiếu Post ID hoặc Access Token."}

            publisher = FacebookPublisher(page_id, token)
            res = publisher.get_post(post_id)
            
            if res["success"]:
                data = res["data"]
                # Cập nhật Thumbnail
                thumb = data.get("full_picture")
                if not thumb and "attachments" in data:
                    attachments = data["attachments"].get("data", [])
                    if attachments:
                        thumb = attachments[0].get("media", {}).get("image", {}).get("src")
                
                if thumb:
                    item["Thumbnail"] = thumb
                
                # Cập nhật Permalink nếu có
                if data.get("permalink_url"):
                    item["Link_On_Platfrom"] = data.get("permalink_url")
                
                # Cập nhật message (nếu cần đồng bộ text)
                if data.get("message"):
                    item["Name_video"] = data.get("message")[:100] # Tạm lấy message làm title nếu trống
                
                SheetService.update_row(self.HISTORY_SHEET, index, item)
                return {"success": True, "data": item}
            
            return res
        except Exception as e:
            return {"success": False, "error": str(e)}

    def edit_facebook_post(self, index, new_message):
        """
        Chỉnh sửa nội dung bài viết đã đăng trên Facebook.
        """
        try:
            rows = SheetService.get_all_rows(self.HISTORY_SHEET)
            if not rows or index >= len(rows):
                return {"success": False, "error": "Không tìm thấy dòng lịch sử."}
            
            item = rows[index]
            post_id = item.get("Facebook_Post_Id")
            page_id = item.get("Page_Id")
            token = item.get("Access_token")

            if not post_id or not token:
                return {"success": False, "error": "Thiếu Post ID hoặc Access Token."}

            publisher = FacebookPublisher(page_id, token)
            res = publisher.update_post_metadata(post_id, message=new_message)
            
            if res["success"]:
                # Cập nhật lại trong Sheet
                item["Name_video"] = new_message[:100] # Update preview name
                SheetService.update_row(self.HISTORY_SHEET, index, item)
                return {"success": True}
            
            return res
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_facebook_post(self, index):
        """
        Xóa bài viết trên Facebook và xóa khỏi Published_History.
        """
        try:
            rows = SheetService.get_all_rows(self.HISTORY_SHEET)
            if not rows or index >= len(rows):
                return {"success": False, "error": "Không tìm thấy dòng lịch sử."}
            
            item = rows[index]
            post_id = item.get("Facebook_Post_Id")
            page_id = item.get("Page_Id")
            token = item.get("Access_token")

            if not post_id or not token:
                # Nếu không có ID nhưng vẫn muốn xóa dòng trong Sheet
                SheetService.delete_row(self.HISTORY_SHEET, index)
                return {"success": True, "message": "Đã xóa dòng trong Sheet (không tìm thấy ID FB)."}

            publisher = FacebookPublisher(page_id, token)
            res = publisher.delete_post(post_id)
            
            if res["success"] or "error" in res:
                # Dù lỗi FB (VD bài đã bị xóa thủ công) thì vẫn ưu tiên xóa dòng trong Sheet
                SheetService.delete_row(self.HISTORY_SHEET, index)
                return {"success": True}
            
            return res
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _log_history(self, history_data):
        """Ghi nhật ký bài đăng thành công vào tab Published_History."""
        try:
            SheetService.append_row(self.HISTORY_SHEET, history_data)
        except Exception as e:
            print(f"Lỗi ghi lịch sử: {e}")
