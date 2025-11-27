import json
from collections import defaultdict, Counter

INPUT_FILE = "normalized_all_products.json"
OUTPUT_FILE = "normalized_metadata_summary.json"

EXCLUDED_SELLERS = {
    "amazon.com", "amazon", "kind", "kind snacks", "kindsnacks"
}

def safe_lower(x):
    return (x or "").strip().lower()

def classify_rating_tier(pos):
    if pos is None:
        return None
    if pos >= 90:
        return "excellent"
    if pos >= 75:
        return "good"
    if pos >= 50:
        return "mixed"
    return "poor"

def generate_summary():
    with open(INPUT_FILE, "r") as f:
        data = json.load(f)

    total_products = len(data)
    total_categories = len({p.get("category") for p in data})

    # --------------------------------------------------------
    # COUNTERS
    # --------------------------------------------------------
    total_skus = 0
    products_per_category = defaultdict(int)
    skus_per_category = defaultdict(int)
    marketplace_skus_per_category = defaultdict(int)

    unique_sellers = set()
    unique_sellers_excl_main = set()

    seller_sku_impact = defaultdict(set)
    price_flag_counter = Counter()
    rating_tier_counter = Counter()
    top_gouged_candidates = []

    product_variant_summary = []

    # --------------------------------------------------------
    # MAIN LOOP
    # --------------------------------------------------------
    for item in data:
        category = item.get("category") or "Unknown"
        variants = item.get("variants", [])
        variant_count = len(variants)

        total_skus += variant_count
        products_per_category[category] += 1
        skus_per_category[category] += variant_count

        seller_market = item.get("seller_market", [])
        main_sellers = item.get("main_seller", [])

        # Product summary (simple)
        product_variant_summary.append({
            "product_name": item.get("product_name"),
            "category": category,
            "variant_count": variant_count,
            "unique_sellers_in_product": list({s.get("seller_name") for s in seller_market})
        })

        # --------------------------------------------------------
        # PROCESS EACH VARIANT
        # --------------------------------------------------------
        for v in variants:
            asin = v.get("asin")

            # Sellers for this ASIN
            sellers = [s for s in seller_market if s.get("asin") == asin]
            main_s = [s for s in main_sellers if s.get("asin") == asin]

            # Marketplace SKU count
            if sellers:
                marketplace_skus_per_category[category] += 1

            # Process sellers (main + marketplace)
            for s in (main_s + sellers):
                name = (s.get("seller_name") or "").strip()
                if not name:
                    continue

                unique_sellers.add(name)

                if safe_lower(name) not in EXCLUDED_SELLERS:
                    unique_sellers_excl_main.add(name)

                # Seller SKU impact
                seller_sku_impact[name].add(asin)

                # Price flag stats
                pf = s.get("price_flag")
                if pf:
                    price_flag_counter[pf] += 1

                # Rating tiers
                pos = s.get("positive_rating_percent")
                tier = classify_rating_tier(pos)
                if tier:
                    rating_tier_counter[tier] += 1

                # Price gouging candidates
                pct = s.get("price_delta_percent")
                if pct is not None:
                    top_gouged_candidates.append({
                        "asin": asin,
                        "product_name": item.get("product_name"),
                        "category": category,
                        "seller_name": name,
                        "price_delta_percent": pct,
                        "price_delta_abs": s.get("price_delta_abs")
                    })

    # --------------------------------------------------------
    # FINAL TRANSFORMS
    # --------------------------------------------------------
    seller_impact_sorted = {
        k: len(v)
        for k, v in sorted(seller_sku_impact.items(), key=lambda x: len(x[1]), reverse=True)
    }

    top_gouged_sorted = sorted(
        top_gouged_candidates,
        key=lambda x: x["price_delta_percent"] or -999,
        reverse=True
    )[:20]

    # --------------------------------------------------------
    # FINAL METADATA OBJECT
    # --------------------------------------------------------
    out = {
        "total_products": total_products,
        "total_categories": total_categories,
        "total_skus": total_skus,

        "products_per_category": dict(products_per_category),
        "skus_per_category": dict(skus_per_category),
        "marketplace_skus_per_category": dict(marketplace_skus_per_category),

        "total_unique_sellers": len(unique_sellers),
        "unique_sellers": sorted(unique_sellers),

        "unique_sellers_excluding_amazon_and_kind": sorted(unique_sellers_excl_main),
        "total_unique_sellers_excluding_amazon_and_kind": len(unique_sellers_excl_main),

        "seller_sku_impact": seller_impact_sorted,

        "price_flag_summary": dict(price_flag_counter),
        "rating_tiers_summary": dict(rating_tier_counter),

        "top_gouged_skus": top_gouged_sorted,

        "product_variant_summary": product_variant_summary
    }

    # --------------------------------------------------------
    # WRITE OUTPUT
    # --------------------------------------------------------
    with open(OUTPUT_FILE, "w") as f:
        json.dump(out, f, indent=4)

    print("✔ Metadata generated:", OUTPUT_FILE)
    print("✔ Total products:", total_products)
    print("✔ Total SKUs:", total_skus)
    print("✔ Unique sellers:", len(unique_sellers))
    print("✔ Unique sellers (excl Amazon/KIND):", len(unique_sellers_excl_main))

if __name__ == "__main__":
    generate_summary()
