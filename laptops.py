#!/usr/bin/env python3
"""
TAP.AZ Scraper - Fixed Decompression Issue
The site returns compressed data that needs proper handling
"""

import requests
from bs4 import BeautifulSoup
import time
import random
import json
import csv
import gzip
import zlib
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional
from urllib.parse import urljoin

@dataclass
class LaptopListing:
    id: str
    name: str
    price: str
    currency: str
    location: str
    brand: str
    is_shop: bool
    is_vip: bool
    is_featured: bool
    is_bumped: bool
    url: str
    image_url: str
    scraped_at: str

class TapAzScraperFixed:
    def __init__(self):
        self.base_url = "https://tap.az"
        self.laptop_url = "https://tap.az/elanlar/elektronika/noutbuklar"
        self.session = self._create_session()
        self.listings = []
    
    def _create_session(self):
        """Create session with proper decompression handling"""
        session = requests.Session()
        
        # Headers WITHOUT compression to avoid the issue
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,az;q=0.8',
            # Remove Accept-Encoding to avoid compression issues
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        session.headers.update(headers)
        return session
    
    def _decompress_response(self, response):
        """Manually decompress response if needed"""
        content = response.content
        
        print(f"🔍 Response encoding: {response.encoding}")
        print(f"📊 Content-Encoding header: {response.headers.get('content-encoding', 'none')}")
        print(f"📏 Raw content length: {len(content)} bytes")
        
        # Check if content looks like binary/compressed
        try:
            # Try to decode as UTF-8 first
            text = content.decode('utf-8')
            print(f"✅ Successfully decoded as UTF-8")
            return text
        except UnicodeDecodeError:
            print("❌ UTF-8 decode failed, trying decompression...")
        
        # Try gzip decompression
        try:
            if content.startswith(b'\x1f\x8b'):  # gzip magic number
                text = gzip.decompress(content).decode('utf-8')
                print(f"✅ Successfully decompressed with gzip")
                return text
        except Exception as e:
            print(f"❌ Gzip decompression failed: {e}")
        
        # Try deflate decompression
        try:
            text = zlib.decompress(content).decode('utf-8')
            print(f"✅ Successfully decompressed with deflate")
            return text
        except Exception as e:
            print(f"❌ Deflate decompression failed: {e}")
        
        # Try deflate with -15 wbits (raw deflate)
        try:
            text = zlib.decompress(content, -15).decode('utf-8')
            print(f"✅ Successfully decompressed with raw deflate")
            return text
        except Exception as e:
            print(f"❌ Raw deflate decompression failed: {e}")
        
        # If all fails, try to use response.text (let requests handle it)
        try:
            text = response.text
            print(f"✅ Using response.text fallback")
            return text
        except Exception as e:
            print(f"❌ All decompression methods failed: {e}")
            return ""
    
    def _clean_text(self, text: str) -> str:
        """Clean text content"""
        if not text:
            return ""
        
        text = text.strip()
        text = text.replace('\n', ' ').replace('\r', ' ')
        text = ' '.join(text.split())
        
        replacements = {
            '"': '"', '"': '"', ''': "'", ''': "'",
            '&quot;': '"', '&#39;': "'", '&amp;': '&'
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text
    
    def _extract_brand(self, name: str) -> str:
        """Extract brand from laptop name"""
        name_lower = name.lower()
        brands = {
            'Apple': ['apple', 'macbook'],
            'Lenovo': ['lenovo', 'thinkpad', 'ideapad', 'legion'],
            'ASUS': ['asus', 'zenbook', 'vivobook', 'rog', 'tuf'],
            'HP': ['hp', 'pavilion', 'envy', 'omen', 'victus', 'probook', 'elitebook'],
            'Dell': ['dell', 'inspiron', 'latitude', 'precision', 'vostro', 'alienware'],
            'Acer': ['acer', 'aspire', 'predator', 'nitro', 'swift'],
            'Samsung': ['samsung'],
            'MSI': ['msi'],
            'Toshiba': ['toshiba'],
            'Huawei': ['huawei', 'matebook']
        }
        
        for brand, keywords in brands.items():
            if any(keyword in name_lower for keyword in keywords):
                return brand
        
        return 'Other'
    
    def _parse_listings_from_html(self, html: str) -> List[LaptopListing]:
        """Parse laptop listings from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        listings = []
        
        print(f"📄 HTML length: {len(html):,} characters")
        print(f"📝 Title: {soup.title.get_text() if soup.title else 'No title'}")
        
        # Debug: Show first 200 chars of HTML
        print(f"📝 First 200 chars: {html[:200]}")
        
        # Try multiple selectors
        selectors = [
            'div.products-i',
            'div[class*="products"]',
            '.product-item',
            '.listing-item',
            'div[data-ad-id]',
            '.products-shop',
            '.card',
            'article'
        ]
        
        product_containers = []
        used_selector = None
        
        for selector in selectors:
            containers = soup.select(selector)
            print(f"🔍 Selector '{selector}': {len(containers)} elements")
            if containers:
                product_containers = containers
                used_selector = selector
                break
        
        if not product_containers:
            print("❌ No product containers found")
            
            # Show all divs with classes for debugging
            all_divs = soup.find_all('div', class_=True)[:10]
            print(f"📊 Found {len(soup.find_all('div', class_=True))} divs with classes")
            print("🔍 Sample div classes:")
            for div in all_divs:
                classes = ' '.join(div.get('class', []))
                print(f"   - {classes}")
            
            return []
        
        print(f"✅ Using selector: {used_selector}")
        print(f"📦 Processing {len(product_containers)} containers...")
        
        for i, container in enumerate(product_containers):
            try:
                # Extract product ID
                id_elem = container.find(attrs={'data-ad-id': True})
                product_id = id_elem.get('data-ad-id') if id_elem else f'unknown_{i}'
                
                # Extract product name
                name_elem = container.find('div', class_='products-name')
                if not name_elem:
                    name_elem = container.find(class_=lambda x: x and 'name' in str(x).lower())
                
                if not name_elem:
                    continue
                
                product_name = self._clean_text(name_elem.get_text())
                
                # Extract price
                price_elem = container.find('span', class_='price-val')
                if not price_elem:
                    price_elem = container.find(class_=lambda x: x and 'price' in str(x).lower())
                
                if not price_elem:
                    continue
                
                price = price_elem.get_text(strip=True)
                
                # Extract currency
                currency_elem = container.find('span', class_='price-cur')
                currency = currency_elem.get_text(strip=True) if currency_elem else 'AZN'
                
                # Extract location
                location_elem = container.find('div', class_='products-created')
                location = location_elem.get_text(strip=True) if location_elem else 'Unknown'
                
                # Extract URL
                link_elem = container.find('a', class_='products-link')
                if not link_elem:
                    link_elem = container.find('a')
                
                product_url = ''
                if link_elem and link_elem.get('href'):
                    href = link_elem.get('href')
                    product_url = urljoin(self.base_url, href)
                
                # Extract image
                img_elem = container.find('img')
                image_url = img_elem.get('src', '') if img_elem else ''
                
                # Extract features
                container_str = str(container)
                is_shop = 'products-shop' in container_str
                is_vip = 'vipped' in container_str
                is_featured = 'featured' in container_str
                is_bumped = 'bumped' in container_str
                
                # Create listing
                listing = LaptopListing(
                    id=product_id,
                    name=product_name,
                    price=price,
                    currency=currency,
                    location=location,
                    brand=self._extract_brand(product_name),
                    is_shop=is_shop,
                    is_vip=is_vip,
                    is_featured=is_featured,
                    is_bumped=is_bumped,
                    url=product_url,
                    image_url=image_url,
                    scraped_at=datetime.now().isoformat()
                )
                
                listings.append(listing)
                
                if i < 3:  # Debug first few
                    print(f"✅ Item {i+1}: {product_name} - {price}")
                
            except Exception as e:
                print(f"❌ Error parsing item {i+1}: {e}")
                continue
        
        return listings
    
    def scrape(self, max_pages: int = 3) -> List[LaptopListing]:
        """Main scraping method with proper decompression"""
        all_listings = []
        
        print("🚀 TAP.AZ Scraper with Decompression Fix")
        print("="*50)
        
        for page in range(max_pages):
            try:
                url = self.laptop_url
                print(f"\n📥 Scraping page {page + 1}: {url}")
                
                # Random delay
                delay = random.uniform(3, 6)
                print(f"⏳ Waiting {delay:.1f} seconds...")
                time.sleep(delay)
                
                # Make request
                response = self.session.get(url, timeout=30)
                print(f"📊 Status: {response.status_code}")
                
                if response.status_code != 200:
                    print(f"❌ Bad status code: {response.status_code}")
                    continue
                
                # Decompress and get readable HTML
                html_content = self._decompress_response(response)
                
                if not html_content or len(html_content) < 1000:
                    print(f"❌ Invalid HTML content (length: {len(html_content)})")
                    continue
                
                # Save decompressed HTML for debugging
                with open(f'decompressed_page_{page+1}.html', 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print(f"💾 Saved decompressed HTML to: decompressed_page_{page+1}.html")
                
                # Parse listings
                page_listings = self._parse_listings_from_html(html_content)
                
                if page_listings:
                    all_listings.extend(page_listings)
                    print(f"✅ Found {len(page_listings)} listings on page {page + 1}")
                    print(f"📈 Total so far: {len(all_listings)}")
                else:
                    print(f"❌ No listings found on page {page + 1}")
                    break
                
            except Exception as e:
                print(f"❌ Error on page {page + 1}: {e}")
                import traceback
                traceback.print_exc()
                break
        
        self.listings = all_listings
        print(f"\n🎉 Scraping completed! Total: {len(all_listings)} listings")
        return all_listings
    
    def save_to_csv(self, filename: str = None) -> str:
        """Save listings to CSV"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tapaz_laptops_{timestamp}.csv"
        
        if not self.listings:
            print("⚠️ No listings to save")
            return filename
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(asdict(self.listings[0]).keys()))
            writer.writeheader()
            for listing in self.listings:
                writer.writerow(asdict(listing))
        
        print(f"💾 Saved {len(self.listings)} listings to {filename}")
        return filename
    
    def print_results(self):
        """Print results summary"""
        if not self.listings:
            print("❌ No listings found")
            return
        
        print(f"\n📋 Found {len(self.listings)} laptop listings:")
        print("-" * 60)
        
        # Show first 5 listings
        for i, listing in enumerate(self.listings[:5], 1):
            print(f"{i:2d}. {listing.name}")
            print(f"    💰 {listing.price} {listing.currency}")
            print(f"    🏷️ Brand: {listing.brand}")
            print(f"    📍 {listing.location}")
            print(f"    🔗 {listing.url}")
            print()
        
        if len(self.listings) > 5:
            print(f"... and {len(self.listings) - 5} more listings")
        
        # Basic stats
        brands = {}
        for listing in self.listings:
            brands[listing.brand] = brands.get(listing.brand, 0) + 1
        
        print(f"\n📊 Brand distribution:")
        for brand, count in sorted(brands.items(), key=lambda x: x[1], reverse=True):
            print(f"   {brand}: {count}")

def main():
    try:
        scraper = TapAzScraperFixed()
        listings = scraper.scrape(max_pages=2)
        
        if listings:
            scraper.print_results()
            filename = scraper.save_to_csv()
            print(f"\n✅ Success! Saved to: {filename}")
        else:
            print("❌ No listings found - check the decompressed HTML files")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
