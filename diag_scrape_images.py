
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def test_scrape(url):
    print(f"Testing scraping for: {url}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        images = []
        for meta_prop in ["og:image", "twitter:image"]:
            img_meta = soup.find("meta", property=meta_prop) or soup.find("meta", attrs={"name": meta_prop})
            if img_meta and img_meta.get("content"):
                images.append(urljoin(url, img_meta.get("content")))
        
        # Selectors
        selectors = ['img.wp-post-image', '.woocommerce-product-gallery__image img', 'img.main-image', '.product-single__media img']
        for sel in selectors:
            found = soup.select(sel)
            for f in found:
                src = f.get('src') or f.get('data-src') or f.get('srcset')
                if src:
                    # srcset can have multiple urls, just take the first
                    actual_src = src.split(' ')[0].split(',')[0].strip()
                    images.append(urljoin(url, actual_src))
        
        unique = []
        for img in images:
            if img.startswith('http') and img not in unique:
                unique.append(img)
        
        print(f"Found {len(unique)} image(s):")
        for i in unique[:5]:
            print(f" - {i}")
            
    except Exception as e:
        print(f"Scrape failed: {e}")

test_url = "https://www.thietbihatlive.com/products/loa-karaoke-di-dong-ppaudio-ts220"
test_scrape(test_url)
