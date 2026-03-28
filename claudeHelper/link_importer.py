"""
Link Importer Module for NotiFly
Scrapes bio link pages (Linktree, etc.) and extracts social/content links
"""
import re
import urllib.request
import urllib.error
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

class LinkExtractor(HTMLParser):
    """Custom HTML parser to extract links from bio pages"""
    
    def __init__(self):
        super().__init__()
        self.links = []
        self.current_link = None
        self.capture_text = False
        
        self.blacklist = [
            'login', 'signup', 'sign up', 'sign in', 'register',
            'cookie', 'privacy', 'terms', 'about us', 'contact',
            'help', 'support', 'faq', 'blog', 'careers',
            'download', 'get the app', 'app store', 'google play',
            'share', 'report', 'advertise', 'press'
        ]
    
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            attrs_dict = dict(attrs)
            href = attrs_dict.get('href', '')
            
            if href and not href.startswith('#'):
                self.current_link = {
                    'url': href,
                    'label': attrs_dict.get('title', ''),
                    'aria_label': attrs_dict.get('aria-label', '')
                }
                self.capture_text = True
    
    def handle_data(self, data):
        if self.capture_text and self.current_link:
            text = data.strip()
            if text and not self.current_link.get('text'):
                self.current_link['text'] = text
    
    def handle_endtag(self, tag):
        if tag == 'a' and self.current_link:
            self.capture_text = False
            
            label = (
                self.current_link.get('text') or
                self.current_link.get('aria_label') or
                self.current_link.get('label') or
                'Link'
            ).strip()
            
            url = self.current_link['url']
            
            if not self._is_system_link(label, url):
                self.links.append({
                    'label': label[:100],
                    'url': url
                })
            
            self.current_link = None
    
    def _is_system_link(self, label, url):
        label_lower = label.lower()
        url_lower = url.lower()
        
        for term in self.blacklist:
            if term in label_lower or term in url_lower:
                return True
        
        if url.startswith(('javascript:', 'mailto:', 'tel:')):
            return True
        
        if url.startswith('#'):
            return True
        
        if len(label) < 2:
            return True
        
        return False


def fetch_links(url, timeout=10):
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status != 200:
                return {'success': False, 'links': [], 'msg': f'HTTP {response.status} error'}
            
            html = response.read().decode('utf-8', errors='ignore')
        
        parser = LinkExtractor()
        parser.feed(html)
        
        processed_links = []
        seen_urls = set()
        
        for link in parser.links:
            absolute_url = urljoin(base_url, link['url'])
            
            if absolute_url in seen_urls:
                continue
            seen_urls.add(absolute_url)
            
            link_domain = urlparse(absolute_url).netloc
            if link_domain and link_domain != parsed.netloc:
                processed_links.append({
                    'label': link['label'],
                    'url': absolute_url
                })
        
        if not processed_links:
            return {'success': False, 'links': [], 'msg': 'No external links found on this page'}
        
        return {'success': True, 'links': processed_links, 'msg': f'Found {len(processed_links)} links'}
    
    except urllib.error.HTTPError as e:
        return {'success': False, 'links': [], 'msg': f'HTTP Error: {e.code} - {e.reason}'}
    except urllib.error.URLError as e:
        return {'success': False, 'links': [], 'msg': f'Connection Error: {str(e.reason)}'}
    except Exception as e:
        return {'success': False, 'links': [], 'msg': f'Error: {str(e)}'}


def get_existing_urls(db_conn, handle):
    cursor = db_conn.cursor()
    cursor.execute("SELECT url FROM links WHERE handle = ?", (handle,))
    return {row['url'] for row in cursor.fetchall()}


def channel_exists(db_conn, handle):
    cursor = db_conn.cursor()
    cursor.execute("SELECT 1 FROM channels WHERE handle = ?", (handle,))
    return cursor.fetchone() is not None


def toggle_link(db_conn, handle, label, url, enabled):
    cursor = db_conn.cursor()
    
    try:
        if enabled:
            if not channel_exists(db_conn, handle):
                return {
                    'success': False,
                    'msg': 'Channel does not exist. Create channel before adding links.'
                }
            
            cursor.execute(
                "INSERT INTO links (handle, label, url) VALUES (?, ?, ?)",
                (handle, label, url)
            )
            db_conn.commit()
            return {'success': True, 'msg': 'Link added'}
        else:
            cursor.execute(
                "DELETE FROM links WHERE handle = ? AND url = ?",
                (handle, url)
            )
            db_conn.commit()
            return {'success': True, 'msg': 'Link removed'}
    except Exception as e:
        db_conn.rollback()
        return {'success': False, 'msg': str(e)}
