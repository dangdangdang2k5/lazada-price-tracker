import json
import re
import asyncio
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

        target_url = canonical_url

        # If it's a Lazada short link (s.lazada.vn), resolve it to the full authenticated product URL with laz_token
        if "s.lazada" in canonical_url:
            short_html = await self._fetch_html(canonical_url)
            if short_html:
                target_url_match = (
                    re.search(r'var\s+REDIRECTURL\s*=\s*new\s+URL\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', short_html) or
                    re.search(r'<link\s+rel=[\'"]origin[\'"]\s+href=[\'"]([^\'"]+)[\'"]', short_html, re.IGNORECASE) or
                    re.search(r'<link\s+rel=[\'"]canonical[\'"]\s+href=[\'"]([^\'"]+)[\'"]', short_html, re.IGNORECASE)
                )
                if target_url_match and "products" in target_url_match.group(1):
                    target_url = normalize_lazada_url(target_url_match.group(1))
                    logger.info(f"[CRAWLER] Short link resolved: {canonical_url} -> {target_url}")

        # Extract SKU ID from URL (e.g. -s116886611256.html)
        sku_match = re.search(r'-s(\d+)\.html', target_url) or re.search(r'-s(\d+)\.html', url)
        target_sku_id = sku_match.group(1) if sku_match else None

        # Strategy 1: High accuracy Playwright dynamic mtop extraction (captures flash sale & voucher prices)
        try:
            pw_data = await self._fetch_with_playwright(target_url, target_sku_id)
            if pw_data and pw_data.price > 0:
                logger.info(f"[CRAWLER] Successfully extracted real-time sale price via Playwright: {pw_data.price} VND (Original: {pw_data.original_price})")
                return pw_data
        except Exception as pw_err:
            logger.warning(f"[CRAWLER] Playwright dynamic fetch skipped or failed: {pw_err}. Falling back to HTTP HTML parsing.")

        html_content = await self._fetch_html(target_url)
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

        # Strategy 1: Extract from Lazada window.__INIT_DATA__ / pdpData / app state in script tags (Accurate Sale Price)
        scripts = soup.find_all("script")
        for script in scripts:
            script_text = script.string or ""
            if any(k in script_text for k in ["__INIT_DATA__", "app.config", "pdpData", "pageData", "pdpImpression", "skuInfos"]):
                # Look for coupon & salePrice first
                if not price:
                    price_patterns = [
                        r'"coupon"\s*:\s*\{\s*"priceNumber"\s*:\s*([\d\.]+)',
                        r'"salePrice"\s*:\s*\{\s*"value"\s*:\s*([\d\.]+)',
                        r'"discountPrice"\s*:\s*\{\s*"value"\s*:\s*([\d\.]+)',
                        r'"salePrice"\s*:\s*"?([0-9.,]+)"?',
                        r'"discountPrice"\s*:\s*"?([0-9.,]+)"?',
                        r'"priceShow"\s*:\s*"₫?\s*([0-9.,]+)"',
                        r'"priceText"\s*:\s*"₫?\s*([0-9.,]+)"',
                        r'"price"\s*:\s*\{\s*"value"\s*:\s*([\d\.]+)',
                        r'"price"\s*:\s*"?([0-9.,]+)"?',
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

        # Strategy 2: Extract from pdpTrackingData / dataLayer tracking scripts
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

        # Strategy 3: JSON-LD structured data (Fallback)
        if not price:
            ld_json_scripts = soup.find_all("script", type="application/ld+json")
            for script in ld_json_scripts:
                try:
                    if not script.string:
                        continue
                    ld_data = json.loads(script.string.strip())
                    items = ld_data if isinstance(ld_data, list) else [ld_data]
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

    async def _fetch_with_playwright(self, url: str, target_sku_id: Optional[str] = None) -> Optional[ProductScrapedData]:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return None

        # Extract Item ID if present in the URL
        m_item = re.search(r'-i(\d+)', url) or re.search(r'i(\d+)', url)
        item_id = m_item.group(1) if m_item else None

        captured_mtop: Optional[str] = None
        captured_catalog_json: Optional[Dict[str, Any]] = None
        page_title: Optional[str] = None

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-infobars",
                    "--window-size=1366,768"
                ]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                locale="vi-VN",
                viewport={"width": 1366, "height": 768},
            )

            page = await context.new_page()
            captured_list = []
            mtop_event = asyncio.Event()

            async def on_response(response):
                nonlocal captured_catalog_json
                req_url = response.url.lower()
                if "catalog" in req_url and "ajax=true" in req_url:
                    try:
                        data = await response.json()
                        if data and "mods" in data:
                            captured_catalog_json = data
                            mtop_event.set()
                    except Exception:
                        pass
                elif "getdetailinfo" in req_url or ("mtop" in req_url and "detail" in req_url):
                    try:
                        text = await response.text()
                        if "skuInfos" in text or "module" in text:
                            captured_list.append(text)
                            mtop_event.set()
                    except Exception:
                        pass

            page.on("response", on_response)

            # High-priority bypass strategy: Query Lazada Catalog via Item ID
            # This completely avoids Alibaba sufei-punish WAF while delivering accurate sale & promo prices
            if item_id:
                search_url = f"https://www.lazada.vn/catalog/?q={item_id}"
                try:
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
                    try:
                        await asyncio.wait_for(mtop_event.wait(), timeout=6.0)
                    except asyncio.TimeoutError:
                        pass
                except Exception as e:
                    logger.warning(f"[PW] Catalog search error for {item_id}: {e}")

            # If catalog search didn't yield result, try direct PDP navigation
            if not captured_catalog_json and not captured_list:
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    await page.evaluate("window.scrollBy(0, 300)")
                    try:
                        await asyncio.wait_for(mtop_event.wait(), timeout=8.0)
                    except asyncio.TimeoutError:
                        pass
                except Exception:
                    pass

            if captured_list:
                captured_mtop = captured_list[0]

            try:
                page_title = await page.title()
            except Exception:
                pass

            await browser.close()

        # Priority 1: Parse dynamic MTOP if captured
        if captured_mtop:
            parsed = self._parse_mtop_detail(captured_mtop, url, target_sku_id, fallback_title=page_title)
            if parsed and parsed.price > 0:
                logger.info(f"[PW] Dynamic MTOP parsed successfully: {parsed.price} VND (Orig: {parsed.original_price})")
                return parsed

        # Priority 2: Parse Catalog Search AJAX JSON (Resilient & fast)
        if captured_catalog_json:
            mods = captured_catalog_json.get("mods", {})
            list_items = mods.get("listItems", [])
            for it in list_items:
                if not item_id or str(it.get("itemId")) == str(item_id) or len(list_items) == 1:
                    price_val = 0
                    raw_price = it.get("price")
                    if raw_price:
                        try:
                            price_val = int(float(raw_price))
                        except Exception:
                            pass
                    if price_val <= 0 and it.get("priceShow"):
                        price_val = parse_currency(it.get("priceShow")) or 0

                    orig_val = None
                    raw_orig = it.get("originalPrice")
                    if raw_orig:
                        try:
                            orig_val = int(float(raw_orig))
                            if orig_val <= price_val:
                                orig_val = None
                        except Exception:
                            pass

                    if price_val > 0:
                        prod_name = it.get("name") or page_title or "Lazada Product"
                        logger.info(f"[PW] Catalog AJAX parsed successfully: {prod_name[:40]} -> {price_val} VND")
                        return ProductScrapedData(
                            name=prod_name,
                            price=price_val,
                            original_price=orig_val,
                            image_url=it.get("image"),
                            sku_id=target_sku_id,
                            url=url,
                            success=True
                        )

        logger.warning(f"[PW] No dynamic mtop or catalog price captured for {url}")
        return None

    def _parse_mtop_detail(self, mtop_text: str, url: str, target_sku_id: Optional[str], fallback_title: Optional[str] = None) -> Optional[ProductScrapedData]:
        json_match = re.search(r'(\{.*\})', mtop_text, re.DOTALL)
        if not json_match:
            return None

        try:
            data = json.loads(json_match.group(1))
            raw_mod = data.get("data", {}).get("module", "{}")
            mod = json.loads(raw_mod) if isinstance(raw_mod, str) else raw_mod

            # Title
            product_obj = mod.get("product", {})
            name = product_obj.get("title")
            if not name:
                tracking = mod.get("tracking", {})
                name = tracking.get("pdt_name") or fallback_title

            # Clean name
            if name and " | Lazada" in name:
                name = name.split(" | Lazada")[0].strip()

            sku_infos = mod.get("skuInfos", {})
            po = mod.get("productOption", {})
            sku_base = po.get("skuBase", {})

            # Map property vid -> readable variation name
            vid_map = {}
            for prop in sku_base.get("properties", []):
                pid = prop.get("pid")
                for val in prop.get("values", []):
                    vid = str(val.get("vid"))
                    vname = val.get("name")
                    vid_map[f"{pid}:{vid}"] = vname
                    vid_map[vid] = vname

            # Extract all variations
            variations = []
            skus_list = sku_base.get("skus", [])
            
            if skus_list:
                for sku_item in skus_list:
                    sid = str(sku_item.get("skuId"))
                    proppath = sku_item.get("propPath", "")
                    page_path = sku_item.get("pagePath", "")
                    
                    prop_parts = proppath.split(";")
                    names = []
                    for part in prop_parts:
                        if part in vid_map:
                            names.append(vid_map[part])
                        elif ":" in part and part.split(":")[1] in vid_map:
                            names.append(vid_map[part.split(":")[1]])
                    var_name = " / ".join(names) if names else f"Phân loại #{sid}"

                    sinfo = sku_infos.get(sid, {})
                    p_obj = sinfo.get("price", {})
                    coupon = p_obj.get("coupon", {})
                    sale_p = p_obj.get("salePrice", {})
                    orig_p = p_obj.get("originalPrice", {})

                    price = 0
                    if coupon and coupon.get("priceNumber"):
                        price = int(coupon["priceNumber"])
                    elif sale_p and sale_p.get("value"):
                        price = int(sale_p["value"])

                    orig_price = int(orig_p.get("value", 0)) if orig_p else 0
                    img = sinfo.get("image") or sku_item.get("image")
                    full_url = ("https://www.lazada.vn" + page_path) if page_path else url

                    if price > 0:
                        variations.append({
                            "sku_id": sid,
                            "name": var_name,
                            "price": price,
                            "original_price": orig_price if orig_price > price else None,
                            "image": img,
                            "url": full_url
                        })
            else:
                # Fallback: iterate over sku_infos directly
                for sid, sinfo in sku_infos.items():
                    if sid == "0" and len(sku_infos) > 1:
                        continue
                    p_obj = sinfo.get("price", {})
                    coupon = p_obj.get("coupon", {})
                    sale_p = p_obj.get("salePrice", {})
                    orig_p = p_obj.get("originalPrice", {})

                    price = 0
                    if coupon and coupon.get("priceNumber"):
                        price = int(coupon["priceNumber"])
                    elif sale_p and sale_p.get("value"):
                        price = int(sale_p["value"])

                    orig_price = int(orig_p.get("value", 0)) if orig_p else 0
                    img = sinfo.get("image")
                    
                    dlayer = sinfo.get("dataLayer", {})
                    var_name = dlayer.get("sku_name") or f"Phân loại #{sid}"

                    if price > 0:
                        variations.append({
                            "sku_id": str(sid),
                            "name": var_name,
                            "price": price,
                            "original_price": orig_price if orig_price > price else None,
                            "image": img,
                            "url": url
                        })

            # Pick target SKU or default
            chosen_var = None
            if target_sku_id:
                for v in variations:
                    if str(v["sku_id"]) == str(target_sku_id):
                        chosen_var = v
                        break

            if not chosen_var and variations:
                chosen_var = variations[0]

            final_price = chosen_var["price"] if chosen_var else 0
            orig_price = chosen_var.get("original_price") if chosen_var else None
            image_url = chosen_var.get("image") if chosen_var else None
            sku_name = chosen_var.get("name") if chosen_var else None
            sku_id = chosen_var.get("sku_id") if chosen_var else target_sku_id
            target_url = (chosen_var.get("url") if chosen_var and chosen_var.get("url") else url)

            # Fallback if no variations but single sku_data
            if final_price <= 0 and sku_infos:
                sku_data = sku_infos.get(target_sku_id) or sku_infos.get("0") or list(sku_infos.values())[0]
                p_obj = sku_data.get("price", {})
                coupon = p_obj.get("coupon", {})
                sale_p = p_obj.get("salePrice", {})
                orig_p = p_obj.get("originalPrice", {})
                if coupon and coupon.get("priceNumber"):
                    final_price = int(coupon["priceNumber"])
                elif sale_p and sale_p.get("value"):
                    final_price = int(sale_p["value"])
                if orig_p and orig_p.get("value"):
                    orig_price = int(orig_p["value"])
                image_url = sku_data.get("image")

            if final_price > 0:
                return ProductScrapedData(
                    name=name or "Lazada Product",
                    price=final_price,
                    original_price=orig_price if (orig_price and orig_price > final_price) else None,
                    sku_id=sku_id,
                    sku_name=sku_name,
                    image_url=image_url,
                    url=target_url,
                    variations=variations,
                    success=True
                )
        except Exception as e:
            logger.warning(f"[CRAWLER] Error parsing mtop detail JSON: {e}")

        return None
