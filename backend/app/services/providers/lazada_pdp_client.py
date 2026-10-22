import asyncio
import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import httpx

from app.core.config import settings

logger = logging.getLogger("client.LazadaPdpClient")


@dataclass
class SkuVariant:
    sku_id: str
    variant_name: str
    price: int
    original_price: Optional[int] = None
    available: bool = True
    image: Optional[str] = None
    url: Optional[str] = None


@dataclass
class PdpSnapshotResult:
    item_id: str
    target_sku_id: Optional[str]
    resolved_url: str
    title: str
    main_image: Optional[str]
    variations: List[SkuVariant] = field(default_factory=list)
    chosen_variation: Optional[SkuVariant] = None
    success: bool = True
    error_message: Optional[str] = None
    error_code: Optional[str] = None


class LazadaPdpClient:
    """
    Dedicated client for fetching PDP snapshots and enriching real-time prices via MTOP.
    100% asynchronous HTTP via httpx, zero browser/Playwright overhead.
    Features self-sustaining cookie & token management with automatic retry on token expiry.
    """

    MTOP_ENDPOINT = "https://acs-m.lazada.vn/h5/mtop.global.detail.web.getdetailinfo/1.0/"
    DEFAULT_APP_KEY = "24677475"
    DEFAULT_JSV = "2.7.2"

    _cached_token: Optional[str] = None
    _cached_token_expires_at: float = 0
    _cached_mtop_cookies: Dict[str, str] = {}
    _token_lock = asyncio.Lock()

    def __init__(self, timeout_seconds: float = 15.0):
        self.timeout = timeout_seconds

    @staticmethod
    def extract_item_and_sku_id(url: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract itemId and skuId from URL pathname or query parameters."""
        if not url:
            return None, None

        item_id: Optional[str] = None
        sku_id: Optional[str] = None

        m_item = re.search(r"-i(\d+)", url)
        if m_item:
            item_id = m_item.group(1)

        m_sku = re.search(r"-s(\d+)", url)
        if m_sku:
            sku_id = m_sku.group(1)

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

    @staticmethod
    def load_session_cookies() -> Dict[str, str]:
        """Load saved session cookies (e.g. from cache/lazada_cookies.json)."""
        cookies: Dict[str, str] = {}
        raw = os.getenv("LAZADA_COOKIES_JSON", "").strip()
        if raw:
            try:
                parsed = json.loads(raw)
                c_list = parsed.get("cookies", []) if isinstance(parsed, dict) else parsed
                if isinstance(c_list, list):
                    for c in c_list:
                        if isinstance(c, dict) and c.get("name") and "value" in c:
                            cookies[c["name"]] = str(c["value"])
            except Exception:
                pass

        cookie_file = Path(settings.LAZADA_COOKIE_FILE).expanduser()
        if not cookies and cookie_file.is_file():
            try:
                data = json.loads(cookie_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    for c in data:
                        if isinstance(c, dict) and c.get("name") and "value" in c:
                            cookies[c["name"]] = str(c["value"])
            except Exception:
                pass

        return cookies

    @staticmethod
    def _persist_session_cookies(new_cookies: Dict[str, str]) -> None:
        """
        Automatically persist updated session cookies to cache/lazada_cookies.json
        to sustain long-term login session health without manual re-exports.
        """
        if not new_cookies:
            return
        cookie_file = Path(settings.LAZADA_COOKIE_FILE).expanduser()
        try:
            cookie_file.parent.mkdir(parents=True, exist_ok=True)
            existing_cookies: List[dict] = []
            if cookie_file.is_file():
                try:
                    data = json.loads(cookie_file.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        existing_cookies = data
                except Exception:
                    existing_cookies = []

            cookie_map = {
                c.get("name"): c
                for c in existing_cookies
                if isinstance(c, dict) and c.get("name")
            }

            for name, val in new_cookies.items():
                if not name or not val:
                    continue
                if name in cookie_map:
                    cookie_map[name]["value"] = val
                else:
                    cookie_map[name] = {
                        "name": name,
                        "value": val,
                        "domain": ".lazada.vn",
                        "path": "/",
                        "secure": True,
                        "httpOnly": False,
                    }

            updated_list = list(cookie_map.values())
            temp = cookie_file.with_suffix(cookie_file.suffix + ".tmp")
            temp.write_text(json.dumps(updated_list, indent=2, ensure_ascii=False), encoding="utf-8")
            temp.replace(cookie_file)
        except Exception as e:
            logger.debug(f"Failed to persist session cookies: {e}")

    async def _ensure_mtop_token(self, client: httpx.AsyncClient) -> Tuple[str, Dict[str, str]]:
        """Ensure valid _m_h5_tk token from Lazada MTOP."""
        now = time.time()
        if self._cached_token and now < self._cached_token_expires_at:
            return self._cached_token, self._cached_mtop_cookies

        async with self._token_lock:
            now = time.time()
            if self._cached_token and now < self._cached_token_expires_at:
                return self._cached_token, self._cached_mtop_cookies

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
                self._cached_mtop_cookies.update(cookies_dict)
                self._persist_session_cookies(cookies_dict)

                tk = cookies_dict.get("_m_h5_tk") or client.cookies.get("_m_h5_tk")
                if tk and "_" in tk:
                    token = tk.split("_")[0]
                    try:
                        exp_ms = float(tk.split("_")[1])
                        self._cached_token = token
                        self._cached_token_expires_at = (exp_ms / 1000.0) - 30.0
                    except Exception:
                        self._cached_token = token
                        self._cached_token_expires_at = time.time() + 3600.0
                    return self._cached_token, self._cached_mtop_cookies
            except Exception as e:
                logger.warning(f"Error refreshing MTOP token: {e}")

            return "", self._cached_mtop_cookies

    def _generate_sign(self, token: str, timestamp: str, app_key: str, data_str: str) -> str:
        raw = f"{token}&{timestamp}&{app_key}&{data_str}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    async def fetch_pdp_snapshot(self, url: str) -> PdpSnapshotResult:
        """
        Step 1: Unshorten URL (preserving share parameters) & Fetch PDP snapshot.
        Step 2: Enrich real-time promotional prices via MTOP with automatic token/cookie renewal.
        Step 3: Parse and output structured SKU variations.
        """
        session_cookies = self.load_session_cookies()
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.lazada.vn/",
        }

        resolved_url = url
        pdp_html = ""

        async with httpx.AsyncClient(
            follow_redirects=True, timeout=self.timeout, cookies=session_cookies
        ) as client:
            # 1. Unshorten & Fetch PDP Snapshot
            if "s.lazada" in url:
                try:
                    resp = await client.get(url, headers=headers)
                    if resp.cookies:
                        self._persist_session_cookies(dict(resp.cookies))

                    candidate = str(resp.url)
                    if "products" in candidate and "-i" in candidate:
                        resolved_url = candidate
                        pdp_html = resp.text or ""
                    else:
                        html = resp.text or ""
                        m = (
                            re.search(r'var\s+REDIRECTURL\s*=\s*new\s+URL\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', html)
                            or re.search(r'<link\s+rel=[\'"]canonical[\'"]\s+href=[\'"]([^\'"]+)[\'"]', html, re.IGNORECASE)
                            or re.search(r'<link\s+rel=[\'"]origin[\'"]\s+href=[\'"]([^\'"]+)[\'"]', html, re.IGNORECASE)
                        )
                        if m and "products" in m.group(1):
                            resolved_url = m.group(1)
                except Exception as e:
                    logger.warning(f"Error unshortening link {url}: {e}")

            logger.info(f"Fetching fresh PDP snapshot {resolved_url}")

            if not pdp_html:
                try:
                    pdp_resp = await client.get(resolved_url, headers=headers)
                    if pdp_resp.cookies:
                        self._persist_session_cookies(dict(pdp_resp.cookies))
                    pdp_html = pdp_resp.text or ""
                except Exception as e:
                    logger.warning(f"Error fetching PDP HTML: {e}")

            item_id, target_sku_id = self.extract_item_and_sku_id(resolved_url)
            if not item_id:
                item_id, target_sku_id = self.extract_item_and_sku_id(url)

            if not item_id:
                return PdpSnapshotResult(
                    item_id="",
                    target_sku_id=target_sku_id,
                    resolved_url=resolved_url,
                    title="Unknown Product",
                    main_image=None,
                    success=False,
                    error_message="Could not resolve Lazada itemId from URL",
                    error_code="INVALID_URL",
                )

            # 2. MTOP Real-time Promotional Price Enrichment with Auto-Retry (Max 2 retries)
            parsed_path = urlparse(resolved_url).path
            uri_slug = parsed_path.strip("/").replace(".html", "") or f"products/i{item_id}"

            data_dict = {
                "deviceType": "pc",
                "uri": uri_slug,
                "path": resolved_url,
                "headerParams": json.dumps({"user-agent": headers["User-Agent"]}),
                "cookieParams": json.dumps(session_cookies) if session_cookies else "{}",
                "requestParams": "{}",
            }
            data_str = json.dumps(data_dict, separators=(",", ":"))

            mtop_module: Optional[dict] = None
            max_retries = 2

            for attempt in range(max_retries + 1):
                token, mtop_cookies = await self._ensure_mtop_token(client)
                client.cookies.update(mtop_cookies)

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
                mtop_headers = {
                    "User-Agent": headers["User-Agent"],
                    "Referer": "https://www.lazada.vn/",
                    "Accept": "application/json",
                }

                try:
                    mtop_resp = await client.get(self.MTOP_ENDPOINT, params=params, headers=mtop_headers)

                    # Persist any Set-Cookie headers returned by Lazada
                    if mtop_resp.cookies:
                        resp_cookies = dict(mtop_resp.cookies)
                        self._cached_mtop_cookies.update(resp_cookies)
                        self._persist_session_cookies(resp_cookies)

                    if mtop_resp.status_code == 200:
                        json_data = mtop_resp.json()
                        ret_list = json_data.get("ret", [])
                        ret_str = ret_list[0] if ret_list else ""

                        # Check for token expiry/empty (handles FAIL_SYS_TOKEN_EXOIRED, FAIL_SYS_TOKEN_EXPIRED, FAIL_SYS_TOKEN_EMPTY)
                        if any(err in ret_str for err in ["TOKEN_EMPTY", "TOKEN_EXOIRED", "TOKEN_EXPIRED", "FAIL_SYS_ILLEGAL_ACCESS"]):
                            if attempt < max_retries:
                                logger.info(
                                    f"MTOP token rejected ({ret_str}), refreshing token and retrying immediately (attempt {attempt + 1}/{max_retries})..."
                                )
                                # Read new token directly from response cookies if provided
                                new_tk = mtop_resp.cookies.get("_m_h5_tk") or client.cookies.get("_m_h5_tk")
                                if new_tk and "_" in new_tk:
                                    parts = new_tk.split("_")
                                    self._cached_token = parts[0]
                                    try:
                                        self._cached_token_expires_at = (float(parts[1]) / 1000.0) - 30.0
                                    except Exception:
                                        self._cached_token_expires_at = time.time() + 3600.0
                                else:
                                    self._cached_token = None
                                    self._cached_token_expires_at = 0
                                    await self._ensure_mtop_token(client)
                                continue

                        raw_mod = json_data.get("data", {}).get("module", {})
                        if isinstance(raw_mod, str):
                            mtop_module = json.loads(raw_mod)
                        elif isinstance(raw_mod, dict):
                            mtop_module = raw_mod
                        break
                except Exception as e:
                    logger.warning(f"Error querying MTOP API for itemId={item_id} (attempt {attempt + 1}): {e}")

            if mtop_module:
                logger.info(f"Successfully enriched real-time promotional prices via MTOP for itemId={item_id}")

            # 3. Parse SKU variations & log
            return self._build_snapshot_result(
                mtop_module, pdp_html, item_id, target_sku_id, resolved_url
            )

    def _build_snapshot_result(
        self,
        mod: Optional[dict],
        pdp_html: str,
        item_id: str,
        target_sku_id: Optional[str],
        resolved_url: str,
    ) -> PdpSnapshotResult:
        """Parse module data and output log for each SKU variant."""
        if not mod and pdp_html:
            # Fallback to embedded module in PDP HTML
            m = re.search(r'var\s+__moduleData__\s*=\s*(\{.*?\});\s*(?:var|</script>)', pdp_html, re.DOTALL)
            if m:
                try:
                    data_obj = json.loads(m.group(1))
                    mod = data_obj.get("data", {}).get("root", {}).get("fields", {})
                except Exception:
                    pass

        if not mod:
            return PdpSnapshotResult(
                item_id=item_id,
                target_sku_id=target_sku_id,
                resolved_url=resolved_url,
                title="Lazada Product",
                main_image=None,
                success=False,
                error_message="Failed to parse PDP data or MTOP module",
                error_code="DATA_NOT_FOUND",
            )

        # Title
        product_obj = mod.get("product", {})
        title = product_obj.get("title")
        if not title:
            tracking = mod.get("tracking", {})
            title = tracking.get("pdt_name") or "Lazada Product"
        if " | Lazada" in title:
            title = title.split(" | Lazada")[0].strip()

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

        variations: List[SkuVariant] = []
        skus_list = sku_base.get("skus", [])

        if skus_list:
            for item in skus_list:
                sid = str(item.get("skuId"))
                prop_parts = item.get("propPath", "").split(";")
                names = []
                for p in prop_parts:
                    if p in vid_map:
                        names.append(vid_map[p])
                    elif ":" in p and p.split(":")[1] in vid_map:
                        names.append(vid_map[p.split(":")[1]])

                variant_name = " - ".join(names) if names else f"Phân loại #{sid}"

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
                elif orig_p and orig_p.get("value"):
                    price = int(orig_p["value"])

                orig_price = int(orig_p.get("value", 0)) if orig_p else None
                img = sinfo.get("image") or item.get("image")
                page_path = item.get("pagePath", "")
                sku_url = ("https://www.lazada.vn" + page_path) if page_path else resolved_url

                qty = sinfo.get("quantity", {})
                text_warn = qty.get("text", "")
                max_limit = qty.get("limit", {}).get("max", 1)
                available = (text_warn != "Hết hàng") and (max_limit > 0)

                variant = SkuVariant(
                    sku_id=sid,
                    variant_name=variant_name,
                    price=price,
                    original_price=orig_price if (orig_price and orig_price > price) else None,
                    available=available,
                    image=img,
                    url=sku_url,
                )
                variations.append(variant)

                # Target format: Parsed SKU <sku_id> variant='<variant_name>' available=<true/false> price=<price>
                logger.info(
                    f"Parsed SKU {sid} variant='{variant_name}' available={str(available).lower()} price={price}"
                )
        else:
            # Fallback direct from skuInfos
            for sid, sinfo in sku_infos.items():
                if sid == "0" and len(sku_infos) > 1:
                    continue
                dlayer = sinfo.get("dataLayer", {})
                variant_name = dlayer.get("sku_name") or f"Phân loại #{sid}"

                price_obj = sinfo.get("price", {})
                coupon = price_obj.get("coupon", {})
                sale_p = price_obj.get("salePrice", {})
                orig_p = price_obj.get("originalPrice", {})

                price = 0
                if coupon and coupon.get("priceNumber"):
                    price = int(coupon["priceNumber"])
                elif sale_p and sale_p.get("value"):
                    price = int(sale_p["value"])
                elif orig_p and orig_p.get("value"):
                    price = int(orig_p["value"])

                orig_price = int(orig_p.get("value", 0)) if orig_p else None
                img = sinfo.get("image")
                qty = sinfo.get("quantity", {})
                available = (qty.get("text") != "Hết hàng") and (qty.get("limit", {}).get("max", 1) > 0)

                variant = SkuVariant(
                    sku_id=str(sid),
                    variant_name=variant_name,
                    price=price,
                    original_price=orig_price if (orig_price and orig_price > price) else None,
                    available=available,
                    image=img,
                    url=resolved_url,
                )
                variations.append(variant)
                logger.info(
                    f"Parsed SKU {sid} variant='{variant_name}' available={str(available).lower()} price={price}"
                )

        # Select target variation
        chosen: Optional[SkuVariant] = None
        if target_sku_id:
            for v in variations:
                if str(v.sku_id) == str(target_sku_id):
                    chosen = v
                    break

        if not chosen and variations:
            # Pick first available, or first item
            chosen = next((v for v in variations if v.available and v.price > 0), variations[0])

        main_img = chosen.image if chosen else None

        return PdpSnapshotResult(
            item_id=item_id,
            target_sku_id=target_sku_id,
            resolved_url=resolved_url,
            title=title,
            main_image=main_img,
            variations=variations,
            chosen_variation=chosen,
            success=True if chosen and chosen.price > 0 else False,
            error_message=None if chosen and chosen.price > 0 else "No valid price found for product",
        )
