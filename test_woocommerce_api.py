import requests
import json
import os

BASE_URL = "http://localhost:3000/api/v2/woocommerce"

def test_config():
    print("\n--- Testing WooCommerce Config ---")
    data = {
        "site_url": "https://example.com",
        "consumer_key": "ck_test_123",
        "consumer_secret": "cs_test_456"
    }
    res = requests.post(f"{BASE_URL}/config", json=data)
    print(f"POST Config: {res.json()}")
    
    res = requests.get(f"{BASE_URL}/config")
    print(f"GET Config: {res.json()}")

def test_db_read():
    print("\n--- Testing WooCommerce DB Read ---")
    res = requests.get(f"{BASE_URL}/db")
    print(f"DB Rows: {res.status_code}")
    if res.status_code == 200:
        print(f"First row (if any): {res.json()[:1]}")

def test_analyze():
    print("\n--- Testing URL AI Analyze ---")
    # Cần API Key thực tế để chạy thật, ở đây test response lỗi nếu thiếu key
    res = requests.post(f"{BASE_URL}/analyze", json={
        "url": "https://www.apple.com/iphone-15/",
        "api_key": "dummy_key",
        "system_prompt": "Write a funny SEO description"
    })
    print(f"Analyze Status: {res.status_code}, Body: {res.text}")

def test_add_item():
    print("\n--- Testing Add Item ---")
    data = {
        "title": "Test Product from API",
        "regular_price": "99.99",
        "description": "This is a test product created by verification script."
    }
    res = requests.post(f"{BASE_URL}/add-item", json=data)
    print(f"Add Item: {res.json()}")

if __name__ == "__main__":
    # Ensure server is running
    try:
        test_config()
        test_db_read()
        test_add_item()
        test_analyze()
    except Exception as e:
        print(f"Test failed: {e}")
