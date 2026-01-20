from provider.gemini import GeminiProvider
import os

def test_gemini_init():
    try:
        provider = GeminiProvider(api_key="TEST_KEY", system_prompt="Test Prompt")
        print("✅ GeminiProvider initialized successfully")
    except Exception as e:
        print(f"❌ GeminiProvider initialization failed: {e}")

if __name__ == "__main__":
    test_gemini_init()
