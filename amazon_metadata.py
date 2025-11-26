import json

INPUT_FILE = "normalized_all_products.json"
OUTPUT_FILE = "normalized_metadata_summary.json"

EXCLUDED_SELLERS = {"Amazon.com", "Kind", "KIND", "Kind Snacks"}


def generate_summary():
    with open(INPUT_FILE, "r") as f:
        data = json.load(f)

    total_products = len(data)
    total_categories = len(set(p["category"] for p in data))

    # Counters
    total_skus = 0
    category_counts = {}
    skus_per_category = {}  # <-- NEW

    unique_sellers = set()
    unique_sellers_excl_main = set()

    summary_products = []

    for item in data:
        category = item.get("category")
        variants = item.get("variants", [])
        variant_count = len(variants)

        # Count product families per category
        category_counts[category] = category_counts.get(category, 0) + 1

        # Count SKUs per category (NEW)
        skus_per_category[category] = skus_per_category.get(category, 0) + variant_count

        # Add to total SKUs
        total_skus += variant_count

        # Sellers
        main_sellers = item.get("main_seller", [])
        seller_market = item.get("seller_market", [])

        for s in main_sellers + seller_market:
            name = (s.get("seller_name") or "").strip()
            if not name:
                continue

            unique_sellers.add(name)
            if name not in EXCLUDED_SELLERS:
                unique_sellers_excl_main.add(name)

        # Per-product summary
        summary_products.append({
            "product_name": item.get("product_name"),
            "category": category,
            "variant_count": variant_count,
            "unique_sellers_in_product": list({s["seller_name"] for s in seller_market})
        })

    # Final output
    output = {
        "total_products": total_products,
        "total_categories": total_categories,
        "total_skus": total_skus,

        "products_per_category": category_counts,
        "skus_per_category": skus_per_category,   # <-- NEW OUTPUT

        "total_unique_sellers": len(unique_sellers),
        "unique_sellers": sorted(list(unique_sellers)),

        "unique_sellers_excluding_amazon_and_kind":
            sorted(list(unique_sellers_excl_main)),

        "total_unique_sellers_excluding_amazon_and_kind":
            len(unique_sellers_excl_main),

        "product_variant_summary": summary_products,
    }

    with open(OUTPUT_FILE, "w") as out:
        json.dump(output, out, indent=4)

    print("✔ Metadata file generated:", OUTPUT_FILE)
    print("✔ Total products:", total_products)
    print("✔ Total SKUs:", total_skus)
    print("✔ Total categories:", total_categories)
    print("✔ Unique sellers:", len(unique_sellers))
    print("✔ Unique sellers (excluding Amazon & Kind):",
          len(unique_sellers_excl_main))


if __name__ == "__main__":
    generate_summary()
