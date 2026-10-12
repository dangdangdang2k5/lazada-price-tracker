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
    Return a stable product URL without volatile Lazada share/tracking tokens.

    Product identity (including a selected SKU) is encoded in the path as
    ``-i<item>-s<sku>.html``. Query parameters such as ``laz_token`` and
    ``exlaz`` belong to a share link and can expire or cause a redirect to a
    login/challenge page when reused by a crawler.
    """
    if not url or not isinstance(url, str):
        return ""
    url = url.strip().rstrip(".")
    try:
        parsed = urlparse(url)
        # A short URL cannot be canonicalised until the redirect bridge is
        # fetched, so preserve it for the resolver in the provider.
        if "s.lazada" in parsed.netloc:
            return url
        # Full PDP URLs work from their pathname alone. Drop every query key,
        # rather than maintaining an unreliable allow/deny list of changing
        # Lazada share parameters.
        return urlunparse((parsed.scheme or "https", parsed.netloc, parsed.path, "", "", ""))
    except Exception:
        return url

