import json
import re
from urllib.parse import urlparse

INPUT_FILE = "all_products_merged.json"
OUTPUT_FILE = "normalized_all_products.json"


# =========================
# HELPERS
# =========================

def parse_money(m):
    if not m:
        return None
    m = m.replace(",", "")
    m = re.search(r"\$([0-9]+(?:\.[0-9]+)?)", m)
    return float(m.group(1)) if m else None


def parse_unit_price(text):
    if not text:
        return None
    text = text.replace(",", "")
    m = re.search(r"\$([0-9]+(?:\.[0-9]+)?)\s*/", text)
    return float(m.group(1)) if m else parse_money(text)


def parse_rating_stars(t):
    if not t:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s+out of\s+5", t)
    return float(m.group(1)) if m else None


def parse_rating_meta(t):
    if not t:
        return None, None
    # count
    c = re.search(r"\(([\d,]+)\s+ratings?\)", t)
    count = int(c.group(1).replace(",", "")) if c else None
    # positive %
    p = re.search(r"(\d+)%\s+positive", t)
    positive = float(p.group(1)) if p else None
    return count, positive


def extract_slug(url):
    if not url:
        return None
    part = urlparse(url).path.rstrip("/").split("/")[-1]
    return part.replace("-", " ").title()


def extract_product_family(url):
    try:
        parts = urlparse(url).path.split("/")
        idx = parts.index("products") + 1
        return parts[idx].replace("-", " ").title()
    except:
        return None


def classify_price_flag(pct):
    """
    Returns a business-friendly price classification based on
    how much higher the seller's price is compared to Amazon.
    """

    if pct is None:
        return None

    # 0% or cheaper → fair
    if pct <= 0:
        return "Fair Price"

    # Up to +20% → slightly high
    if pct <= 20:
        return "Slightly High"

    # +20% to +50% → high price
    if pct <= 50:
        return "High Price"

    # Above +50% → price gouging
    return "Price Gouging"


# =========================
# NORMALIZER
# =========================

def normalize():
    with open(INPUT_FILE, "r") as f:
        items = json.load(f)

    groups = {}

    for p in items:
        asin = p.get("asin")
        src = p.get("source_product_url")
        if not asin or not src:
            continue

        # Group Key
        if src not in groups:
            groups[src] = {
                "category": p.get("category"),
                "category_display": p.get("category_display"),
                "source_product_url": src,
                "product_name": extract_product_family(src) or extract_slug(src),
                "variants": [],
            }

        # ---------------------------------------
        # VARIANT PROCESSING
        # ---------------------------------------
        variant_name = (
            p.get("flavor")
            or (p.get("variant_dimensions") or {}).get("flavor_name")
            or extract_slug(src)
        )

        base_price = parse_money(p.get("price"))
        unit_price = parse_unit_price(p.get("price_per_unit"))

        variant_obj = {
            "asin": asin,
            "variant_name": variant_name,
            "title": p.get("title"),
            "price": base_price,
            "unit_price": unit_price,
            "prime": p.get("prime"),
            "flavor": variant_name,
            "size": p.get("size"),
            "variant_dimensions": p.get("variant_dimensions") or {},
            "final_url": p.get("final_url"),
            "original_amazon_link": p.get("original_amazon_link"),
        }

        groups[src]["variants"].append(variant_obj)

        # ---------------------------------------
        # MAIN SELLER (per variant)
        # ---------------------------------------
        main_seller = {
            "asin": asin,
            "seller_name": p.get("sold_by"),
            "ships_from": p.get("ships_from"),
            "is_authorized": True if p.get("sold_by") == "Amazon.com" else False,
            "price": base_price,
            "unit_price": unit_price,
            "price_currency": "USD",
            "prime": p.get("prime"),
        }

        # Store as list (one per variant)
        if "main_seller" not in groups[src]:
            groups[src]["main_seller"] = []

        groups[src]["main_seller"].append(main_seller)

        # ---------------------------------------
        # OTHER SELLERS
        # ---------------------------------------
        if "seller_market" not in groups[src]:
            groups[src]["seller_market"] = []

        for osel in p.get("other_sellers", []):
            osp = parse_money(osel.get("price"))
            stars = parse_rating_stars(osel.get("seller_rating"))
            rcount, pos = parse_rating_meta(osel.get("seller_rating_count"))

            delta = (osp - base_price) if (osp and base_price) else None
            pct = ((delta / base_price) * 100) if (delta and base_price) else None

            groups[src]["seller_market"].append({
                "asin": asin,
                "seller_name": osel.get("sold_by"),
                "ships_from": osel.get("ships_from"),
                "is_authorized": False,
                "price": osp,
                "unit_price": parse_unit_price(osel.get("price_per_unit")),
                "price_currency": "USD",
                "price_delta_abs": delta,
                "price_delta_percent": pct,
                "price_flag": classify_price_flag(pct),
                "rating_stars": stars,
                "rating_count": rcount,
                "positive_rating_percent": pos,
                "rating_flag": None if pos is None else (
                    "excellent" if pos >= 90 else
                    "good" if pos >= 75 else
                    "mixed" if pos >= 50 else
                    "poor"
                )
            })

    # convert dict → list
    result = list(groups.values())

    with open(OUTPUT_FILE, "w") as f:
        json.dump(result, f, indent=2)

    print("✔ FINAL Normalization Complete")
    print("✔ Output:", OUTPUT_FILE)
    print("✔ Product Families:", len(result))


if __name__ == "__main__":
    normalize()
