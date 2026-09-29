import json
import re
from typing import Optional, Dict, Any, List
import httpx
from bs4 import BeautifulSoup
from app.core.logging import logger
from app.services.providers.base import BasePriceProvider, ProductScrapedData
from app.utils.currency import parse_currency
from app.utils.validators import is_valid_lazada_url, normalize_lazada_url

# Standard user agents to avoid trivial blocks
USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
]


class LazadaPriceProvider(BasePriceProvider):
    """
    Price provider implementation for Lazada e-commerce platform.
    Uses multi-strategy extraction (JSON-LD, Embedded page configs, Meta tags, and fallback Regex).
    """

    def __init__(self, timeout_seconds: float = 15.0, retries: int = 2):
        self.timeout = timeout_seconds
        self.retries = retries

    async def get_product_info(self, url: str) -> ProductScrapedData:
        canonical_url = normalize_lazada_url(url)
        if not is_valid_lazada_url(canonical_url):
            return ProductScrapedData(
                name="Unknown Product",
                price=0,
                url=canonical_url,
                success=False,
                error_message="Invalid or unsupported Lazada product URL"
            )

        html_content = await self._fetch_html(canonical_url)
        if not html_content:
            return ProductScrapedData(
                name="Unknown Product",
                price=0,
                url=canonical_url,
                success=False,
                error_message="Failed to fetch product page (timeout or network error)"
            )

        # Handle Lazada short links (s.lazada.vn share bridge pages)
        target_url_match = (
            re.search(r'<link\s+rel=["\']origin["\']\s+href=["\']([^"\']+)["\']', html_content, re.IGNORECASE) or
            re.search(r'var\s+REDIRECTURL\s*=\s*new\s+URL\s*\(\s*["\']([^"\']+)["\']\s*\)', html_content) or
            re.search(r'<link\s+rel=["\']canonical["\']\s+href=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
        )
        if target_url_match and "products" in target_url_match.group(1):
            extracted_target = target_url_match.group(1)
            target_canonical = normalize_lazada_url(extracted_target)
            logger.info(f"[CRAWLER] Short link resolved: {canonical_url} -> {target_canonical}")
            canonical_url = target_canonical
            target_html = await self._fetch_html(canonical_url)
            if target_html:
                html_content = target_html

        # Check for Lazada anti-bot / captcha challenge page
        if any(k in html_content.lower() for k in ["sec.lazada.vn", "punishpage", "x5step", "rgv5c_act", "captcha"]):
            logger.warning(f"[CRAWLER] Lazada anti-bot challenge detected for: {canonical_url}")
            return ProductScrapedData(
                name="Sản phẩm Lazada (Bị Anti-Bot chặn)",
                price=0,
                url=canonical_url,
                success=False,
                error_message="Lazada đã kích hoạt cơ chế Anti-Bot/Captcha. Không thể cào dữ liệu giá trực tiếp."
            )

        data = self._parse_html(html_content, canonical_url)
        if not data or data.price <= 0:
            logger.warning(f"[CRAWLER] Could not extract valid price for: {canonical_url}")
            return ProductScrapedData(
                name=data.name if data and data.name else "Lazada Product",
                price=0,
                image_url=data.image_url if data else None,
                url=canonical_url,
                success=False,
                error_message="Unable to parse product price from Lazada page"
            )

        return data

    async def _fetch_html(self, url: str) -> Optional[str]:
        headers = {
            "User-Agent": USER_AGENTS[0],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Sec-Ch-Ua": '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }

        async with httpx.AsyncClient(follow_redirects=True, timeout=self.timeout) as client:
            for attempt in range(1, self.retries + 1):
                try:
                    headers["User-Agent"] = USER_AGENTS[attempt % len(USER_AGENTS)]
                    response = await client.get(url, headers=headers)
                    if response.status_code == 200 and response.text:
                        return response.text
                    else:
                        logger.warning(f"[CRAWLER] Attempt {attempt} returned status {response.status_code} for {url}")
                except Exception as e:
                    logger.warning(f"[CRAWLER] Attempt {attempt} failed for {url}: {str(e)}")
        return None

    def _parse_html(self, html: str, url: str) -> Optional[ProductScrapedData]:
        soup = BeautifulSoup(html, "html.parser")
        
        name: Optional[str] = None
        price: Optional[int] = None
        original_price: Optional[int] = None
        image_url: Optional[str] = None

        # Strategy 1: JSON-LD structured data (<script type="application/ld+json">)
        ld_json_scripts = soup.find_all("script", type="application/ld+json")
        for script in ld_json_scripts:
            try:
                if not script.string:
                    continue
                ld_data = json.loads(script.string.strip())
                if isinstance(ld_data, list):
                    items = ld_data
                else:
                    items = [ld_data]

                for item in items:
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        name = name or item.get("name")
                        image_url = image_url or (item.get("image")[0] if isinstance(item.get("image"), list) else item.get("image"))
                        offers = item.get("offers")
                        if isinstance(offers, dict):
                            p = offers.get("price") or offers.get("lowPrice")
                            if p:
                                price = parse_currency(str(p))
                        elif isinstance(offers, list) and len(offers) > 0:
                            p = offers[0].get("price") or offers[0].get("lowPrice")
                            if p:
                                price = parse_currency(str(p))
            except Exception:
                pass

        # Strategy 2: Extract from Lazada window.__INIT_DATA__ / app state in script tags
        scripts = soup.find_all("script")
        for script in scripts:
            script_text = script.string or ""
            if any(k in script_text for k in ["__INIT_DATA__", "app.config", "pdpData", "pageData", "pdpImpression", "skuInfos"]):
                # Look for price in embedded JSON object
                if not price:
                    price_patterns = [
                        r'"salePrice"\s*:\s*\{\s*"value"\s*:\s*([\d\.]+)',
                        r'"price"\s*:\s*\{\s*"value"\s*:\s*([\d\.]+)',
                        r'"salePrice"\s*:\s*"?([0-9.,]+)"?',
                        r'"price"\s*:\s*"?([0-9.,]+)"?',
                        r'"discountPrice"\s*:\s*"?([0-9.,]+)"?',
                        r'"priceShow"\s*:\s*"₫?\s*([0-9.,]+)"',
                        r'"priceText"\s*:\s*"₫?\s*([0-9.,]+)"',
                    ]
                    for pat in price_patterns:
                        m = re.search(pat, script_text)
                        if m:
                            parsed = parse_currency(m.group(1))
                            if parsed and parsed > 1000:
                                price = parsed
                                break

                if not original_price:
                    orig_patterns = [
                        r'"originalPrice"\s*:\s*\{\s*"value"\s*:\s*([\d\.]+)',
                        r'"originalPrice"\s*:\s*"?([0-9.,]+)"?',
                        r'"wasPrice"\s*:\s*"?([0-9.,]+)"?',
                    ]
                    for pat in orig_patterns:
                        m = re.search(pat, script_text)
                        if m:
                            parsed = parse_currency(m.group(1))
                            if parsed and parsed > 1000:
                                original_price = parsed
                                break

                # Also look for title / name
                title_match = re.search(r'"title"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', script_text)
                if not name and title_match:
                    try:
                        name = json.loads(f'"{title_match.group(1)}"')
                    except Exception:
                        name = title_match.group(1)

                # Look for image
                image_match = re.search(r'"image"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', script_text)
                if not image_url and image_match:
                    image_url = image_match.group(1)

        # Strategy 2.5: Extract from pdpTrackingData / dataLayer tracking scripts
        if not price or not name or not image_url:
            pdt_price_match = re.search(r'pdt_price(?:\\*)["\']\s*:\s*(?:\\*)["\']([^\\"\']*)', html)
            if not price and pdt_price_match:
                price = parse_currency(pdt_price_match.group(1))

            pdt_name_match = re.search(r'pdt_name(?:\\*)["\']\s*:\s*(?:\\*)["\']([^\\"\']*)', html)
            if not name and pdt_name_match:
                name = pdt_name_match.group(1).strip()

            pdt_photo_match = re.search(r'pdt_photo(?:\\*)["\']\s*:\s*(?:\\*)["\']([^\\"\']*)', html)
            if not image_url and pdt_photo_match:
                image_url = pdt_photo_match.group(1).strip()

        # Strategy 3: Meta tags OpenGraph / Twitter Cards
        if not name:
            og_title = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "twitter:title"})
            if og_title and og_title.get("content"):
                name = og_title["content"]
            elif soup.title and soup.title.string:
                name = soup.title.string.strip()

        if not image_url:
            og_image = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
            if og_image and og_image.get("content"):
                image_url = og_image["content"]

        if not price:
            og_price = soup.find("meta", property="product:price:amount") or soup.find("meta", property="og:price:amount") or soup.find("meta", attrs={"name": "twitter:data1"})
            if og_price and og_price.get("content"):
                price = parse_currency(og_price["content"])

        # Strategy 4: Fallback Regex on entire raw HTML
        if not price:
            patterns = [
                r'class="[^"]*pdp-price[^"]*"[^>]*>([0-9.,\s₫VND]+)<',
                r'class="[^"]*pdp-v2-price[^"]*"[^>]*>([0-9.,\s₫VND]+)<',
                r'itemprop="price"[^>]*content="([^"]+)"',
                r'itemprop="price"[^>]*>([0-9.,\s₫VND]+)<',
                r'"price"\s*:\s*"?([0-9.,]+)"?',
                r'"lowPrice"\s*:\s*"?([0-9.,]+)"?',
                r'"salePrice"\s*:\s*"([0-9.,\s₫]+)"',
            ]
            for pattern in patterns:
                match = re.search(pattern, html)
                if match:
                    parsed = parse_currency(match.group(1))
                    if parsed and parsed > 1000:  # Typical VND price > 1000
                        price = parsed
                        break

        # If name is still missing, fallback to readable title from URL slug
        if not name:
            slug = url.split("/")[-1].replace(".html", "").replace("-i", " ")
            name = slug.replace("-", " ").title()

        if not price:
            return None

        # Fix relative image URLs
        if image_url and image_url.startswith("//"):
            image_url = "https:" + image_url

        return ProductScrapedData(
            name=name.strip() if name else "Lazada Product",
            price=price,
            original_price=original_price if (original_price and original_price > price) else None,
            image_url=image_url,
            url=url,
            success=True
        )
