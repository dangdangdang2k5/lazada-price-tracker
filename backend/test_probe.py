import asyncio
import json
import sys
import time

from app.core.config import settings
from app.services.providers.lazada_api import LazadaApiProvider

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


async def main():
    sample_url = (
        "https://www.lazada.vn/products/"
        "aula-ban-phim-co-f75-khong-day-3-che-do-gasket-mount-hotswap-layout-75-co-num-xoay"
        "-i3300646509-s16055633476.html"
    )

    if len(sys.argv) > 1:
        sample_url = sys.argv[1]

    print("=" * 70)
    print("PROBE TEST: LazadaApiProvider (MTOP Gateway Direct API)")
    print(f"Target URL : {sample_url}")
    print(f"Provider Mode : {settings.PRICE_PROVIDER_MODE}")
    print("=" * 70)

    provider = LazadaApiProvider()

    start_time = time.perf_counter()
    result = await provider.get_product_info(sample_url, use_cache=False)
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    print(f"\n[Response Time]: {elapsed_ms:.2f} ms")
    print(f"[Success]      : {result.success}")
    if not result.success:
        print(f"[Error Code]   : {result.error_code}")
        print(f"[Error Message]: {result.error_message}")
        return

    print(f"[Title]        : {result.name}")
    print(f"[Current Price]: {result.price:,} VND")
    if result.original_price:
        print(f"[Orig Price]   : {result.original_price:,} VND")
    print(f"[Selected SKU] : {result.sku_id} - {result.sku_name}")
    print(f"[Main Image]   : {result.image_url}")
    print(f"[Total SKUs]   : {len(result.variations)} variations")

    print("\n--- Top 3 Variations Sample ---")
    for idx, v in enumerate(result.variations[:3], 1):
        avail_str = "Available" if v.get("available", True) else "Out of Stock"
        print(f"  {idx}. [SKU {v['sku_id']}] {v['name']} | {v['price']:,} VND | {avail_str}")

    print("=" * 70)
    print("PROBE COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(main())

