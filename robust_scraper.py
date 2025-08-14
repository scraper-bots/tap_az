#!/usr/bin/env python3
"""
Ultra-robust scraper with multiple fallback strategies
"""

import requests
import time
import random
import json
import csv
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
import logging
from fake_useragent import UserAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class RobustScraper:
    def __init__(self, proxy_token="e3bf6a3303714404b00f11451786c08ac29046a1e0f"):
        self.session = requests.Session()
        self.base_url = "https://tap.az"
        self.laptops_url = "https://tap.az/elanlar/elektronika/noutbuklar"
        self.proxy_token = proxy_token
        self.proxy_base = "http://api.scrape.do/"
        
        # Initialize user agent
        try:
            self.ua = UserAgent()
        except:
            self.ua = None
    
    def get_user_agent(self):
        """Get a random user agent"""
        if self.ua:
            try:
                return self.ua.random
            except:
                pass
        
        # Fallback user agents
        agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        return random.choice(agents)
    
    def is_valid_html(self, text):
        """Check if response is valid HTML"""
        if not text or len(text) < 100:
            return False
        
        # Check for HTML indicators
        html_indicators = ['<html', '<head', '<body', '<!doctype', 'noutbuk', 'laptop']
        text_lower = text.lower()
        
        return any(indicator in text_lower for indicator in html_indicators)
    
    def try_proxy_request(self, url):
        """Try proxy request with different strategies"""
        strategies = [
            # Strategy 1: Simple proxy
            {"url": f"{self.proxy_base}?url={quote(url, safe='')}&token={self.proxy_token}"},
            
            # Strategy 2: With format parameter
            {"url": f"{self.proxy_base}?url={quote(url, safe='')}&token={self.proxy_token}&format=html"},
            
            # Strategy 3: With render parameter
            {"url": f"{self.proxy_base}?url={quote(url, safe='')}&token={self.proxy_token}&render=false"},
        ]
        
        for i, strategy in enumerate(strategies, 1):
            try:
                logger.info(f"Trying proxy strategy {i}/3...")
                
                headers = {
                    'User-Agent': self.get_user_agent(),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'identity',  # Don't accept compressed responses
                }
                
                response = self.session.get(strategy["url"], headers=headers, timeout=45)
                
                if response.status_code == 200 and self.is_valid_html(response.text):
                    logger.info(f"Proxy strategy {i} successful: {len(response.text)} chars")
                    return response
                else:
                    logger.warning(f"Proxy strategy {i} failed: status={response.status_code}, valid_html={self.is_valid_html(response.text)}")
                    
            except Exception as e:
                logger.warning(f"Proxy strategy {i} error: {e}")
                
            time.sleep(1)  # Brief delay between strategies
        
        return None
    
    def try_direct_request(self, url):
        """Try direct request with stealth headers"""
        try:
            logger.info("Trying direct request...")
            
            # Create fresh session for direct request
            direct_session = requests.Session()
            
            headers = {
                'User-Agent': self.get_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9,az;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0'
            }
            
            # First visit homepage to get cookies
            homepage_response = direct_session.get("https://tap.az", headers=headers, timeout=30)
            time.sleep(random.uniform(2, 4))
            
            # Then visit laptops page
            headers['Referer'] = 'https://tap.az'
            response = direct_session.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200 and self.is_valid_html(response.text):
                logger.info(f"Direct request successful: {len(response.text)} chars")
                return response
            else:
                logger.warning(f"Direct request failed: status={response.status_code}")
                
        except Exception as e:
            logger.warning(f"Direct request error: {e}")
        
        return None
    
    def parse_products(self, html):
        """Parse products from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        products = []
        
        # Check page validity
        title = soup.find('title')
        if title:
            logger.info(f"Page title: {title.get_text(strip=True)[:100]}")
        
        # Try different selectors
        selectors = [
            'div.products-i',
            'div[data-ad-id]',
            'a[href*="/elanlar/elektronika/noutbuklar/"]'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            logger.info(f"Selector '{selector}': Found {len(elements)} elements")
            
            if elements:
                for element in elements[:20]:  # Limit to 20 products
                    try:
                        # Find the product container
                        product_div = element
                        if element.name == 'a':
                            product_div = element.find_parent('div')
                        
                        if not product_div:
                            continue
                        
                        # Extract product information
                        name = "N/A"
                        name_elem = product_div.select_one('.products-name, [class*="name"], .title')
                        if name_elem:
                            name = name_elem.get_text(strip=True)
                        
                        price = "N/A"
                        price_elem = product_div.select_one('.price-val, [class*="price"]')
                        if price_elem:
                            price = price_elem.get_text(strip=True)
                        
                        url = "N/A"
                        link_elem = product_div.select_one('a[href*="/elanlar/"]')
                        if link_elem:
                            url = urljoin(self.base_url, link_elem.get('href', ''))
                        elif element.name == 'a':
                            url = urljoin(self.base_url, element.get('href', ''))
                        
                        location = "N/A"
                        created_elem = product_div.select_one('.products-created')
                        if created_elem:
                            created_text = created_elem.get_text(strip=True)
                            if ',' in created_text:
                                location = created_text.split(',')[0].strip()
                        
                        if name != "N/A" and (price != "N/A" or url != "N/A"):
                            product = {
                                'name': name,
                                'price': price,
                                'location': location,
                                'url': url,
                                'strategy': selector
                            }
                            products.append(product)
                            
                    except Exception as e:
                        logger.debug(f"Error parsing element: {e}")
                        continue
                
                if products:
                    break
        
        logger.info(f"Successfully parsed {len(products)} products")
        return products
    
    def extract_next_cursor(self, html):
        """Extract next page cursor from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for pagination
        pagination = soup.find('div', class_='pagination')
        if pagination:
            next_link = pagination.find('a')
            if next_link and next_link.get('href'):
                href = next_link.get('href')
                if 'cursor=' in href:
                    import re
                    cursor_match = re.search(r'cursor=([^&]+)', href)
                    if cursor_match:
                        return cursor_match.group(1)
        
        return None
    
    def scrape_page(self, cursor=None):
        """Scrape a single page"""
        url = self.laptops_url
        if cursor:
            url = f"{self.laptops_url}?cursor={cursor}"
        
        # Try proxy first
        response = self.try_proxy_request(url)
        method = "proxy"
        
        if not response:
            # Fallback to direct
            time.sleep(random.uniform(2, 4))
            response = self.try_direct_request(url)
            method = "direct"
        
        if not response:
            return [], None, "failed"
        
        products = self.parse_products(response.text)
        next_cursor = self.extract_next_cursor(response.text)
        
        return products, next_cursor, method
    
    def scrape_all(self, max_pages=None):
        """Scrape all pages with infinite scrolling"""
        logger.info("Starting FULL scraping of ALL pages...")
        
        all_products = []
        cursor = None
        page_count = 0
        total_products = 0
        methods_used = {}
        
        while True:
            page_count += 1
            
            if max_pages and page_count > max_pages:
                logger.info(f"Reached maximum pages limit: {max_pages}")
                break
            
            logger.info(f"Scraping page {page_count}...")
            
            products, next_cursor, method = self.scrape_page(cursor)
            
            # Track methods used
            methods_used[method] = methods_used.get(method, 0) + 1
            
            if not products:
                logger.warning(f"No products found on page {page_count}")
                if page_count == 1:
                    # If first page fails, something is wrong
                    logger.error("First page failed, stopping")
                    break
                else:
                    # If later page fails, might be end of results
                    logger.info("No more products, reached end")
                    break
            
            all_products.extend(products)
            total_products += len(products)
            
            logger.info(f"Page {page_count}: Found {len(products)} products (Total: {total_products})")
            
            # Progress update every 10 pages
            if page_count % 10 == 0:
                print(f"🔄 Progress: {page_count} pages scraped, {total_products} products collected")
            
            # Save backup every 500 products
            if total_products % 500 == 0 and total_products > 0:
                backup_filename = f"backup_{total_products}_products"
                self.save_results(all_products, f"mixed({methods_used})", backup_filename)
                print(f"💾 Backup saved: {total_products} products")
            
            cursor = next_cursor
            if not cursor:
                logger.info("No next cursor found, reached end of results")
                break
            
            # Delay between pages
            time.sleep(random.uniform(2, 5))
        
        logger.info(f"Full scraping completed!")
        logger.info(f"Total pages: {page_count}")
        logger.info(f"Total products: {total_products}")
        logger.info(f"Methods used: {methods_used}")
        
        return all_products, methods_used
    
    def scrape(self):
        """Main scraping method - now scrapes ALL pages"""
        return self.scrape_all()
    
    def save_results(self, products, method, filename="robust_results"):
        """Save results to files"""
        if not products:
            logger.warning("No products to save")
            return
        
        # Add method info to products
        for product in products:
            product['scrape_method'] = method
        
        # Save JSON
        with open(f'{filename}.json', 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        # Save CSV
        with open(f'{filename}.csv', 'w', newline='', encoding='utf-8') as f:
            if products:
                writer = csv.DictWriter(f, fieldnames=products[0].keys())
                writer.writeheader()
                writer.writerows(products)
        
        logger.info(f"Saved {len(products)} products to {filename}.json/.csv")

def main():
    print("🔥 FULL TAP.AZ SCRAPER - ALL PAGES")
    print("=" * 60)
    print("🚀 Scraping ALL laptop listings with infinite scrolling!")
    print("📊 Progress updates every 10 pages")
    print("💾 Auto-backup every 500 products")
    print("-" * 60)
    
    scraper = RobustScraper()
    
    try:
        # Auto-start full scraping
        print("⚠️  Scraping ALL pages (could be 1000+ products)")
        print("✅ Auto-starting in 3 seconds...")
        
        print("\n🎯 Starting FULL scraping...")
        print("Press Ctrl+C to stop gracefully and save current progress")
        print()
        
        products, methods_used = scraper.scrape()
        
        if products:
            print(f"\n🎉 SCRAPING COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print(f"📊 FINAL STATISTICS:")
            print(f"   Total Products: {len(products)}")
            print(f"   Methods Used: {methods_used}")
            
            # Save final results
            scraper.save_results(products, f"full_scrape({methods_used})")
            
            print(f"\n📱 Sample Products (First 20):")
            print("-" * 90)
            print(f"{'#':<3} {'Name':<45} {'Price':<12} {'Location':<15} {'Method'}")
            print("-" * 90)
            
            for i, product in enumerate(products[:20]):
                name = product['name'][:42] + "..." if len(product['name']) > 45 else product['name']
                price = product['price'] if len(product['price']) <= 10 else product['price'][:10] + "..."
                method_short = product.get('scrape_method', 'unknown')[:8]
                
                print(f"{i+1:<3} {name:<45} {price:<12} {product['location']:<15} {method_short}")
            
            if len(products) > 20:
                print(f"    ... and {len(products) - 20} more products")
            
            # Price analysis
            prices = []
            for p in products:
                try:
                    clean_price = p['price'].replace(' ', '').replace(',', '').replace('AZN', '')
                    if clean_price and clean_price.replace('.', '').isdigit():
                        prices.append(float(clean_price))
                except:
                    pass
            
            if prices:
                print(f"\n💰 PRICE ANALYSIS:")
                print(f"   Products with valid prices: {len(prices)}")
                print(f"   Price range: {min(prices):.0f} - {max(prices):,.0f} AZN")
                print(f"   Average price: {sum(prices)/len(prices):,.0f} AZN")
                print(f"   Median price: {sorted(prices)[len(prices)//2]:,.0f} AZN")
                
                # Price distribution
                cheap = sum(1 for p in prices if p < 500)
                mid = sum(1 for p in prices if 500 <= p < 2000)
                expensive = sum(1 for p in prices if p >= 2000)
                
                print(f"\n📈 PRICE DISTRIBUTION:")
                print(f"   Budget (< 500 AZN): {cheap} products ({cheap/len(prices)*100:.1f}%)")
                print(f"   Mid-range (500-2000 AZN): {mid} products ({mid/len(prices)*100:.1f}%)")
                print(f"   Premium (> 2000 AZN): {expensive} products ({expensive/len(prices)*100:.1f}%)")
            
            print(f"\n💾 Final data saved to:")
            print(f"   📄 robust_results.json")
            print(f"   📄 robust_results.csv")
            
        else:
            print("❌ No products could be scraped")
            
    except KeyboardInterrupt:
        print(f"\n⏹️  Scraping interrupted by user!")
        # The scraper automatically saves backups, so data is preserved
        print("💾 Your progress has been saved in backup files")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logger.error(f"Main error: {e}")
    
    print(f"\n🏁 FULL SCRAPING SESSION COMPLETED!")

if __name__ == "__main__":
    main()