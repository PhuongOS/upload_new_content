import sys
import os

# Link folder root
sys.path.append(os.getcwd())

from post-service.facebook_publisher import FacebookPublisher

def test_fb():
    # TEST DATA (Sửa lại thông tin thật để test)
    PAGE_ID = "YOUR_PAGE_ID"
    ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"
    
    publisher = FacebookPublisher(PAGE_ID, ACCESS_TOKEN)
    
    print("--- 1. Testing Status Publish ---")
    # res = publisher.publish_status("Hello from Antigravity Agent! This is a test post.")
    # print(res)
    
    print("\n--- 2. Testing Image Publish ---")
    # res = publisher.publish_image("https://via.placeholder.com/600", "Beautiful test image")
    # print(res)
    
    print("\n[NOTE] Hãy điền ID và Token thật vào script để thực hiện test API trực tiếp.")

if __name__ == "__main__":
    test_fb()
