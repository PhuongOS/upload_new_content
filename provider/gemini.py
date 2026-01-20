import google.generativeai as genai

class GeminiProvider:
    def __init__(self, api_key, system_prompt=None):
        self.api_key = api_key
        self.system_prompt = system_prompt or "You are a helpful social media content creator."
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def generate_content(self, user_prompt):
        """
        Gửi yêu cầu đến Gemini để tạo nội dung
        """
        if not self.api_key:
            raise ValueError("API Key is required for Gemini Provider")
            
        full_prompt = f"System: {self.system_prompt}\n\nUser: {user_prompt}"
        
        try:
            response = self.model.generate_content(full_prompt)
            if response and response.text:
                return response.text.strip()
            return ""
        except Exception as e:
            print(f"Gemini Error: {e}")
            raise e
