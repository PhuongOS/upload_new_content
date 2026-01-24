import json
import datetime
import time
import os
from googleapiclient.discovery import build
from .facebook_publisher import FacebookPublisher
from .youtube_publisher import YoutubePublisher
from services.sheet_service import SheetService
from services.account_service import AccountService
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

    def _convert_to_unix(self, date_str):
        """Chuyển đổi chuỗi ngày tháng (DD/MM/YYYY HH:MM hoặc HH:MM:SS) sang Unix Timestamp."""
        if not date_str: return None
        for fmt in ["%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S"]:
            try:
                dt = datetime.datetime.strptime(date_str, fmt)
                return dt.timestamp()
            except ValueError:
                continue
        return None

    def get_media_type(self, drive_id):
        """Kiểm tra MimeType của file trên Drive để xác định là Video hay Image."""
        if not drive_id: return "Unknown"
        try:
            creds = get_creds()
            service = build('drive', 'v3', credentials=creds)
            file_meta = service.files().get(fileId=drive_id, fields='mimeType').execute()
            mime = file_meta.get('mimeType', '')
            if 'video' in mime:
                return "Video"
            elif 'image' in mime:
                return "Image"
            return "Other"
        except:
            return "Unknown"

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

    def _lookup_account_id_for_channel(self, channel_id, channel_name):
        """
        Tra cứu account_id từ Youtube_Config dựa trên channel_id hoặc channel_name.
        Trả về account_id nếu tìm thấy, None nếu không.
        """
        try:
            configs = SheetService.get_all_rows("Youtube_Config")
            for config in configs:
                # Match bằng channel_id hoặc channel_name
                if channel_id and config.get("channel_id") == channel_id:
                    account_id = config.get("account_id")
                    if account_id:
                        print(f"[PostManager] Found account_id by channel_id: {account_id}")
                        return account_id
                if channel_name and config.get("channel_name") == channel_name:
                    account_id = config.get("account_id")
                    if account_id:
                        print(f"[PostManager] Found account_id by channel_name: {account_id}")
                        return account_id
            print(f"[PostManager] ⚠️ No account_id found for channel: {channel_name} ({channel_id})")
            return None
        except Exception as e:
            print(f"[PostManager] Error looking up account_id: {e}")
            return None

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
            
            # Xử lý Hẹn giờ (Scheduling)
            scheduled_unix = None
            scheduled_iso = None
            calendar_str = item.get('calendar')
            if calendar_str:
                unix = self._convert_to_unix(calendar_str)
                if unix:
                    now = datetime.datetime.now().timestamp()
                    # Facebook yêu cầu > 10 phút (600s), Youtube yêu cầu tương lai
                    if unix > now + 600: 
                        scheduled_unix = unix
                        # Youtube cần ISO8601
                        scheduled_iso = datetime.datetime.fromtimestamp(unix).isoformat() + 'Z'
                        print(f"[PostManager] 🕒 Đã lên lịch đăng lúc: {scheduled_iso}")

            if "Facebook" in sheet_name:
                return self._handle_facebook_publish(item, sheet_name, index, task_id, scheduled_time=scheduled_unix)
            elif "Youtube" in sheet_name:
                return self._handle_youtube_publish(item, sheet_name, index, task_id, scheduled_time=scheduled_iso)
                
            return {"success": False, "error": "Nền tảng không được hỗ trợ."}
        except Exception as e:
            return {"success": False, "error": f"Lỗi hệ thống: {str(e)}"}

    def _handle_facebook_publish(self, item, sheet_name, index, task_id=None, scheduled_time=None):
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
        
        # Auto-detect logic: Nếu là Status nhưng có link, kiểm tra loại file
        if post_type in ["", "Status"] and (video_url or item.get('thumbnail_url')):
            # Lấy link tiềm năng
            check_url = video_url or item.get('thumbnail_url')
            # Thử trích xuất ID
            d_id = self.extract_drive_id(check_url)
            if d_id:
                m_type = self.get_media_type(d_id)
                if m_type == "Video":
                    post_type = "Video"
                    print(f"[PostManager] 💡 Auto-detected Post Type: Video")
                elif m_type == "Image":
                    # Check nếu là list ảnh (Album)
                    if isinstance(check_url, str) and check_url.strip().startswith('['):
                        post_type = "Album"
                        print(f"[PostManager] 💡 Auto-detected Post Type: Album")
                    else:
                        post_type = "Image"
                        print(f"[PostManager] 💡 Auto-detected Post Type: Image")

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
                    res = publisher.publish_video(video_path=temp_path, title=video_title, description=message, scheduled_time=scheduled_time)
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
                        res = publisher.publish_album(image_paths=local_paths, message=message, scheduled_time=scheduled_time)
                    else:
                        # Ảnh đơn
                        update_task_msg("Đang upload ảnh đơn lên Facebook...")
                        res = publisher.publish_image(local_paths[0], caption=message, scheduled_time=scheduled_time) 
                        # Fallback nếu publish_image chưa hỗ trợ path -> dùng publish_album với 1 ảnh cũng OK
                        if not res.get("success"):
                             res = publisher.publish_album(image_paths=local_paths, message=message, scheduled_time=scheduled_time)

                elif image_urls and not local_paths:
                     # Trường hợp 100% là URL public (không phải Drive)
                     if len(image_urls) > 1:
                         update_task_msg(f"Đang tạo Album với {len(image_urls)} URLs...")
                         res = publisher.publish_album(image_urls=image_urls, message=message, scheduled_time=scheduled_time)
                     else:
                         update_task_msg("Đang đăng ảnh từ URL...")
                         res = publisher.publish_image(image_urls[0], caption=message, scheduled_time=scheduled_time)
                else:
                    return {"success": False, "error": "Không tìm thấy ảnh hợp lệ để đăng."}
            finally:
                # Dọn dẹp
                for p in local_paths:
                    if os.path.exists(p):
                        os.remove(p)

        else:
            update_task_msg("Đang đăng Status (Text)...")
            res = publisher.publish_status(message, scheduled_time=scheduled_time)

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
                "Status": "SCHEDULED" if scheduled_time else "SUCCESS"
            }
            
            update_task_msg("Đang ghi lịch sử và cập nhật trạng thái...")
            self._log_history(history_data)
            
            item['status'] = 'SCHEDULED' if scheduled_time else 'PUBLISHED'
            item['fb_post_id'] = post_id
            SheetService.update_row(sheet_name, index, item)
            
            return {"success": True, "post_id": post_id}
        
        return res

    def _handle_youtube_publish(self, item, sheet_name, index, task_id=None, scheduled_time=None):
        """Xử lý đăng bài lên YouTube và ghi lịch sử với logging chi tiết."""
        def update_task_msg(msg):
            if task_id and task_id in tasks:
                tasks[task_id]["message"] = msg

        print(f"[PostManager] YT Publish - Dòng {index}")
        try:
            update_task_msg("Đang chuẩn bị xác thực YouTube...")
            
            # [MULTI-ACCOUNT] Lấy channel info
            channel = item.get('channel', {})
            channel_id = channel.get('id')
            channel_name = channel.get('name')
            
            # Lookup account_id từ Youtube_Config dựa trên channel_id hoặc channel_name
            account_id = self._lookup_account_id_for_channel(channel_id, channel_name)
            
            print(f"[PostManager] Channel: {channel_name} (ID: {channel_id}), Account ID: {account_id}")
            
            # Chọn credentials dựa trên account_id
            if account_id:
                print(f"[PostManager] Using account-specific credentials: {account_id}")
                try:
                    creds = AccountService.get_credentials(account_id)
                except Exception as e:
                    print(f"[PostManager] ⚠️ Account creds failed, fallback to default: {e}")
                    creds = get_creds()
            else:
                print(f"[PostManager] ⚠️ No account_id found, using default credentials")
                creds = get_creds()
            
            publisher = YoutubePublisher(creds)
            
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
                description=item.get('hook', ''),
                scheduled_time=scheduled_time
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
                    "Status": "SCHEDULED" if scheduled_time else "SUCCESS"
                }
                
                update_task_msg("Đang ghi lịch sử và cập nhật trạng thái...")
                self._log_history(history_data)
                
                item['status'] = 'SCHEDULED' if scheduled_time else 'PUBLISHED'
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

    def update_post_content(self, sheet_name, index, data, thumbnail_file=None):
        """
        Cập nhật nội dung bài viết (Title, Description, Privacy, Thumbnail) cho cả FB và YT.
        """
        try:
            rows = SheetService.get_all_rows(self.HISTORY_SHEET)
            if index >= len(rows): return {"success": False, "error": "Index out of range"}
            
            item = rows[index]
            
            title = data.get('title')
            description = data.get('description')
            privacy = data.get('privacy') # public, private, unlisted

            # Xử lý Thumbnail File (Lưu tạm)
            temp_thumb_path = None
            if thumbnail_file:
                filename = f"thumb_{index}_{int(time.time())}.jpg"
                temp_thumb_path = os.path.join(".", filename)
                thumbnail_file.save(temp_thumb_path)

            try:
                if item.get("Page_Id"): # Facebook
                    page_id = item.get("Page_Id")
                    token = item.get("Access_token")
                    post_id = item.get("Facebook_Post_Id")
                    
                    if not post_id: return {"success": False, "error": "No Post ID"}
                    
                    publisher = FacebookPublisher(page_id, token)
                    # FB Video dùng update_video_metadata
                    res = publisher.update_post_metadata(post_id, message=description)
                    
                    if item.get("Type_conten") == "Video":
                        publisher.update_video_metadata(post_id, title=title, description=description)
                        
                        # Update Thumbnail nếu có
                        if temp_thumb_path:
                            print(f"[Facebook] Updating thumbnail for {post_id}...")
                            thumb_res = publisher.set_video_thumbnail(post_id, temp_thumb_path)
                            if not thumb_res["success"]:
                                print(f"[Facebook] Thumbnail Warning: {thumb_res.get('error')}")
                    
                    if res["success"]:
                        if description: item["Name_video"] = description[:100]
                        SheetService.update_row(self.HISTORY_SHEET, index, item)
                    return res

                elif item.get("Channel_Id"): # YouTube
                    # Logic xác thực
                    creds = get_creds()
                    publisher = YoutubePublisher(creds)
                    video_id = item.get("Youtube_Post_Id")
                    
                    if not video_id: return {"success": False, "error": "No Video ID"}
                    
                    # 1. Update Metadata
                    res = publisher.update_metadata(video_id, title=title, description=description, privacy_status=privacy)
                    
                    # 2. Update Thumbnail (nếu có)
                    if temp_thumb_path:
                        print(f"[YouTube] Updating thumbnail for {video_id}...")
                        if not thumb_res["success"]:
                            print(f"[YouTube] Thumbnail Warning: {thumb_res.get('error')}")
                            # Không return error ngay nếu metadata success, chỉ cảnh báo?
                            # Hoặc gộp error
                    
                    if res["success"]:
                        if title: item["Name_video"] = title
                        SheetService.update_row(self.HISTORY_SHEET, index, item)
                    return res
                    
                return {"success": False, "error": "Unknown Platform"}

            finally:
                if temp_thumb_path and os.path.exists(temp_thumb_path):
                    os.remove(temp_thumb_path)
            
            return {"success": False, "error": "Platform ID not found in row"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def publish_now(self, index):
        """
        [NEW] Chuyển ngay bài viết đang SCHEDULED sang PUBLISHED (Public Now).
        Bỏ qua thời gian chờ.
        """
        try:
            print(f"[PostManager] Force Publishing row {index}...")
            rows = SheetService.get_all_rows(self.HISTORY_SHEET)
            if index >= len(rows): return {"success": False, "error": "Index out of range"}
            item = rows[index]
            
            # --- FACEBOOK ---
            if item.get("Page_Id"):
                page_id = item.get("Page_Id")
                token = item.get("Access_token")
                post_id = item.get("Facebook_Post_Id")
                post_type = item.get("Type_conten")
                
                if page_id and token and post_id:
                    publisher = FacebookPublisher(page_id, token)
                    res = None
                    
                    if post_type == "Video":
                        # FB Video: Update published=true
                        res = publisher._make_request(post_id, method="POST", data={"published": True})
                    else:
                        # FB Post/Image: Update is_published=true
                        res = publisher._make_request(post_id, method="POST", params={"is_published": "true"})
                        
                    if res["success"]:
                        item["Status"] = "SUCCESS"
                        SheetService.update_row(self.HISTORY_SHEET, index, item)
                    return res

            # --- YOUTUBE ---
            elif item.get("Channel_Id"):
                video_id = item.get("Youtube_Post_Id")
                if video_id:
                     creds = get_creds()
                     publisher = YoutubePublisher(creds)
                     # Update privacy to public (this clears publishAt)
                     res = publisher.update_metadata(video_id, privacy_status="public")
                     if res["success"]:
                         item["Status"] = "SUCCESS"
                         SheetService.update_row(self.HISTORY_SHEET, index, item)
                     return res

            return {"success": False, "error": "Platform or ID not found or not supported"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_published_post(self, sheet_name, index):
        """
        Xóa bài viết đã đăng (FB/YT) và xóa dòng trong History.
        """
        try:
            rows = SheetService.get_all_rows(self.HISTORY_SHEET)
            if index >= len(rows): return {"success": False, "error": "Index out of range"}
            item = rows[index]
            
            res = {"success": False}

            if item.get("Page_Id"): # Facebook
                page_id = item.get("Page_Id")
                token = item.get("Access_token")
                post_id = item.get("Facebook_Post_Id")
                
                # [FIX Logic] Nếu không có ID/Token (ví dụ lỗi khi tạo), cho phép xóa row
                if not post_id or not token:
                     SheetService.delete_row(self.HISTORY_SHEET, index)
                     return {"success": True, "message": "Deleted row (missing FB ID/Token)"}

                if post_id and token:
                    publisher = FacebookPublisher(page_id, token)
                    res = publisher.delete_node(post_id)

            elif item.get("Channel_Id"): # YouTube
                video_id = item.get("Youtube_Post_Id")
                
                # [FIX Logic] Nếu không có ID (ví dụ lỗi khi tạo), cho phép xóa row
                if not video_id:
                     SheetService.delete_row(self.HISTORY_SHEET, index)
                     return {"success": True, "message": "Deleted row (missing YT ID)"}

                if video_id:
                    creds = get_creds()
                    publisher = YoutubePublisher(creds)
                    res = publisher.delete_video(video_id)
            
            # Xóa trong Sheet bất kể API success hay fail (để dọn rác)
            # Hoặc chỉ xóa nếu success? User yêu cầu xóa bài post thành công
            # Tốt nhất là xóa dòng nếu API OK hoặc API báo không tìm thấy (đã xóa)
            # [FIX] Luôn xóa trong Sheet để tránh bị kẹt
            # Nếu API lỗi thì trả về success=True nhưng kèm message cảnh báo
            SheetService.delete_row(self.HISTORY_SHEET, index)
            
            if res.get("success"):
                 return {"success": True}
            
            # Nếu API fail, vẫn báo success để FE load lại, nhưng kèm warning
            return {"success": True, "warning": res.get("error", "Platform delete failed")}
            
            return res
        except Exception as e:
            return {"success": False, "error": str(e)}

    def sync_thumbnail(self, sheet_name, index):
        """
        Đồng bộ Thumbnail từ Platform về Sheet.
        """
        try:
            rows = SheetService.get_all_rows(self.HISTORY_SHEET)
            if index >= len(rows): return {"success": False, "error": "Index out of range"}
            item = rows[index]
            
            thumb_url = None

            if item.get("Page_Id"): # Facebook
                page_id = item.get("Page_Id")
                token = item.get("Access_token")
                post_id = item.get("Facebook_Post_Id")
                
                if post_id:
                    publisher = FacebookPublisher(page_id, token)
                    # Thử lấy video thumbnail trước
                    if item.get("Type_conten") == "Video":
                        res = publisher.get_video_thumbnail(post_id)
                        if res["success"]: thumb_url = res.get("thumbnail_url")
                    
                    # Nếu chưa có, lấy post picture (cho image post)
                    if not thumb_url:
                        res = publisher.get_post(post_id, fields="full_picture")
                        if res["success"]: thumb_url = res["data"].get("full_picture")

            elif item.get("Channel_Id"): # YouTube
                video_id = item.get("Youtube_Post_Id")
                if video_id:
                    creds = get_creds()
                    publisher = YoutubePublisher(creds)
                    res = publisher.get_video_details(video_id)
                    if res["success"]:
                        thumb_url = res.get("thumbnail_url")

            if thumb_url:
                item["Thumbnail"] = thumb_url
                SheetService.update_row(self.HISTORY_SHEET, index, item)
                return {"success": True, "thumbnail": thumb_url}
            
            return {"success": False, "error": "Thumbnail not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_post_details(self, sheet_name, index):
        """
        Lấy thông tin chi tiết hiện tại của bài viết từ Platform (Title, Description, Privacy).
        """
        try:
            rows = SheetService.get_all_rows(self.HISTORY_SHEET)
            if index >= len(rows): return {"success": False, "error": "Index out of range"}
            item = rows[index]
            
            data = {"title": "", "description": "", "privacy": ""}

            if item.get("Page_Id"): # Facebook
                page_id = item.get("Page_Id")
                token = item.get("Access_token")
                post_id = item.get("Facebook_Post_Id")
                
                if post_id and token:
                    publisher = FacebookPublisher(page_id, token)
                    # Xác định là Video hay Post thường
                    is_video = item.get("Type_conten") == "Video"
                    
                    if is_video:
                        # Lấy thông tin Video
                        res = publisher._make_request(post_id, method="GET", params={"fields": "title,description,published"})
                        if res["success"]:
                            d = res["data"]
                            data["title"] = d.get("title", "")
                            data["description"] = d.get("description", "")
                            # FB Video Privacy logic is complex, simplify for now
                            data["privacy"] = "public" # Placeholder
                            return {"success": True, "data": data}
                    else:
                        # Lấy thông tin Post
                        res = publisher.get_post(post_id, fields="message,privacy")
                        if res["success"]:
                            d = res["data"]
                            data["description"] = d.get("message", "") # Post uses message
                            # FB Privacy field structure: {"value": "EVERYONE", ...}
                            p_val = d.get("privacy", {}).get("value", "")
                            data["privacy"] = "public" if p_val == "EVERYONE" else "private"
                            return {"success": True, "data": data}

            elif item.get("Channel_Id"): # YouTube
                video_id = item.get("Youtube_Post_Id")
                if video_id:
                    creds = get_creds()
                    publisher = YoutubePublisher(creds)
                    res = publisher.get_video_details(video_id)
                    if res["success"]:
                        data["title"] = res.get("title", "")
                        data["description"] = res.get("description", "")
                        data["privacy"] = res.get("privacy", "")
                        return {"success": True, "data": data}

            return {"success": False, "error": "Platform or ID not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _log_history(self, history_data):
        """Ghi nhật ký bài đăng thành công vào tab Published_History."""
        try:
            SheetService.append_row(self.HISTORY_SHEET, history_data)
        except Exception as e:
            print(f"[PostManager] ❌ Lỗi khi ghi lịch sử: {e}")

    def check_status_recur(self):
        """
        [Background Job] Kiểm tra trạng thái các bài đang SCHEDULED.
        Nếu đã public thì cập nhật lại Status trong Sheet.
        
        Logic Check:
        - FB Video: published == True
        - FB Image/Status: is_hidden == False
        - FB Scheduled Object: is_published == True
        - FB Reels: has permalink_url
        - YT: status.privacyStatus == 'public'
        """
        try:
            print("[Scheduler] Đang kiểm tra trạng thái bài đăng...")
            start_time = time.time()
            rows = SheetService.get_all_rows(self.HISTORY_SHEET)
            updates_count = 0
            
            for index, item in enumerate(rows):
                if item.get("Status") != "SCHEDULED":
                    continue
                
                # --- FACEBOOK CHECK ---
                if item.get("Page_Id"):
                    page_id = item.get("Page_Id")
                    token = item.get("Access_token")
                    post_id = item.get("Facebook_Post_Id")
                    post_type = item.get("Type_conten", "Status")
                    
                    if page_id and token and post_id:
                        publisher = FacebookPublisher(page_id, token)
                        is_live = False
                        
                        # 1. Check Video
                        if post_type == "Video":
                            res = publisher._make_request(post_id, method="GET", params={"fields": "published"})
                            if res["success"] and res["data"].get("published") is True:
                                is_live = True
                                
                        # 2. Check Reels
                        elif post_type == "Reels":
                            # Reels thường ko có published/is_hidden, check permalink
                            res = publisher._make_request(post_id, method="GET", params={"fields": "permalink_url"})
                            if res["success"] and res["data"].get("permalink_url"):
                                is_live = True
                                
                        # 3. Check Scheduled Object (đã tạo ID nhưng chưa tới giờ)
                        # Trước tiên thử check xem nó có còn là scheduled object không
                        res_sched = publisher._make_request(post_id, method="GET", params={"fields": "is_published"})
                        if res_sched["success"]:
                            if res_sched["data"].get("is_published") is True:
                                is_live = True
                        
                        # 4. Fallback cho Image/Status (Feed Post)
                        # Nếu check is_published ở trên trả về True rồi thì thôi. 
                        # Nếu chưa, và là Image/Status, check is_hidden
                        if not is_live and post_type in ["Image", "Album", "Status"]:
                             res_hidden = publisher._make_request(post_id, method="GET", params={"fields": "is_hidden"})
                             if res_hidden["success"]:
                                 # is_hidden=False nghĩa là đang hiện -> Public
                                 if res_hidden["data"].get("is_hidden") is False:
                                     is_live = True

                        if is_live:
                            print(f"[Scheduler] ✅ FB Post {post_id} đã Pubic. Cập nhật Sheet...")
                            item["Status"] = "SUCCESS"
                            SheetService.update_row(self.HISTORY_SHEET, index, item)
                            updates_count += 1

                # --- YOUTUBE CHECK ---
                elif item.get("Channel_Id"):
                    video_id = item.get("Youtube_Post_Id")
                    if video_id:
                        try:
                            # Tối ưu: Nếu chưa có service, function này sẽ tự gọi get_creds
                            creds = get_creds()
                            if creds:
                                yt_pub = YoutubePublisher(creds)
                                res = yt_pub.get_video_details(video_id) # Hàm này trả về title, desc, privacy
                                if res.get("success") and res.get("privacy") == "public":
                                    print(f"[Scheduler] ✅ YT Video {video_id} đã Public. Cập nhật Sheet...")
                                    item["Status"] = "SUCCESS"
                                    SheetService.update_row(self.HISTORY_SHEET, index, item)
                                    updates_count += 1
                        except Exception as ex:
                            print(f"[Scheduler] Lỗi check YT {video_id}: {ex}")

            if updates_count > 0:
                print(f"[Scheduler] Hoàn tất. Đã cập nhật {updates_count} bài.")
            else:
                print(f"[Scheduler] Không có bài nào chuyển sang Public.")
                
        except Exception as e:
            print(f"[Scheduler] ❌ Lỗi quá trình kiểm tra: {e}")
