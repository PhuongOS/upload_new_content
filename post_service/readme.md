❌ GET /{post_id}?fields=is_published KHÔNG đúng trong mọi trường hợp

is_published không áp dụng chung cho tất cả post. Tùy loại object mà field kiểm tra public khác nhau.

✅ CÁCH ĐÚNG ĐỂ CHECK “ĐÃ PUBLIC CHƯA”
1️⃣ Post thường (Page feed post: ảnh, link, text)

👉 KHÔNG có is_published

GET https://graph.facebook.com/v19.0/{POST_ID}
?fields=is_hidden


Diễn giải

is_hidden = false  → ĐANG PUBLIC
is_hidden = true   → BỊ ẨN (chỉ admin thấy)


📌 Facebook không có field is_published cho feed post

2️⃣ Video post (Page video)

👉 DÙNG published

GET https://graph.facebook.com/v19.0/{VIDEO_ID}
?fields=published

published = true  → PUBLIC
published = false → UNPUBLISHED


✔️ Đây là field ĐÚNG cho video

3️⃣ Reels

👉 KHÔNG có API check public chính xác

Không có published

Không có is_published

Không có is_hidden

➡️ Chỉ có thể suy đoán bằng:

GET /{REEL_ID}?fields=permalink_url


Có permalink → gần như chắc là public

Không có → chưa public / restricted

⚠️ Không đảm bảo 100%

4️⃣ Scheduled post (đã tạo nhưng chưa tới giờ)

👉 DÙNG is_published (CHỈ TRƯỜNG HỢP NÀY)

GET https://graph.facebook.com/v19.0/{POST_ID}
?fields=is_published,scheduled_publish_time

is_published = false + scheduled_publish_time tồn tại
→ bài hẹn giờ


✔️ Field này chỉ dùng cho scheduled post

📌 TÓM TẮT CHUẨN
Feed post (ảnh / link / text) → is_hidden
Video post                    → published
Scheduled post                → is_published
Reels                          → KHÔNG API chính xác
