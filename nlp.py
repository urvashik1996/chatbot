import nltk
import logging
from scraper import fetch_page

logging.basicConfig(level=logging.DEBUG)

try:
    nltk.download('punkt', quiet=True)
    nltk.download('wordnet', quiet=True)
except Exception as e:
    logging.error(f"Error downloading NLTK data: {e}")
    raise

def extract_keywords_and_intent(user_message, session_id, website_map, user_sessions):
    """Extract keywords and intent from the user message."""
    tokens = nltk.word_tokenize(user_message.lower())
    keywords = [token for token in tokens if token not in ['what', 'are', 'the', 'of', 'in', 'a', 'an', 'to', 'for', 'about']]
    
    # Simple intent detection
    intent = 'description'
    if any(word in user_message.lower() for word in ['cause', 'causes', 'reason', 'reasons']):
        intent = 'causes'
    elif any(word in user_message.lower() for word in ['about', 'who', 'what']):
        intent = 'about'
    elif any(word in user_message.lower() for word in ['contact', 'phone', 'email', 'address']):
        intent = 'contact'
    
    logging.debug(f"Session {session_id}: Extracted keywords: {keywords}, Intent: {intent}")
    return keywords, intent

def scrape_targeted_content(keywords, intent, session_id, url, website_map, user_sessions):
    """Scrape targeted content from the given URL based on keywords and intent."""
    logging.debug(f"Scraping content from {url} for keywords: {keywords}, intent: {intent}")

    # Fetch the page content
    soup = fetch_page(url)
    if not soup:
        return "Sorry, I couldn’t fetch the content for this section."

    # Determine the type of content to scrape based on intent
    if intent == 'causes':
        # Look for sections that might contain causes (e.g., headings with "causes", "reasons", or lists)
        content = []
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4'], string=lambda text: text and any(kw in text.lower() for kw in ['causes', 'reasons', 'factors'])):
            # Extract paragraphs or lists following the heading
            next_elements = heading.find_all_next(['p', 'ul', 'ol'], limit=5)
            for elem in next_elements:
                if elem.name == 'p':
                    text = elem.get_text(strip=True)
                    if text and len(text.split()) > 5:  # Ensure it's a meaningful paragraph
                        content.append(f"- {text}")
                elif elem.name in ['ul', 'ol']:
                    for li in elem.find_all('li'):
                        text = li.get_text(strip=True)
                        if text:
                            content.append(f"- {text}")
        if content:
            return "\n".join(content)
        return "Sorry, I couldn’t find specific information about causes for this section."

    elif intent == 'about':
        # Look for "About" sections or general descriptive paragraphs
        content = []
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4'], string=lambda text: text and 'about' in text.lower()):
            next_elements = heading.find_all_next(['p'], limit=3)
            for elem in next_elements:
                text = elem.get_text(strip=True)
                if text and len(text.split()) > 5:
                    content.append(text)
        if content:
            return "\n\n".join(content)
        # Fallback: Extract the first few meaningful paragraphs
        for p in soup.find_all('p', limit=3):
            text = p.get_text(strip=True)
            if text and len(text.split()) > 5:
                content.append(text)
        if content:
            return "\n\n".join(content)
        return "Sorry, I couldn’t find specific information about this section."

    elif intent == 'contact':
        # Look for contact information in the footer or contact section
        contact_info = []
        footer = soup.find('footer') or soup.find('div', class_=lambda x: x and 'contact' in x.lower())
        if footer:
            for elem in footer.find_all(['p', 'div'], string=lambda text: text and any(keyword in text.lower() for keyword in ['phone', 'email', 'address'])):
                text = elem.get_text(strip=True)
                if text:
                    contact_info.append(text)
        if contact_info:
            return "\n".join(contact_info)
        return "Sorry, I couldn’t find contact information on the website."

    else:
        # Default: Extract a general description
        content = []
        for p in soup.find_all('p', limit=3):
            text = p.get_text(strip=True)
            if text and len(text.split()) > 5:
                content.append(text)
        if content:
            return "\n\n".join(content)
        return "Sorry, I couldn’t find specific information about this section."