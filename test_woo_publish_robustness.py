
import unittest
from unittest.mock import MagicMock, patch
from post_service.manager import PostManager
import datetime

class TestWooPublishRobustness(unittest.TestCase):
    @patch('post_service.manager.SheetService')
    @patch('post_service.manager.WoocommercePublisher')
    def test_handle_woocommerce_publish_sheet_failure(self, MockWC, MockSheet):
        # 1. Setup Mock WooCommerce Success
        mock_wc_instance = MockWC.return_value
        mock_wc_instance.create_product.return_value = {
            "success": True, 
            "data": {"id": 1234, "permalink": "https://site.com/prod"}
        }
        
        # 2. Setup Mock Sheet Config
        MockSheet.get_all_rows.return_value = [{
            "site_url": "https://site.com", 
            "consumer_key": "ck_...", 
            "consumer_secret": "cs_..."
        }]
        
        # 3. Setup Mock Sheet Update Failure
        MockSheet.update_row.side_effect = Exception("Google Sheet API Error")
        
        # 4. Execute
        manager = PostManager()
        item = {"title": "Test Product", "status": "NEW"}
        result = manager._handle_woocommerce_publish(item, "Woocommerce_db", 0)
        
        # 5. Assertions
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["id"], 1234)
        self.assertIn("warning", result)
        self.assertIn("Google Sheet API Error", result["warning"])
        print("✅ Passed: Reporting success with warning when sheet update fails.")

if __name__ == "__main__":
    unittest.main()
