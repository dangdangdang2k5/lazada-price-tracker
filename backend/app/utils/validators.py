import re
from urllib.parse import urlparse, urlunparse


def is_valid_lazada_url(url: str) -> bool:
    """
    Validate if a URL is a valid Lazada product URL.
    Examples:
        https://www.lazada.vn/products/chuot-gaming-logitech-g-pro-x-i12345678-s87654321.html
        https://s.lazada.vn/s.xxxx
        https://lazada.vn/products/...
    """
    if not url or not isinstance(url, str):
        return False

    url = url.strip()
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False

        # Support domains: lazada.vn, www.lazada.vn, s.lazada.vn, lazada.co.th, lazada.com.ph, lazada.sg, lazada.com.my, lazada.co.id
        domain_pattern = r"(?:[a-zA-Z0-9-]+\.)?lazada\.(vn|co\.th|com\.ph|sg|com\.my|co\.id)"
        if not re.search(domain_pattern, parsed.netloc, re.IGNORECASE):
            return False

        # Check path or query
        if "products" in parsed.path or parsed.netloc.startswith("s.lazada") or re.search(r"-i\d+", parsed.path):
            return True
        
        # If it's a valid domain with some path, accept it
        return len(parsed.path) > 1
    except Exception:
        return False


def normalize_lazada_url(url: str) -> str:
    """
    Clean tracking queries (e.g., spm, search, clickTrackInfo) from Lazada URL to keep it canonical.
    """
    if not url or not isinstance(url, str):
        return ""
    url = url.strip().rstrip(".")
    try:
        parsed = urlparse(url)
        # For short link domain s.lazada.vn, preserve full URL including query params
        if "s.lazada" in parsed.netloc:
            return url
        # Keep scheme, netloc, path, and discard tracking queries unless needed
        return urlunparse((parsed.scheme or "https", parsed.netloc, parsed.path, "", "", ""))
    except Exception:
        return url

