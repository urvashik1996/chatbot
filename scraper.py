import requests
from bs4 import BeautifulSoup
import logging
import time
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError as e:
    logging.error(f"Selenium import failed: {e}")
    raise

logging.basicConfig(level=logging.DEBUG)

def fetch_page(url, use_selenium=True, retries=2, delay=2):
    """Fetch and parse a webpage, returning a BeautifulSoup object, with retries."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    }

    # Try with Selenium first
    if use_selenium:
        for attempt in range(retries + 1):
            try:
                options = Options()
                options.add_argument('--headless')
                options.add_argument('--disable-gpu')
                options.add_argument(f'user-agent={headers["User-Agent"]}')
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
                driver.get(url)
                time.sleep(1)  # Wait for page to load
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                driver.quit()
                return soup
            except Exception as e:
                logging.error(f"Attempt {attempt + 1}/{retries + 1} - Error fetching {url} with Selenium: {e}")
                if attempt == retries:
                    logging.warning(f"Max retries reached for Selenium. Falling back to requests for {url}.")
                    break
                time.sleep(delay)

    # Fallback to requests
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            return soup
        except requests.RequestException as e:
            logging.error(f"Attempt {attempt + 1}/{retries + 1} - Error fetching {url}: {e}")
            if attempt == retries:
                logging.error(f"Max retries reached for {url}. Failed to fetch content.")
                return None
            time.sleep(delay)

def build_website_map(base_url="https://stolmeierlaw.com/"):
    """Build a knowledge map of the website's structure (titles and URLs only, no content)."""
    website_map = {}
    logging.debug("Building website knowledge map (structure only)...")

    # Hardcode the navigation structure to avoid unnecessary scraping
    nav_items = [
        {'title': 'Home', 'url': 'https://stolmeierlaw.com/', 'subcategories': []},
        {'title': 'Practice Areas', 'url': 'https://stolmeierlaw.com/practice-areas/', 'subcategories': []},
        {'title': 'Recent Results', 'url': 'https://stolmeierlaw.com/recent-results/', 'subcategories': []},
        {'title': 'About', 'url': 'https://stolmeierlaw.com/about/', 'subcategories': []},
        {'title': 'Blogs', 'url': 'https://stolmeierlaw.com/blogs/', 'subcategories': []},
        {'title': 'Contact Us', 'url': 'https://stolmeierlaw.com/contact-us/', 'subcategories': []}
    ]

    # Hardcode subcategories for Practice Areas (can be updated if the website changes)
    practice_area_subcategories = [
        {'title': 'Car Accidents', 'url': 'https://stolmeierlaw.com/car-accidents/', 'description': 'No description available.'},
        {'title': 'Personal Injury', 'url': 'https://stolmeierlaw.com/personal-injury/', 'description': 'No description available.'},
        {'title': 'Family Law', 'url': 'https://stolmeierlaw.com/family-law/', 'description': 'No description available.'},
        {'title': 'Criminal Defense', 'url': 'https://stolmeierlaw.com/criminal-defense/', 'description': 'No description available.'},
        {'title': 'Wrongful Death', 'url': 'https://stolmeierlaw.com/wrongful-death/', 'description': 'No description available.'},
        {'title': 'Medical Malpractice', 'url': 'https://stolmeierlaw.com/medical-malpractice/', 'description': 'No description available.'}
    ]

    website_map = {item['title'].lower(): {'url': item['url'], 'subcategories': {}} for item in nav_items}
    website_map['practice areas']['subcategories'] = {
        sub['title'].lower(): {'url': sub['url'], 'content': []} for sub in practice_area_subcategories
    }

    logging.debug(f"Website map structure: {website_map}")
    return website_map

def scrape_contact_info_fallback():
    """Scrape contact info directly from the website (only when requested)."""
    soup = fetch_page("https://stolmeierlaw.com/")
    if not soup:
        return "Sorry, I couldn't fetch contact information."
    
    footer = soup.find('footer')
    if footer:
        contact_section = footer.find_all(['p', 'div'], string=lambda text: text and any(keyword in text.lower() for keyword in ['contact', 'phone', 'email', 'address']))
        contact_text = ' '.join([elem.get_text(strip=True) for elem in contact_section])
        return contact_text or "No contact information found on the website."
    
    return "No contact information found on the website."