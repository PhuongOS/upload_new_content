
import google.generativeai as genai
import sys

def test_key(api_key):
    print(f"Testing API Key: {api_key[:10]}...")
    try:
        genai.configure(api_key=api_key.strip())
        model = genai.GenerativeModel('gemini-flash-latest')
        response = model.generate_content("Say hello")
        if response and response.text:
            print("✅ API Key is working perfectly!")
            print(f"Response: {response.text}")
        else:
            print("⚠️ API Key returned an empty response.")
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Resource has been exhausted" in error_msg:
            print("❌ API Key is currently LIMITED (Quota Exceeded - 429).")
        elif "API_KEY_INVALID" in error_msg or "403" in error_msg:
            print("❌ API Key is INVALID or Forbidden (403).")
        else:
            print(f"❌ Error testing API Key: {error_msg}")

if __name__ == "__main__":
    key = "AIzaSyBCgcHK6PmD_NzEzICpRBsKDnPHm669zk8" # The key being tested
    test_key(key)
