========================================
YOUTUBE CONTENT MANAGEMENT – API GUIDE
YouTube Data API v3
========================================

I. XÁC THỰC (BẮT BUỘC)
----------------------------------------
OAuth 2.0
Scope:
https://www.googleapis.com/auth/youtube
hoặc
https://www.googleapis.com/auth/youtube.force-ssl

Access Token gắn vào Header:
Authorization: Bearer ACCESS_TOKEN


II. LẤY THÔNG TIN VIDEO
----------------------------------------

1. GET MÔ TẢ, TIÊU ĐỀ, TRẠNG THÁI, THUMBNAIL
----------------------------------------
GET https://www.googleapis.com/youtube/v3/videos
Params:
- part=snippet,status
- id=VIDEO_ID

Response quan trọng:
snippet.title
snippet.description
snippet.thumbnails.default|medium|high|maxres
status.privacyStatus (public | unlisted | private)
status.publishAt


III. SỬA TIÊU ĐỀ + MÔ TẢ
----------------------------------------

PUT https://www.googleapis.com/youtube/v3/videos
Params:
- part=snippet

Body (JSON):
{
  "id": "VIDEO_ID",
  "snippet": {
    "title": "Tiêu đề mới",
    "description": "Mô tả mới",
    "categoryId": "22"
  }
}

⚠️ Lưu ý:
- BẮT BUỘC gửi lại đầy đủ field trong snippet
- Nếu thiếu field → bị reset


IV. GET THUMBNAIL
----------------------------------------

YouTube KHÔNG có API download thumbnail riêng
→ Lấy từ snippet.thumbnails

Ví dụ:
https://i.ytimg.com/vi/VIDEO_ID/maxresdefault.jpg


V. SỬA / UPLOAD THUMBNAIL
----------------------------------------

POST https://www.googleapis.com/upload/youtube/v3/thumbnails/set
Params:
- videoId=VIDEO_ID
- uploadType=media

Header:
Content-Type: image/jpeg | image/png

Body:
(binary image)

⚠️ Điều kiện:
- Video phải xác minh
- Channel không bị giới hạn


VI. GET TRẠNG THÁI ĐĂNG VIDEO
----------------------------------------

GET https://www.googleapis.com/youtube/v3/videos
Params:
- part=status
- id=VIDEO_ID

status.privacyStatus:
- public
- unlisted
- private


VII. SỬA TRẠNG THÁI ĐĂNG (PUBLIC / PRIVATE / HẸN GIỜ)
----------------------------------------

PUT https://www.googleapis.com/youtube/v3/videos
Params:
- part=status

Body:
{
  "id": "VIDEO_ID",
  "status": {
    "privacyStatus": "public",
    "publishAt": "2026-01-21T10:00:00Z"
  }
}

Ví dụ:
- Public ngay → privacyStatus=public
- Hẹn giờ → publishAt + privacyStatus=private
- Ẩn link → unlisted


VIII. ĐĂNG VIDEO MỚI
----------------------------------------

POST https://www.googleapis.com/upload/youtube/v3/videos
Params:
- part=snippet,status
- uploadType=resumable | multipart

Body (multipart):
snippet:
  title
  description
  tags
status:
  privacyStatus

⚠️ Video upload nên dùng resumable để tránh lỗi mạng


IX. GET TRẠNG THÁI XỬ LÝ VIDEO (PROCESSING)
----------------------------------------

GET https://www.googleapis.com/youtube/v3/videos
Params:
- part=processingDetails,status
- id=VIDEO_ID

processingDetails.processingStatus:
- processing
- succeeded
- failed


X. NHỮNG LỖI THƯỜNG GẶP
----------------------------------------
- 403 → thiếu scope
- 400 → thiếu field trong snippet/status
- 401 → token hết hạn
- Thumbnail upload fail → video chưa public / channel bị giới hạn


XI. TÀI LIỆU CHÍNH THỨC
----------------------------------------
YouTube Data API v3
========================================
