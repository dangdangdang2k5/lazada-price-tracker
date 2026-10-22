import asyncio
import logging
import os
import sys

# Configure stdout for UTF-8 on Windows
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Configure logging with exact format: <logger_name> - <message>
logging.basicConfig(
    level=logging.INFO,
    format="%(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Silence low-level HTTP transport noise so our application logs shine
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

from app.services.providers.lazada_authenticated import AuthenticatedLazadaPriceProvider


async def run_probe(url: str, watch_item_id: int = 7):
    provider = AuthenticatedLazadaPriceProvider()
    data = await provider.get_product_info(
        url=url,
        use_cache=False,
        watch_item_id=watch_item_id,
    )

    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY:")
    print(f"Title       : {data.name}")
    print(f"Final Price : {data.price:,} VND")
    if data.original_price:
        print(f"Orig Price  : {data.original_price:,} VND")
    print(f"Chosen SKU  : {data.sku_id} ({data.sku_name})")
    print(f"Total SKUs  : {len(data.variations)}")
    print(f"Success     : {data.success}")
    print("=" * 60)


if __name__ == "__main__":
    test_url = (
        "https://www.lazada.vn/products/"
        "aula-ban-phim-co-f75-khong-day-3-che-do-gasket-mount-hotswap-layout-75-co-num-xoay"
        "-i3300646509-s16055633476.html?exlaz=e_share&laz_share_info=123456&appSourcePage=lzd_homesite_app_share_product_module"
    )

    if len(sys.argv) > 1:
        test_url = sys.argv[1]

    asyncio.run(run_probe(test_url))

