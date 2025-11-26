import json
import time
from playwright.sync_api import sync_playwright

HEADLESS = False


def extract_amazon(page, product_url):

    try:
        page.goto(product_url, timeout=60000)
        page.wait_for_load_state("load")
        time.sleep(2)

        title_elem = page.query_selector("h1.pdp-hero__product-name")
        title = title_elem.inner_text().strip() if title_elem else None

        img_elem = page.query_selector("img.pdp-hero-slide__image")
        img_url = img_elem.get_attribute("src") if img_elem else None

        # === Open WTB widget ===
        wtb_btn = page.wait_for_selector(".ps-widget", timeout=10000)
        wtb_btn.click(force=True)
        time.sleep(2)

        # === ZIP CODES to test (All regions) ===
        ZIP_CODES = [
            "60601", "48201",
            "10001", "02139",
            "75201", "33101",
            "90001", "98101",
            "80202", "84101"
        ]

        amazon_link = None

        for zipcode in ZIP_CODES:
            print(f"\n📌 ZIP Try → {zipcode}")

            # CLICK nearby tab every loop
            try:
                nearby_tab = page.query_selector("h2.ps-local-heading")
                if nearby_tab:
                    nearby_tab.click(force=True)
                    time.sleep(1)
            except:
                pass

            # Fill ZIP
            loc_input = page.query_selector("input.ps-map-location-textbox")
            if loc_input:
                loc_input.fill(zipcode)
                time.sleep(1)

            search_btn = page.query_selector("span.ps-map-location-button")
            if search_btn:
                search_btn.click(force=True)
                time.sleep(3)

            # === Method #1: Original Nearby Retailer selector ===
            amazon_block = page.query_selector(
                'div.ps-online-seller-details-wrapper[data-retailer="Amazon.com"]'
            )
            if amazon_block:
                buy_btn = amazon_block.query_selector("button.ps-online-buy-button")
                if buy_btn:
                    print("👉 Found Amazon in Nearby tab")
                    try:
                        with page.expect_popup() as popup_info:
                            buy_btn.click(force=True)
                        popup = popup_info.value
                        amazon_link = popup.url
                        popup.close()
                        print(f"🎯 SUCCESS @ ZIP {zipcode}")
                        break
                    except:
                        pass

            # === Method #2: Find Online tab → retailer Amazon.com ===
            try:
                online_tab = page.query_selector('[data-item="onlineSellers"]')
                if online_tab:
                    online_tab.click(force=True)
                    time.sleep(2)
            except:
                pass

            amazon_online_block = page.query_selector(
                'div.ps-online-seller-details-wrapper[data-retailer="Amazon.com"] button.ps-online-buy-button'
            )
            if amazon_online_block:
                print("👉 Found Amazon in Find Online tab (Retailer Name)")
                try:
                    with page.expect_popup() as popup_info:
                        amazon_online_block.click(force=True)
                    popup = popup_info.value
                    amazon_link = popup.url
                    popup.close()
                    print(f"🎯 SUCCESS in Online Tab @ ZIP {zipcode}")
                    break
                except:
                    pass

            # === Method #3: Find Online → data-seller="2" ===
            amazon_seller_btn = page.query_selector(
                'li[data-seller="2"] button.ps-online-buy-button'
            )
            if amazon_seller_btn:
                print("👉 Found Amazon using Seller ID=2")
                try:
                    with page.expect_popup() as popup_info:
                        amazon_seller_btn.click(force=True)
                    popup = popup_info.value
                    amazon_link = popup.url
                    popup.close()
                    print(f"🎯 SUCCESS via Seller #2 @ ZIP {zipcode}")
                    break
                except:
                    pass

        return {
            "title": title,
            "image": img_url,
            "amazon": amazon_link
        }

    except Exception as e:
        print(f"⚠ Extract failed: {e}")
        return {"title": None, "image": None, "amazon": None}


def test_single_product():
    test_url = "https://www.kindsnacks.com/products/thins/caramel-almond-sea-salt"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        page = browser.new_page()

        result = extract_amazon(page, test_url)

        browser.close()

    print("\n===================")
    print("FINAL RESULT")
    print("===================")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    test_single_product()
