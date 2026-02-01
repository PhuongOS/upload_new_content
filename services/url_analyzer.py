import requests
from bs4 import BeautifulSoup
import re
import json
from provider.gemini import GeminiProvider

class URLAnalyzer:
    def __init__(self, api_key, system_prompt=None):
        self.ai = GeminiProvider(api_key, system_prompt)

    def scrape_product_info(self, url):
        """
        Cào thông tin thô từ trang web sản phẩm bao gồm cả ảnh
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=20)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. Trích xuất tiêu đề
            title = soup.title.string if soup.title else ""
            
            # 2. Trích xuất giá
            price = ""
            price_meta = soup.find("meta", property="product:price:amount") or \
                         soup.find("meta", property="og:price:amount") or \
                         soup.find("meta", itemprop="price")
            if price_meta:
                price = price_meta.get("content", "")
            
            # 3. Trích xuất ảnh
            images = []
            from urllib.parse import urljoin
            
            # Meta tags (Commonly best quality)
            for meta_prop in ["og:image", "twitter:image", "product:image"]:
                img_meta = soup.find("meta", property=meta_prop) or soup.find("meta", attrs={"name": meta_prop})
                if img_meta and img_meta.get("content"):
                    img_url = urljoin(url, img_meta.get("content"))
                    images.append(img_url)
            
            # Common product image selectors
            img_selectors = [
                'img.wp-post-image', 
                'img.attachment-shop_single',
                '.woocommerce-product-gallery__image img',
                '#main-image',
                '.product-image-main',
                'img.main-image',
                '#ProductPhoto img',
                '.product-single__media img',
                '.product-media-content img',
                '.flex-control-thumbs img'
            ]
            for sel in img_selectors:
                found_elements = soup.select(sel)
                for found in found_elements:
                    src = found.get('src') or found.get('data-src') or found.get('data-lazy-src') or found.get('srcset')
                    if src:
                        # Nếu là srcset, lấy URL đầu tiên
                        actual_src = src.split(' ')[0].split(',')[0].strip()
                        img_url = urljoin(url, actual_src)
                        images.append(img_url)
            
            # Filter and deduplicate
            final_images = []
            for img in images:
                if img and img.startswith('http') and img not in final_images:
                    # Bỏ qua các icon nhỏ hoặc logo
                    lower_img = img.lower()
                    if not any(x in lower_img for x in ['logo', 'icon', 'pixel', 'avatar', 'spinner']):
                        # Ưu tiên các định dạng ảnh phổ biến
                        if any(ext in lower_img for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                            final_images.append(img)
            
            images = final_images[:8] # Lấy tối đa 8 ảnh

            # 4. Trích xuất văn bản thô
            for s in soup(["script", "style", "nav", "footer", "header"]):
                s.extract()
            body_text = soup.get_text(separator=' ', strip=True)
            
            return {
                "url": url,
                "raw_title": title,
                "raw_price": price,
                "scraped_images": images,
                "content_snippet": body_text[:6000]
            }
        except Exception as e:
            return {"error": str(e)}

    def generate_seo_product(self, raw_data, youtube_url=None):
        """
        Sử dụng AI để viết lại nội dung sản phẩm chuẩn SEO và chọn lọc ảnh.
        Nếu có youtube_url, sẽ chèn mã nhúng vào đầu mô tả.
        """
        if "error" in raw_data:
            return raw_data

        user_prompt = f"""
        Analyze the following raw product data and generate a structured JSON for a WooCommerce product.
        
        URL: {raw_data['url']}
        Title: {raw_data['raw_title']}
        Price: {raw_data['raw_price']}
        Scraped Images: {raw_data['scraped_images']}
        Content Snippet: {raw_data['content_snippet']}

        Return ONLY a JSON object with the following fields:
        {{
            "title": "SEO Optimized Product Title (Vietnamese)",
            "regular_price": "Numeric price found (no currency symbol)",
            "sale_price": "Suggest a slightly lower price if appropriate, or empty",
            "description": "Engaging HTML SEO optimized description (Vietnamese). USE <img> tags with src from 'Scraped Images' to illustrate features inside the description.",
            "short_description": "Catchy short summary (Vietnamese)",
            "categories": "Suggest category IDs as a comma-separated string if you can guess from content, else empty",
            "images": "Comma-separated list of the best image URLs from the 'Scraped Images' list"
        }}
        """
        
        try:
            ai_response = self.ai.generate_content(user_prompt)
            json_match = re.search(r"\{.*\}", ai_response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                # Chèn Video Youtube nếu có
                if youtube_url:
                    video_id = ""
                    if 'v=' in youtube_url:
                        video_id = youtube_url.split('v=')[-1].split('&')[0]
                    elif 'youtu.be/' in youtube_url:
                        video_id = youtube_url.split('youtu.be/')[-1].split('?')[0]
                    
                    if video_id:
                        iframe = f'<div class="video-container" style="text-align:center; margin-bottom:20px;"><iframe width="560" height="315" src="https://www.youtube.com/embed/{video_id}" frameborder="0" allowfullscreen></iframe></div>\n'
                        result['description'] = iframe + result.get('description', '')
                
                return result
            return {"error": "AI did not return valid JSON", "raw": ai_response}
        except Exception as e:
            return {"error": f"AI Error: {str(e)}"}
