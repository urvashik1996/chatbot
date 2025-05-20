import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from thefuzz import fuzz, process
import logging
from scraper import fetch_page

# Download NLTK data with error handling
try:
    nltk.download('punkt', quiet=True)
    nltk.download('wordnet', quiet=True)
except Exception as e:
    logging.error(f"Error downloading NLTK data: {e}")
    raise

logging.basicConfig(level=logging.DEBUG)

lemmatizer = WordNetLemmatizer()

def extract_keywords_and_intent(user_message, session_id, website_map, user_sessions):
    """Extract keywords and intent from the user's message using NLTK."""
    logging.debug(f"Processing user message: {user_message}")
    
    # Tokenize and lemmatize with error handling
    try:
        tokens = word_tokenize(user_message.lower())
    except Exception as e:
        logging.error(f"Tokenization failed for message '{user_message}': {e}")
        tokens = user_message.lower().split()  # Fallback to basic splitting
    
    try:
        tokens = [lemmatizer.lemmatize(token) for token in tokens]
    except Exception as e:
        logging.error(f"Lemmatization failed: {e}")
        # Proceed with original tokens if lemmatization fails
    
    # Preserve phrases like "car accidents" by checking for known multi-word terms
    known_terms = list(website_map.keys())
    if 'practice areas' in website_map:
        known_terms.extend(list(website_map['practice areas']['subcategories'].keys()))
    known_terms.extend(['firm', 'history', 'fees', 'attorneys'])
    
    # Combine tokens into potential phrases
    keywords = []
    i = 0
    while i < len(tokens):
        # Check for two-word phrases
        if i + 1 < len(tokens):
            two_word_phrase = f"{tokens[i]} {tokens[i+1]}"
            best_match = process.extractOne(two_word_phrase, known_terms, scorer=fuzz.token_sort_ratio)
            if best_match and best_match[1] > 85:
                keywords.append(best_match[0])
                logging.debug(f"Matched phrase '{two_word_phrase}' to '{best_match[0]}' (score: {best_match[1]})")
                i += 2
                continue
        # Check single word
        best_match = process.extractOne(tokens[i], known_terms, scorer=fuzz.token_sort_ratio)
        if best_match and best_match[1] > 80:
            keywords.append(best_match[0])
            logging.debug(f"Matched token '{tokens[i]}' to '{best_match[0]}' (score: {best_match[1]})")
        else:
            keywords.append(tokens[i])
        i += 1
    
    # Remove common words
    common_words = {'what', 'are', 'the', 'of', 'about', 'tell', 'me', 'i', 'want', 'to', 'know', 'on', 'in', 'a', 'an', 'is', 'for'}
    keywords = [word for word in keywords if word not in common_words]
    
    # Determine intent
    intent_keywords = {
        'causes': ['cause', 'reason', 'why', 'factor'],
        'description': ['about', 'tell', 'describe', 'information'],
        'contact': ['contact', 'phone', 'email', 'address'],
        'fees': ['fee', 'cost', 'price']
    }
    intent = 'description'
    for intent_name, keywords_list in intent_keywords.items():
        if any(keyword in user_message.lower() for keyword in keywords_list):
            intent = intent_name
            break
    
    if session_id in user_sessions:
        previous_keywords = user_sessions[session_id].get('keywords', [])
        previous_intent = user_sessions[session_id].get('intent', 'description')
        if not keywords and previous_keywords:
            keywords.extend(previous_keywords)
        if intent == 'description' and previous_intent != 'description':
            intent = previous_intent
    
    user_sessions[session_id] = {'keywords': keywords, 'intent': intent}
    
    logging.debug(f"Extracted keywords: {keywords}, Intent: {intent}")
    return keywords, intent

def scrape_targeted_content(keywords, intent, session_id, url, website_map, user_sessions):
    """Scrape content from the specified URL immediately, matching the given keywords and intent."""
    logging.debug(f"Scraping targeted content for keywords: {keywords}, intent: {intent}, URL: {url}")
    
    # Adjust keywords based on intent
    search_keywords = keywords.copy()
    if intent == 'causes':
        search_keywords.extend(['reason', 'factors', 'why', 'cause', 'causes'])
    
    # Scrape the content immediately from the provided URL
    soup = fetch_page(url)
    if not soup:
        logging.error(f"Failed to scrape content from {url}")
        return f"Sorry, I couldn't fetch the content for {' '.join(keywords)}."
    
    # Search a broader range of tags to ensure content isn't missed
    elements = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'section', 'article', 'ul', 'ol', 'span'])
    content = []
    for elem in elements:
        text = ''
        if elem.name in ['ul', 'ol']:
            list_items = elem.find_all('li')
            text = ' • '.join([item.get_text(strip=True) for item in list_items if item.get_text(strip=True)])
        else:
            text = elem.get_text(strip=True)
        if text:
            content.append((elem.name, text))
    
    # Search for matching content
    best_match_content = []
    found_content = False
    
    if content:
        logging.debug(f"Searching scraped content for keywords: {search_keywords}")
        i = 0
        while i < len(content):
            tag, text = content[i]
            text_lower = text.lower()
            # Check for keyword matches (relaxed for intent)
            matches = sum(1 for keyword in search_keywords if keyword.lower() in text_lower)
            if matches > 0 or (intent == 'description' and any(keyword in text_lower for keyword in keywords)):
                logging.debug(f"Found matching element: {text[:100]}...")
                if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    section_content = [text]
                    i += 1
                    while i < len(content) and content[i][0] not in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                        sub_tag, sub_text = content[i]
                        if sub_tag in ['ul', 'ol']:
                            list_items = [item.strip() for item in sub_text.split('•') if item.strip()]
                            for item in list_items:
                                section_content.append(f"- {item}")
                        else:
                            section_content.append(sub_text)
                        i += 1
                    best_match_content.extend(section_content)
                elif tag in ['p', 'div', 'section', 'article', 'span']:
                    best_match_content.append(text)
                    i += 1
                elif tag in ['ul', 'ol']:
                    list_items = [item.strip() for item in text.split('•') if item.strip()]
                    for item in list_items:
                        best_match_content.append(f"- {item}")
                    i += 1
                else:
                    i += 1
                found_content = True
            else:
                i += 1
    
    # Fallback: If no exact match, include some general content for the description intent
    if not found_content and intent == 'description':
        logging.debug("No exact match found, including general content as fallback.")
        i = 0
        while i < len(content) and len(best_match_content) < 3:  # Limit to 3 elements
            tag, text = content[i]
            if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']:
                best_match_content.append(text)
                found_content = True
            i += 1
    
    if not found_content:
        logging.warning(f"No content found matching keywords: {search_keywords}")
        return f"Sorry, I couldn't find specific information about {' '.join(keywords)}. Could you rephrase your request?"
    
    response_header = f"Here are some details about {' '.join(keywords)} I found on the website:\n"
    formatted_response = response_header + '\n'.join(best_match_content[:10])
    if len(best_match_content) > 10:
        formatted_response += "\n... (more content available on the website)"
    
    formatted_response += "\n\nWas this helpful? (Reply 'yes' or 'no')"
    
    logging.debug(f"Formatted response: {formatted_response[:200]}...")
    return formatted_response