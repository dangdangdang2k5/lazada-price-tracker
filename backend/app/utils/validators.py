import re
from typing import Optional, Tuple
from urllib.parse import parse_qs, urlparse, urlunparse


def is_valid_lazada_url(url: str) -> bool:
    """
    Validate if a URL is a valid Lazada product URL.
    Examples:
        https://www.lazada.vn/products/chuot-gaming-logitech-g-pro-x-i12345678-s87654321.html
        https://www.lazada.vn//products/i3276673627-s15829337083.html
        https://s.lazada.vn/s.xxxx
        https://lazada.vn/products/...
    """
    if not url or not isinstance(url, str):
        return False

    # Clean double slashes in path before parsing
    clean_url = re.sub(r"(?<!:)//+", "/", url.strip())
    try:
        parsed = urlparse(clean_url)
        if not parsed.scheme or not parsed.netloc:
            return False

        # Support domains: lazada.vn, www.lazada.vn, s.lazada.vn, lazada.co.th, lazada.com.ph, lazada.sg, lazada.com.my, lazada.co.id
        domain_pattern = r"(?:[a-zA-Z0-9-]+\.)?lazada\.(vn|co\.th|com\.ph|sg|com\.my|co\.id)"
        if not re.search(domain_pattern, parsed.netloc, re.IGNORECASE):
            return False

        # Check path or query for products indicator or itemId indicator
        if (
            "products" in parsed.path
            or parsed.netloc.startswith("s.lazada")
            or re.search(r"(?:[?&/_-]i|^i)\d+", clean_url)
        ):
            return True

        # If it's a valid domain with some path, accept it
        return len(parsed.path) > 1
    except Exception:
        return False


def normalize_lazada_url(url: str) -> str:
    """
    Return a stable product URL without volatile Lazada share/tracking tokens,
    while normalizing consecutive slashes (//products -> /products).

    Product identity (including a selected SKU) is encoded in the path as
    ``-i<item>-s<sku>.html`` or ``/i<item>-s<sku>.html``. Query parameters such
    as ``laz_token`` and ``exlaz`` belong to a share link and can expire.
    """
    if not url or not isinstance(url, str):
        return ""
    clean_url = re.sub(r"(?<!:)//+", "/", url.strip().rstrip("."))
    try:
        parsed = urlparse(clean_url)
        # A short URL cannot be canonicalised until the redirect bridge is
        # fetched, so preserve it for the resolver in the provider.
        if "s.lazada" in parsed.netloc:
            return clean_url

        # Clean multiple slashes inside the pathname as well
        clean_path = re.sub(r"/+", "/", parsed.path)

        # Full PDP URLs work from their pathname alone. Drop query keys
        return urlunparse((parsed.scheme or "https", parsed.netloc, clean_path, "", "", ""))
    except Exception:
        return clean_url


def extract_item_and_sku_id(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract itemId and skuId from any Lazada product URL format.
    Handles:
        - Slug URLs: .../product-name-i3300646509-s16055633476.html
        - Slugless URLs: ...//products/i3276673627-s15829337083.html
        - Query param URLs: .../products/?itemId=3276673627&skuId=15829337083
        - Separator variants: .../item_i3276673627_s15829337083.html
    """
    if not url or not isinstance(url, str):
        return None, None

    clean_url = re.sub(r"(?<!:)//+", "/", url.strip())

    item_id: Optional[str] = None
    sku_id: Optional[str] = None

    # 1. Regex matching for itemId: (?:[?&/_-]i|^i)(\d+)
    m_item = re.search(r"(?:[?&/_-]i|^i)(\d+)", clean_url)
    if m_item:
        item_id = m_item.group(1)

    # 2. Regex matching for skuId: (?:[?&/_-]s|^s)(\d+)
    m_sku = re.search(r"(?:[?&/_-]s|^s)(\d+)", clean_url)
    if m_sku:
        sku_id = m_sku.group(1)

    # 3. Query param fallback (?itemId=...&skuId=...)
    if not item_id or not sku_id:
        try:
            parsed = urlparse(clean_url)
            params = parse_qs(parsed.query)
            if not item_id and "itemId" in params and params["itemId"]:
                item_id = params["itemId"][0]
            if not sku_id and "skuId" in params and params["skuId"]:
                sku_id = params["skuId"][0]
        except Exception:
            pass

    return item_id, sku_id
