from flask import Flask, request, jsonify, render_template
import logging
from scraper import build_website_map, scrape_contact_info_fallback
from nlp import extract_keywords_and_intent, scrape_targeted_content
from database import init_db, get_contact_info, store_contact_info
from thefuzz import fuzz, process  # Added fuzz import

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

# Global variables
website_map = {}
user_sessions = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/welcome', methods=['GET'])
def welcome():
    """Return welcome message and navigation items (structure only, no scraping)."""
    global website_map
    website_map = build_website_map()
    if not website_map:
        logging.error("Failed to build website map.")
        return jsonify({'message': 'Sorry, I couldn’t load the website sections.', 'nav_items': []})

    nav_items = [
        {
            'title': title.capitalize(),
            'url': data['url'],
            'subcategories': [
                {'title': sub_title.capitalize(), 'url': sub_data['url']}
                for sub_title, sub_data in data['subcategories'].items()
            ] if title.lower() == 'practice areas' else []
        }
        for title, data in website_map.items()
    ]

    welcome_data = {
        'message': 'How can I help you? Explore these sections from Stolmeier Law:',
        'nav_items': nav_items
    }
    return jsonify(welcome_data)

@app.route('/scrape_page', methods=['POST'])
def scrape_page_endpoint():
    """Scrape a specific page on-demand and return its targeted content."""
    data = request.json
    url = data.get('url', '')
    session_id = data.get('session_id', 'default')
    if not url:
        return jsonify({'response': 'No URL provided to scrape.'})

    global website_map
    if not website_map:
        website_map = build_website_map()
        if not website_map:
            return jsonify({'response': 'Sorry, I couldn’t access the website to process your request.'})

    # Find the page title or subcategory title corresponding to the URL
    keywords = []
    found = False

    # Check main pages
    for page_title, page_data in website_map.items():
        if page_data['url'] == url:
            keywords = [page_title]
            found = True
            break

    # Check subcategories
    if not found and 'practice areas' in website_map:
        for sub_title, sub_data in website_map['practice areas']['subcategories'].items():
            if sub_data['url'] == url:
                keywords = [sub_title]
                found = True
                break

    if not found:
        return jsonify({'response': 'Sorry, I couldn’t find the requested section.'})

    # Scrape the content immediately for the requested URL
    response = scrape_targeted_content(keywords, 'description', session_id, url, website_map, user_sessions)
    return jsonify({'response': response})

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    session_id = data.get('session_id', 'default')
    if not user_message:
        return jsonify({'response': 'Please provide a message.'})

    global website_map
    if not website_map:
        website_map = build_website_map()
        if not website_map:
            return jsonify({'response': 'Sorry, I couldn’t access the website to process your request.'})

    if any(keyword in user_message.lower() for keyword in ['contact', 'phone', 'email', 'address']):
        contact_text = get_contact_info()
        if contact_text:
            return jsonify({'response': contact_text})
        contact_text = scrape_contact_info_fallback()
        store_contact_info(contact_text)
        return jsonify({'response': contact_text})

    if user_message.lower() in ['yes', 'no']:
        feedback = user_message.lower()
        logging.debug(f"User feedback for session {session_id}: {feedback}")
        return jsonify({'response': 'Thank you for your feedback! How can I assist you further?'})

    keywords, intent = extract_keywords_and_intent(user_message, session_id, website_map, user_sessions)
    if not keywords:
        return jsonify({'response': "Sorry, I couldn't understand your request. Could you provide more details?"})

    # Find the URL corresponding to the keywords
    url = None
    for keyword in keywords:
        keyword_lower = keyword.lower()
        if keyword_lower in website_map:
            url = website_map[keyword_lower]['url']
            break
        if 'practice areas' in website_map:
            for sub_title in website_map['practice areas']['subcategories']:
                if keyword_lower == sub_title:
                    url = website_map['practice areas']['subcategories'][sub_title]['url']
                    break

    if not url:
        # Try fuzzy matching for keywords
        all_sections = list(website_map.keys())
        if 'practice areas' in website_map:
            all_sections.extend(list(website_map['practice areas']['subcategories'].keys()))
        for keyword in keywords:
            best_match = process.extractOne(keyword, all_sections, scorer=fuzz.token_sort_ratio)
            if best_match and best_match[1] > 85:
                matched_section = best_match[0]
                if matched_section in website_map:
                    url = website_map[matched_section]['url']
                    break
                if 'practice areas' in website_map and matched_section in website_map['practice areas']['subcategories']:
                    url = website_map['practice areas']['subcategories'][matched_section]['url']
                    break

    if not url:
        logging.debug(f"No URL found for keywords: {keywords}")
        return jsonify({'response': "Sorry, I couldn't find the requested section."})

    response = scrape_targeted_content(keywords, intent, session_id, url, website_map, user_sessions)
    return jsonify({'response': response})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)