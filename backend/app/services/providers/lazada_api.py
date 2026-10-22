import asyncio
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.services.providers.base import BasePriceProvider, ProductScrapedData
from app.utils.currency import parse_currency
from app.utils.validators import is_valid_lazada_url, normalize_lazada_url


class LazadaApiProvider(BasePriceProvider):
    """
    High-performance, headless-free Price Provider for Lazada.
    Communicates directly with the Lazada Mobile Gateway / MTOP H5 API.
    Does not require Playwright, Chromium, or DOM parsing.
    """

    MTOP_ENDPOINT = "https://acs-m.lazada.vn/h5/mtop.global.detail.web.getdetailinfo/1.0/"
    DEFAULT_APP_KEY = "24677475"
    DEFAULT_JSV = "2.7.2"
    CACHE_TTL_SECONDS = 60

    # In-memory token cache to avoid redundant token handshakes
    _cached_token: Optional[str] = None
    _cached_token_expires_at: float = 0
    _cached_cookies: Dict[str, str] = {}
    _token_lock = asyncio.Lock()

    # In-memory product data cache
    _price_cache: Dict[str, Any] = {}

    def __init__(self, timeout_seconds: float = 12.0, retries: int = 2):
        self.timeout = timeout_seconds
        self.retries = retries

    @staticmethod
    def extract_item_and_sku_id(url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract itemId and skuId from standard or mobile Lazada product URLs.
        Examples:
            - https://www.lazada.vn/products/product-name-i3300646509-s16055633476.html -> ('3300646509', '16055633476')
            - https://www.lazada.vn/products/product-name-i3300646509.html -> ('3300646509', None)
            - https://www.lazada.vn/products/?itemId=3300646509&skuId=16055633476 -> ('3300646509', '16055633476')
        """
        if not url:
            return None, None

        item_id: Optional[str] = None
        sku_id: Optional[str] = None

        # 1. Path-based pattern (-i{itemId}-s{skuId}.html or -i{itemId}.html)
        item_match = re.search(r"-i(\d+)", url)
        if item_match:
            item_id = item_match.group(1)

        sku_match = re.search(r"-s(\d+)", url)
        if sku_match:
            sku_id = sku_match.group(1)

        # 2. Query param fallback (?itemId=...&skuId=...)
        if not item_id or not sku_id:
            try:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                if not item_id and "itemId" in params and params["itemId"]:
                    item_id = params["itemId"][0]
                if not sku_id and "skuId" in params and params["skuId"]:
                    sku_id = params["skuId"][0]
            except Exception:
                pass

        return item_id, sku_id

    async def resolve_short_url(self, short_url: str) -> str:
        """
        Resolve Lazada short URLs (s.lazada.vn) to the canonical product URL.
        """
        logger.info(f"[API_PROVIDER] Resolving short URL: {short_url}")
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=self.timeout) as client:
                resp = await client.get(short_url, headers=headers)
                resolved_url = str(resp.url)

                if "products" in resolved_url and "-i" in resolved_url:
                    return normalize_lazada_url(resolved_url)

                # Look for JS redirects or meta canonical links in body
                html = resp.text or ""
                target_match = (
                    re.search(r'var\s+REDIRECTURL\s*=\s*new\s+URL\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', html)
                    or re.search(r'<link\s+rel=[\'"]canonical[\'"]\s+href=[\'"]([^\'"]+)[\'"]', html, re.IGNORECASE)
                    or re.search(r'<link\s+rel=[\'"]origin[\'"]\s+href=[\'"]([^\'"]+)[\'"]', html, re.IGNORECASE)
                )
                if target_match and "products" in target_match.group(1):
                    return normalize_lazada_url(target_match.group(1))

                return normalize_lazada_url(resolved_url)
        except Exception as e:
            logger.warning(f"[API_PROVIDER] Failed resolving short link {short_url}: {e}")
            return short_url

    def _load_user_cookies(self) -> Dict[str, str]:
        """Load user-configured session cookies if available."""
        cookies: Dict[str, str] = {}
        raw_cookie_json = os.getenv("LAZADA_COOKIES_JSON", "").strip()

        if raw_cookie_json:
            try:
                data = json.loads(raw_cookie_json)
                if isinstance(data, dict):
                    data = data.get("cookies", [])
                if isinstance(data, list):
                    for c in data:
                        if isinstance(c, dict) and c.get("name") and "value" in c:
                            cookies[c["name"]] = str(c["value"])
            except Exception as e:
                logger.warning(f"[API_PROVIDER] Error parsing LAZADA_COOKIES_JSON: {e}")
        else:
            cookie_file = Path(settings.LAZADA_COOKIE_FILE).expanduser()
            if cookie_file.is_file():
                try:
                    data = json.loads(cookie_file.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        for c in data:
                            if isinstance(c, dict) and c.get("name") and "value" in c:
                                cookies[c["name"]] = str(c["value"])
                except Exception as e:
                    logger.warning(f"[API_PROVIDER] Error reading local cookie file: {e}")

        return cookies

    async def _ensure_token(self, client: httpx.AsyncClient) -> Tuple[str, Dict[str, str]]:
        """
        Ensure we have a valid _m_h5_tk token from Lazada MTOP.
        If cached and unexpired, reuse it. Otherwise, request a fresh one.
        """
        now = time.time()
        if self._cached_token and now < self._cached_token_expires_at:
            return self._cached_token, self._cached_cookies

        async with self._token_lock:
            # Recheck after acquiring lock
            now = time.time()
            if self._cached_token and now < self._cached_token_expires_at:
                return self._cached_token, self._cached_cookies

            logger.info("[API_PROVIDER] Refreshing MTOP handshake token...")
            dummy_data = json.dumps({"deviceType": "pc"}, separators=(",", ":"))
            t = str(int(time.time() * 1000))
            params = {
                "jsv": self.DEFAULT_JSV,
                "appKey": self.DEFAULT_APP_KEY,
                "t": t,
                "api": "mtop.global.detail.web.getdetailinfo",
                "v": "1.0",
                "type": "originaljson",
                "dataType": "json",
                "data": dummy_data,
            }
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
                ),
                "Referer": "https://www.lazada.vn/",
                "Accept": "application/json",
            }

            try:
                resp = await client.get(self.MTOP_ENDPOINT, params=params, headers=headers)
                cookies_dict = dict(resp.cookies)

                # Update cookies with response cookies
                self._cached_cookies.update(cookies_dict)

                tk_cookie = cookies_dict.get("_m_h5_tk") or client.cookies.get("_m_h5_tk")
                if tk_cookie and "_" in tk_cookie:
                    parts = tk_cookie.split("_")
                    token = parts[0]
                    try:
                        # parts[1] is expiry timestamp in ms
                        exp_ms = float(parts[1])
                        self._cached_token = token
                        self._cached_token_expires_at = (exp_ms / 1000.0) - 30.0  # 30s buffer
                    except Exception:
                        self._cached_token = token
                        self._cached_token_expires_at = time.time() + 3600.0
                    logger.info("[API_PROVIDER] MTOP token acquired successfully.")
                    return self._cached_token, self._cached_cookies
            except Exception as e:
                logger.warning(f"[API_PROVIDER] Handshake error: {e}")

            # Fallback empty token if handshake failed
            return "", self._cached_cookies

    def _generate_sign(self, token: str, timestamp: str, app_key: str, data_str: str) -> str:
        """Calculate MD5 MTOP signature: md5(token & t & appKey & data)"""
        raw = f"{token}&{timestamp}&{app_key}&{data_str}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    async def get_product_info(self, url: str, use_cache: bool = True) -> ProductScrapedData:
        """
        Fetch and parse product details directly via the Lazada PDP MTOP endpoint.
        """
        if not is_valid_lazada_url(url):
            return ProductScrapedData(
                name="Unknown Product",
                price=0,
                url=url,
                success=False,
                error_message="Invalid or unsupported Lazada product URL",
                error_code="PRODUCT_NOT_FOUND",
            )

        canonical_url = url
        if "s.lazada" in url:
            canonical_url = await self.resolve_short_url(url)

        item_id, target_sku_id = self.extract_item_and_sku_id(canonical_url)
        if not item_id:
            # Try original url if canonical failed to extract
            item_id, target_sku_id = self.extract_item_and_sku_id(url)

        if not item_id:
            return ProductScrapedData(
                name="Unknown Product",
                price=0,
                url=canonical_url,
                success=False,
                error_message="Could not extract Lazada itemId from URL",
                error_code="INVALID_URL",
            )

        cache_key = f"{item_id}:{target_sku_id or ''}"
        if use_cache and cache_key in self._price_cache:
            entry = self._price_cache[cache_key]
            if time.monotonic() - entry["at"] < self.CACHE_TTL_SECONDS:
                return entry["data"].model_copy(deep=True)

        user_cookies = self._load_user_cookies()
        session_cookies = dict(self._cached_cookies)
        session_cookies.update(user_cookies)

        async with httpx.AsyncClient(timeout=self.timeout, cookies=session_cookies) as client:
            token, mtop_cookies = await self._ensure_token(client)
            client.cookies.update(mtop_cookies)

            # Build request payload
            uri_slug = f"products/i{item_id}" + (f"-s{target_sku_id}" if target_sku_id else "")
            data_dict = {
                "deviceType": "pc",
                "uri": uri_slug,
                "path": f"https://www.lazada.vn/{uri_slug}.html",
                "headerParams": json.dumps(
                    {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0"}
                ),
                "cookieParams": json.dumps(user_cookies) if user_cookies else "{}",
                "requestParams": "{}",
            }
            data_str = json.dumps(data_dict, separators=(",", ":"))

            for attempt in range(1, self.retries + 1):
                t = str(int(time.time() * 1000))
                sign = self._generate_sign(token, t, self.DEFAULT_APP_KEY, data_str)

                params = {
                    "jsv": self.DEFAULT_JSV,
                    "appKey": self.DEFAULT_APP_KEY,
                    "t": t,
                    "sign": sign,
                    "api": "mtop.global.detail.web.getdetailinfo",
                    "v": "1.0",
                    "type": "originaljson",
                    "dataType": "json",
                    "data": data_str,
                }
                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
                    ),
                    "Referer": "https://www.lazada.vn/",
                    "Accept": "application/json",
                }

                try:
                    resp = await client.get(self.MTOP_ENDPOINT, params=params, headers=headers)
                    if resp.status_code != 200:
                        logger.warning(f"[API_PROVIDER] Attempt {attempt} returned HTTP {resp.status_code}")
                        continue

                    json_res = resp.json()
                    ret_list = json_res.get("ret", [])
                    ret_str = ret_list[0] if ret_list else ""

                    # Token expired or empty -> invalidate and refresh
                    if any(err in ret_str for err in ["TOKEN_EMPTY", "TOKEN_EXPIRED", "FAIL_SYS_ILLEGAL_ACCESS"]):
                        logger.info(f"[API_PROVIDER] Token rejected ({ret_str}). Refreshing token...")
                        self._cached_token = None
                        self._cached_token_expires_at = 0
                        token, mtop_cookies = await self._ensure_token(client)
                        client.cookies.update(mtop_cookies)
                        continue

                    if "SUCCESS" in ret_str:
                        product_data = self._parse_mtop_response(
                            json_res, canonical_url, item_id, target_sku_id
                        )
                        if product_data and product_data.price > 0:
                            self._price_cache[cache_key] = {
                                "at": time.monotonic(),
                                "data": product_data,
                            }
                            return product_data

                    logger.warning(f"[API_PROVIDER] MTOP response not successful: {ret_str}")
                except Exception as exc:
                    logger.warning(f"[API_PROVIDER] Attempt {attempt} failed: {exc}")

                if attempt < self.retries:
                    await asyncio.sleep(1.0)

        return ProductScrapedData(
            name="Lazada Product",
            price=0,
            url=canonical_url,
            success=False,
            error_message="Failed to retrieve product details from Lazada API gateway",
            error_code="API_EXTRACTION_FAILED",
        )

    def _parse_mtop_response(
        self,
        json_data: dict,
        canonical_url: str,
        item_id: str,
        target_sku_id: Optional[str],
    ) -> Optional[ProductScrapedData]:
        """Parse raw MTOP detail JSON into structured ProductScrapedData."""
        data_block = json_data.get("data", {})
        raw_mod = data_block.get("module", {})
        if isinstance(raw_mod, str):
            try:
                mod = json.loads(raw_mod)
            except Exception:
                return None
        elif isinstance(raw_mod, dict):
            mod = raw_mod
        else:
            return None

        # Extract title
        product_obj = mod.get("product", {})
        name = product_obj.get("title")
        if not name:
            tracking = mod.get("tracking", {})
            name = tracking.get("pdt_name")

        if name and " | Lazada" in name:
            name = name.split(" | Lazada")[0].strip()

        sku_infos = mod.get("skuInfos", {})
        po = mod.get("productOption", {})
        sku_base = po.get("skuBase", {})

        # Map property vid -> readable variation name
        vid_map: Dict[str, str] = {}
        for prop in sku_base.get("properties", []):
            pid = prop.get("pid")
            for val in prop.get("values", []):
                vid = str(val.get("vid"))
                vname = val.get("name")
                if vname:
                    vid_map[f"{pid}:{vid}"] = vname
                    vid_map[vid] = vname

        variations: List[dict] = []
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
                price_obj = sinfo.get("price", {})
                coupon = price_obj.get("coupon", {})
                sale_p = price_obj.get("salePrice", {})
                orig_p = price_obj.get("originalPrice", {})

                price = 0
                if coupon and coupon.get("priceNumber"):
                    price = int(coupon["priceNumber"])
                elif sale_p and sale_p.get("value"):
                    price = int(sale_p["value"])

                orig_price = int(orig_p.get("value", 0)) if orig_p else 0
                img = sinfo.get("image") or sku_item.get("image")
                full_url = ("https://www.lazada.vn" + page_path) if page_path else canonical_url

                qty = sinfo.get("quantity", {})
                available = qty.get("text") != "Hết hàng" and (qty.get("limit", {}).get("max", 1) > 0)

                if price > 0:
                    variations.append({
                        "sku_id": sid,
                        "name": var_name,
                        "price": price,
                        "original_price": orig_price if orig_price > price else None,
                        "image": img,
                        "url": full_url,
                        "available": available,
                    })
        else:
            # Fallback if skus_list not present: iterate over sku_infos directly
            for sid, sinfo in sku_infos.items():
                if sid == "0" and len(sku_infos) > 1:
                    continue
                price_obj = sinfo.get("price", {})
                coupon = price_obj.get("coupon", {})
                sale_p = price_obj.get("salePrice", {})
                orig_p = price_obj.get("originalPrice", {})

                price = 0
                if coupon and coupon.get("priceNumber"):
                    price = int(coupon["priceNumber"])
                elif sale_p and sale_p.get("value"):
                    price = int(sale_p["value"])

                orig_price = int(orig_p.get("value", 0)) if orig_p else 0
                img = sinfo.get("image")
                dlayer = sinfo.get("dataLayer", {})
                var_name = dlayer.get("sku_name") or f"Phân loại #{sid}"

                qty = sinfo.get("quantity", {})
                available = qty.get("text") != "Hết hàng" and (qty.get("limit", {}).get("max", 1) > 0)

                if price > 0:
                    variations.append({
                        "sku_id": str(sid),
                        "name": var_name,
                        "price": price,
                        "original_price": orig_price if orig_price > price else None,
                        "image": img,
                        "url": canonical_url,
                        "available": available,
                    })

        # Match target SKU or select the first available variation
        chosen_var: Optional[dict] = None
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
        target_url = chosen_var.get("url") if chosen_var and chosen_var.get("url") else canonical_url

        if final_price <= 0 and sku_infos:
            sku_data = sku_infos.get(target_sku_id) or sku_infos.get("0") or list(sku_infos.values())[0]
            price_obj = sku_data.get("price", {})
            coupon = price_obj.get("coupon", {})
            sale_p = price_obj.get("salePrice", {})
            orig_p = price_obj.get("originalPrice", {})
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
                success=True,
            )

        return None

