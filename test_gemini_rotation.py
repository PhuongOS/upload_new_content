
import unittest
from unittest.mock import MagicMock, patch
from provider.gemini import GeminiProvider

class TestGeminiRotation(unittest.TestCase):
    @patch('provider.gemini.genai')
    def test_key_rotation_on_429(self, mock_genai):
        # Setup mocking for the model
        mock_model_instance = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model_instance
        
        # Call fails with 429, then succeeds
        error_429 = Exception("429 Resource has been exhausted")
        # Note: we need to return text from the second call's result
        mock_success_response = MagicMock()
        mock_success_response.text = "Success!"
        
        mock_model_instance.generate_content.side_effect = [error_429, mock_success_response]
        
        # Execute
        keys = "key1\nkey2"
        provider = GeminiProvider(keys)
        # Ensure we use the mock instance
        provider.model = mock_model_instance
        
        result = provider.generate_content("Try me")
        
        # Assertions
        self.assertEqual(result, "Success!")
        self.assertEqual(provider.current_key_index, 1) # Should have rotated
        self.assertEqual(mock_model_instance.generate_content.call_count, 2)
        print("✅ Passed: API Key rotated correctly on 429 error.")

    @patch('provider.gemini.genai')
    def test_rotation_exhaustion(self, mock_genai):
        mock_model_instance = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model_instance
        
        error_503 = Exception("503 Service Unavailable")
        mock_model_instance.generate_content.side_effect = [error_503, error_503]
        
        keys = "key1,key2"
        provider = GeminiProvider(keys)
        provider.model = mock_model_instance
        
        with self.assertRaisesRegex(Exception, "Đã thử 2 API Keys nhưng đều thất bại"):
            provider.generate_content("Try me")
            
        self.assertEqual(mock_model_instance.generate_content.call_count, 2)
        print("✅ Passed: Exhaustion handled correctly.")

if __name__ == "__main__":
    unittest.main()
