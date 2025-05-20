import sqlite3
import logging

logging.basicConfig(level=logging.DEBUG)

def init_db():
    """Initialize the SQLite database for contact info only."""
    try:
        conn = sqlite3.connect('website_map.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS website_content (
                page_title TEXT,
                url TEXT,
                tag TEXT,
                content TEXT,
                PRIMARY KEY (page_title, tag, content)
            )
        ''')
        conn.commit()
        logging.debug("Database initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"Error initializing database: {e}")
        raise
    finally:
        conn.close()

def store_contact_info(content):
    """Store contact info in the database."""
    try:
        conn = sqlite3.connect('website_map.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO website_content (page_title, url, tag, content) VALUES (?, ?, ?, ?)",
            ('contact us', 'https://stolmeierlaw.com/', 'p', content)
        )
        conn.commit()
        logging.debug("Stored contact info.")
    except sqlite3.Error as e:
        logging.error(f"Error storing contact info: {e}")
        raise
    finally:
        conn.close()

def get_contact_info():
    """Retrieve contact information from the database."""
    try:
        conn = sqlite3.connect('website_map.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT content FROM website_content WHERE page_title = ? AND content LIKE '%contact%' OR content LIKE '%phone%' OR content LIKE '%email%' OR content LIKE '%address%'",
            ('contact us',)
        )
        contact_text = ' '.join([row[0] for row in cursor.fetchall()])
        return contact_text if contact_text else None
    except sqlite3.Error as e:
        logging.error(f"Error retrieving contact info: {e}")
        return None
    finally:
        conn.close()