import requests
import json
import os

def test_analyze():
    url = "https://www.thietbihatlive.com/products/loa-karaoke-di-dong-ppaudio-ts220?srsltid=AfmBOopUS_BZXQicKbZ7XEG18qV-GogK5aOi3RAM5NhsCud3fpEkjLSK"
    api_url = "http://localhost:3000/api/v2/woocommerce/analyze"
    
    # We need an AI key. I'll try to find it in the environment or files if possible, 
    # but the API requires it in the body.
    # On the frontend, it's stored in localStorage.
    # For testing, I'll use a placeholder or try to read it from a config file if I can find one.
    
    payload = {
        "url": url,
        "api_key": "TODO_FIND_KEY",
        "system_prompt": "You are a WooCommerce expert. Rewrite product info to be SEO friendly."
    }
    
    # Since I don't have the key easily here without reading files, 
    # I'll just check if the scraping part of URLAnalyzer works first.
    from services.url_analyzer import URLAnalyzer
    
    print(f"Testing scraping for: {url}")
    analyzer = URLAnalyzer(api_key="dummy") # AI not needed for scraping
    raw_info = analyzer.scrape_product_info(url)
    print("Raw Info Keys:", raw_info.keys())
    if "error" in raw_info:
        print("Scraping Error:", raw_info["error"])
    else:
        print("Scraping Title:", raw_info.get("raw_title"))
        print("Scraping Price:", raw_info.get("raw_price"))
        print("Content Snippet Length:", len(raw_info.get("content_snippet", "")))

if __name__ == "__main__":
    test_analyze()
