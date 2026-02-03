#!/usr/bin/env python3
"""
Test script to simulate saveAndPublishHaravan with local images (Base64).
Does NOT rely on browser. Calls the API endpoint directly.
"""
import sys
import requests
import json
import base64
import os

# Configuration
BASE_URL = "http://localhost:3000"

def get_base64_image():
    """Create a simple 1x1 pixel red dot base64 image for testing."""
    # Red dot 1x1 transparent png
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

def test_haravan_publish_with_local_images():
    print("=" * 60)
    print("TEST: Publish to Haravan with Local Images (Base64)")
    print("=" * 60)

    # 1. Create a dummy item in Haravan_db sheet (Optional but good for real flow)
    # For now we will assume row 0 exists and is valid or use a mock.
    # Actually, let's just use index 0. Ensure server is running.
    
    # Payload simulating what script.js sends
    payload = {
        "sheet_name": "Haravan_db",
        "index": 0, # Assuming index 0 is safe to overwrite/test on
        "local_images": [
            {
                "filename": "test_image_1.png",
                "base64": get_base64_image()
            },
           {
                "filename": "test_image_2.png",
                "base64": get_base64_image()
            }
        ]
    }
    
    print(f"[INFO] Sending payload to {BASE_URL}/api/v2/post/publish")
    print(f"       - Sheet: {payload['sheet_name']}")
    print(f"       - Index: {payload['index']}")
    print(f"       - Images: {len(payload['local_images'])}")

    try:
        res = requests.post(f"{BASE_URL}/api/v2/post/publish", json=payload)
        
        print(f"\n[INFO] Response Status: {res.status_code}")
        print(f"[INFO] Response Body: {res.text}")
        
        if res.status_code == 200:
            data = res.json()
            task_id = data.get("task_id")
            print(f"\n✅ Request accepted. Task ID: {task_id}")
            print("Check server logs for '[DEBUG] Received publish request...'")
        else:
            print("\n❌ Request failed!")
            
    except Exception as e:
        print(f"\n❌ Connection Error: {e}")
        print("ensure server.py is running on port 3000")

if __name__ == "__main__":
    test_haravan_publish_with_local_images()
