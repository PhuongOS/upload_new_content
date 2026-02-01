import google.generativeai as genai
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GeminiProvider:
    def __init__(self, api_key_string, system_prompt=None):
        """
        api_key_string: Có thể là 1 key hoặc nhiều key cách nhau bởi dấu phẩy hoặc xuống dòng
        """
        raw_keys = []
        if api_key_string:
            # Tách theo xuống dòng hoặc dấu phẩy
            import re
            raw_keys = [k.strip() for k in re.split(r'[\n,]', api_key_string) if k.strip()]
        
        self.api_keys = raw_keys
        self.current_key_index = 0
        self.system_prompt = system_prompt or "You are a helpful social media content creator."
        
        if self.api_keys:
            self._configure_current_key()
        else:
            logging.warning("Gemini API Keys are missing. Generation requests will fail.")

    def _configure_current_key(self):
        """Cấu hình model với key hiện tại trong danh sách xoay vòng"""
        if not self.api_keys:
            return
        
        key = self.api_keys[self.current_key_index]
        genai.configure(api_key=key)
        self.model = genai.GenerativeModel('gemini-flash-latest')
        logging.info(f"[Gemini] Configured with key index {self.current_key_index} (starts with {key[:6]}...)")

    def generate_content(self, user_prompt):
        """
        Gửi yêu cầu đến Gemini để tạo nội dung, có hỗ trợ xoay vòng API Key nếu lỗi 429
        """
        if not self.api_keys:
            logging.error("No API Keys available for Gemini Provider.")
            raise ValueError("API Key is required for Gemini Provider")

        max_retries = len(self.api_keys)
        attempts = 0
        
        while attempts < max_retries:
            logging.info(f"[Gemini] Sending request with prompt length: {len(user_prompt)} (Attempt {attempts + 1})")
            full_prompt = f"System: {self.system_prompt}\n\nUser: {user_prompt}"
            
            try:
                response = self.model.generate_content(full_prompt)
                if response and response.text:
                    logging.info("Gemini content generated successfully.")
                    return response.text.strip()
                logging.warning("Gemini returned an empty response or no text.")
                return ""
            except Exception as e:
                error_msg = str(e)
                logging.error(f"[Gemini] Error on attempt {attempts + 1}: {error_msg}")
                
                # Nếu lỗi là Quota/Server busy, và còn key để thử
                retryable = any(code in error_msg for code in ["429", "503", "403", "Resource has been exhausted"])
                
                if retryable:
                    attempts += 1
                    if attempts < max_retries:
                        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                        logging.warning(f"[Gemini] Quota hit or Server Busy. Rotating to next key (Index {self.current_key_index})...")
                        self._configure_current_key()
                        continue # Thử lại với key mới
                    else:
                        # Đã thử hết các key, thoát vòng lặp để raise exhaustion error
                        break
                
                # Các lỗi nghiêm trọng không quay vòng (lỗi metadata hoặc timeout)
                if "Illegal metadata" in error_msg or "timeout" in error_msg.lower():
                    raise Exception("Lỗi cấu hình API Key hoặc Timeout. Vui lòng kiểm tra lại cấu hình.")
                
                raise e
                
        raise Exception(f"Đã thử {max_retries} API Keys nhưng đều thất bại (Error 429 - Hết quota hoặc Server lỗi). Vui lòng thử lại sau hoặc thêm API Key mới.")
