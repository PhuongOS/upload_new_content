
import requests
from requests.auth import HTTPBasicAuth
import os

site_url = 'https://dientulamphat.com/'
wp_user = 'n8n_wordpress'
wp_app_pass = 'q3V5g95cUcyJrRTY513AmnM8'
test_image_url = 'https://placehold.co/600x400.png'

def test_upload():
    print(f"Testing upload to {site_url}...")
    
    # 1. Download image
    resp = requests.get(test_image_url)
    if resp.status_code != 200:
        print(f"Failed to download test image: {resp.status_code}")
        return
    
    image_data = resp.content
    content_type = resp.headers.get('Content-Type', 'image/png')
    
    # 2. Upload to Media Library
    media_endpoint = f"{site_url.rstrip('/')}/wp-json/wp/v2/media"
    headers = {
        'Content-Type': content_type,
        'Content-Disposition': 'attachment; filename=diagnostic_test.png',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    auth = HTTPBasicAuth(wp_user, wp_app_pass)
    
    # 1.5 Check /users/me
    print(f"Checking /users/me for authentication...")
    me_res = requests.get(f"{site_url.rstrip('/')}/wp-json/wp/v2/users/me", auth=auth, headers={'User-Agent': headers['User-Agent']})
    print(f"Me Status Code: {me_res.status_code}")
    print(f"Me Response: {me_res.text[:500]}")

    print(f"Endpoint: {media_endpoint}")
    print(f"Auth: {wp_user} / {wp_app_pass[:4]}****")
    
    try:
        res = requests.post(
            media_endpoint,
            data=image_data,
            headers=headers,
            auth=auth,
            timeout=30
        )
        print(f"Status Code: {res.status_code}")
        print(f"Response Body: {res.text[:500]}")
        
        if res.status_code in [200, 201]:
            print("SUCCESS! Media ID:", res.json().get('id'))
        else:
            print("FAILED.")
            
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    test_upload()
