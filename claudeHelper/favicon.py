# favicon.py - Handles link icon generation and styling
from urllib.parse import urlparse

def get_css():
    """Returns CSS to style the link button for flexbox alignment."""
    return """
    .link-btn {
        display: flex !important;
        align-items: center;
        justify-content: center;
        gap: 12px;
        position: relative;
        overflow: hidden;
    }
    .link-icon {
        width: 24px;
        height: 24px;
        border-radius: 4px;
        object-fit: contain;
        flex-shrink: 0;
    }
    /* Adjustment for text inside the button to ensure it doesn't shift weirdly */
    .link-btn span {
        text-align: center;
    }
    """

def get_icon_html(url):
    """Generates the <img> tag for the favicon based on the URL domain."""
    try:
        if not url: 
            return ""
            
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Handle cases where user might not type http://
        if not domain:
            domain = parsed.path.split('/')[0]
        
        # Strip common junk if necessary, but usually netloc is enough
        if not domain: 
            return ""

        # Google's S2 service is reliable and free
        icon_url = f"https://www.google.com/s2/favicons?sz=64&domain={domain}"
        
        # onerror hides the image if the API fails or site has no icon
        return f'<img src="{icon_url}" class="link-icon" onerror="this.style.display=\'none\'">'
    except Exception:
        return ""
