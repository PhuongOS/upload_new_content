import requests
import json
import time

class FacebookPublisher:
    """
    Service xử lý đăng bài và quản lý nội dung trên Facebook Page via Graph API.
    Hỗ trợ: Đăng bài (Text/Image/Video/Reels), Xóa bài, Sửa bài và Hẹn giờ.
    """
    
    BASE_URL = "https://graph.facebook.com/v21.0"

    def __init__(self, page_id, access_token):
        self.page_id = page_id
        self.access_token = access_token

    def _make_request(self, endpoint, method="POST", params=None, data=None, files=None):
        """Hàm helper để thực hiện gọi API Facebook với xử lý lỗi tập trung."""
        url = f"{self.BASE_URL}/{endpoint}"
        query_params = {"access_token": self.access_token}
        if params:
            query_params.update(params)
            
        try:
            if method == "POST":
                response = requests.post(url, params=query_params, data=data, files=files)
            elif method == "GET":
                response = requests.get(url, params=query_params)
            elif method == "DELETE":
                response = requests.delete(url, params=query_params)
            
            res_json = response.json()
            if not response.ok:
                error_msg = res_json.get("error", {}).get("message", "Unknown Facebook Error")
                print(f"Facebook API Error: {response.status_code} - {error_msg}")
                return {"success": False, "error": error_msg, "status_code": response.status_code}
            
            return {"success": True, "data": res_json}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def publish_status(self, message, scheduled_time=None):
        """
        Đăng bài viết dạng Text (Status).
        :param scheduled_time: Unix timestamp (phải cách hiện tại > 10p và < 6 tháng)
        """
        endpoint = f"{self.page_id}/feed"
        payload = {"message": message}
        
        if scheduled_time:
            payload["published"] = "false"
            payload["scheduled_publish_time"] = scheduled_time
            
        return self._make_request(endpoint, data=payload)

    def publish_image(self, image_url=None, image_path=None, caption="", scheduled_time=None):
        """
        Đăng bài viết kèm ảnh.
        Hỗ trợ file local (image_path) hoặc URL (image_url).
        """
        endpoint = f"{self.page_id}/photos"
        payload = {"caption": caption}
        
        if scheduled_time:
            payload["published"] = "false"
            payload["scheduled_publish_time"] = scheduled_time
            
        if image_path:
            try:
                files = {'source': open(image_path, 'rb')}
                return self._make_request(endpoint, data=payload, files=files)
            except Exception as e:
                return {"success": False, "error": f"Lỗi đọc file ảnh: {str(e)}"}
        elif image_url:
            payload["url"] = image_url
            return self._make_request(endpoint, data=payload)
        else:
            return {"success": False, "error": "Thiếu source ảnh (path hoặc url)"}

    def publish_video(self, video_path=None, video_url=None, title="", description="", scheduled_time=None):
        """
        Đăng Video lên Fanpage.
        Ưu tiên upload file local nếu có video_path.
        """
        endpoint = f"{self.page_id}/videos"
        payload = {
            "title": title,
            "description": description
        }
        
        if scheduled_time:
            payload["scheduled_publish_time"] = scheduled_time
            
        if video_path:
            # Upload file local
            try:
                files = {
                    'source': open(video_path, 'rb')
                }
                return self._make_request(endpoint, data=payload, files=files)
            except Exception as e:
                return {"success": False, "error": f"Lỗi đọc file video: {str(e)}"}
        elif video_url:
            # Upload qua URL
            payload["file_url"] = video_url
            return self._make_request(endpoint, data=payload)
        else:
            return {"success": False, "error": "Cần cung cấp video_path hoặc video_url"}

    def publish_reel(self, video_path=None, video_url=None, description=""):
        """
        Đăng Reels lên Page (Sử dụng API Reels chuyên dụng).
        Hỗ trợ cả file local và URL.
        """
        # 1. Khởi tạo upload Reel (Sửa endpoint từ reels_videos sang video_reels)
        init_res = self._make_request(f"{self.page_id}/video_reels", data={"upload_phase": "start"})
        if not init_res["success"]: return init_res
        
        video_id = init_res["data"]["video_id"]
        
        # 2. Upload video
        if video_path:
            try:
                with open(video_path, 'rb') as f:
                    file_content = f.read()
                
                # Upload binary tới rupload
                upload_res = requests.post(
                    f"https://rupload.facebook.com/video-upload/v21.0/{video_id}",
                    headers={
                        "Authorization": f"OAuth {self.access_token}", 
                        "offset": "0", 
                        "file_size": str(len(file_content))
                    },
                    data=file_content
                )
                if not upload_res.ok:
                    return {"success": False, "error": f"Reel Upload Failed: {upload_res.text}"}
                    
            except Exception as e:
                 return {"success": False, "error": str(e)}

        elif video_url:
             # Upload qua URL (cũ)
             pass 
        else:
            return {"success": False, "error": "Thiếu source video"}

        # 3. Finish Publish
        finish_data = {
            "upload_phase": "finish",
            "video_state": "PUBLISHED",
            "description": description,
        }
        
        if video_url and not video_path:
             finish_data["file_url"] = video_url
             
        finish_res = self._make_request(f"{video_id}", data=finish_data)
        return finish_res

    def publish_album(self, image_paths=None, image_urls=None, message="", scheduled_time=None):
        """
        Đăng nhiều ảnh (Album) lên Page.
        Quy trình:
        1. Upload từng ảnh với published=false -> Lấy Photo ID.
        2. Đăng Feed với attached_media = [list_ids].
        """
        photo_ids = []
        errors = []

        # 1. Upload ảnh từ Local
        if image_paths:
            for path in image_paths:
                try:
                    endpoint = f"{self.page_id}/photos"
                    payload = {"published": "false"}
                    files = {'source': open(path, 'rb')}
                    
                    res = self._make_request(endpoint, data=payload, files=files)
                    if res.get("success"):
                        photo_ids.append({"media_fbid": res["data"]["id"]})
                    else:
                        errors.append(f"Failed path {path}: {res.get('error')}")
                    
                    # Delay 1.5s tránh rate limit
                    time.sleep(1.5)
                except Exception as e:
                    errors.append(f"Error path {path}: {str(e)}")

        # 2. Upload ảnh từ URL (nếu có)
        if image_urls:
             for url in image_urls:
                endpoint = f"{self.page_id}/photos"
                payload = {"published": "false", "url": url}
                res = self._make_request(endpoint, data=payload)
                if res.get("success"):
                     photo_ids.append({"media_fbid": res["data"]["id"]})
                else:
                     errors.append(f"Failed url {url}: {res.get('error')}")
                
                # Delay 1.5s
                time.sleep(1.5)

        if not photo_ids:
            return {"success": False, "error": f"Không thể upload ảnh nào. Errors: {errors}"}

        # 3. Đăng bài Feed gắn kèm ảnh
        endpoint = f"{self.page_id}/feed"
        payload = {
            "message": message,
            "attached_media": json.dumps(photo_ids)
        }
        
        if scheduled_time:
             payload["published"] = "false"
             payload["scheduled_publish_time"] = scheduled_time

        return self._make_request(endpoint, data=payload)

    def get_post(self, post_id, fields="message,full_picture,attachments,permalink_url,created_time"):
        """
        Lấy thông tin chi tiết của một bài viết.
        """
        params = {"fields": fields}
        return self._make_request(post_id, method="GET", params=params)

    def update_post_metadata(self, post_id, message=None):
        """
        Cập nhật mô tả (caption/message) của bài viết đã đăng.
        """
        payload = {}
        if message: payload["message"] = message
        
        return self._make_request(post_id, data=payload)

    def delete_post(self, post_id):
        """Xóa bài viết trên Facebook."""
        return self._make_request(post_id, method="DELETE")
