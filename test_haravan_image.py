#!/usr/bin/env python3
"""
Test script to verify Haravan image publishing functionality.
"""
import sys
sys.path.insert(0, '/Users/hoaiphuong/Downloads/QT/Forms/Upload_File')

from post_service.haravan_publisher import HaravanPublisher
from services.sheet_service import SheetService
import json

def test_haravan_image_publish():
    """Test creating a product with images on Haravan."""
    
    # 1. Get Haravan config
    print("=" * 50)
    print("1. Đọc cấu hình Haravan...")
    configs = SheetService.get_all_rows("Haravan_Config")
    if not configs:
        print("❌ Chưa cấu hình Haravan!")
        return False
    
    config = configs[0]
    shop_url = config.get("shop_url")
    token = config.get("access_token")
    
    if not shop_url or not token:
        print("❌ Thiếu Shop URL hoặc Access Token!")
        return False
    
    print(f"✅ Shop URL: {shop_url}")
    
    # 2. Create publisher
    publisher = HaravanPublisher(shop_url, token)
    
    # 3. Create test product with images
    print("\n" + "=" * 50)
    print("2. Tạo sản phẩm test với hình ảnh...")
    
    test_images = [
        "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400",
        "https://images.unsplash.com/photo-1583394838336-acd977736f90?w=400"
    ]
    
    payload = {
        "title": "[TEST] Sản phẩm test có ảnh - " + str(__import__('time').time())[:10],
        "body_html": "<p>Đây là sản phẩm test để kiểm tra chức năng đăng ảnh.</p>",
        "vendor": "Test Vendor",
        "product_type": "Test Type",
        "published": True,
        "variants": [
            {
                "option1": "Default Title",
                "price": "100000",
                "compare_at_price": "150000",
                "sku": f"TEST-{int(__import__('time').time())}",
                "grams": 200,
                "inventory_policy": "deny",
                "fulfillment_service": "manual",
                "inventory_management": None,
                "requires_shipping": True
            }
        ],
        "options": [
            {
                "name": "Title",
                "values": ["Default Title"]
            }
        ],
        "images": [{"src": img} for img in test_images]
    }
    
    print(f"📷 Số lượng ảnh: {len(test_images)}")
    for i, img in enumerate(test_images, 1):
        print(f"   Ảnh {i}: {img[:60]}...")
    
    # 4. Call API
    print("\n" + "=" * 50)
    print("3. Gọi API tạo sản phẩm...")
    
    result = publisher.create_product(payload)
    
    if result["success"]:
        product = result["data"].get("product", {})
        p_id = product.get("id")
        handle = product.get("handle")
        images = product.get("images", [])
        
        print(f"\n✅ TẠO SẢN PHẨM THÀNH CÔNG!")
        print(f"   - Product ID: {p_id}")
        print(f"   - Handle: {handle}")
        print(f"   - Link: {shop_url}/products/{handle}")
        print(f"   - Số ảnh đã upload: {len(images)}")
        
        if images:
            print("\n📷 Danh sách ảnh đã upload:")
            for i, img in enumerate(images, 1):
                print(f"   {i}. ID: {img.get('id')}")
                print(f"      URL: {img.get('src', 'N/A')[:80]}...")
        
        return True
    else:
        print(f"\n❌ LỖI: {result.get('error')}")
        return False

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("   HARAVAN IMAGE PUBLISHING TEST")
    print("=" * 60 + "\n")
    
    success = test_haravan_image_publish()
    
    print("\n" + "=" * 60)
    if success:
        print("   ✅ TEST PASSED - Hình ảnh đã được upload thành công!")
    else:
        print("   ❌ TEST FAILED - Có lỗi xảy ra!")
    print("=" * 60 + "\n")
