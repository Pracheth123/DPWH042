from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import json
import re
from schema import create_record

def main():
    options = Options()
    # EXTREMELY CRITICAL: Use the modern "--headless=new" and a valid User-Agent to bypass Cloudflare/Imperva blocking OLX!
    options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    try:
        driver = webdriver.Chrome(options=options)
    except Exception:
        print("Driver failed to initialize")
        return

    try:
        driver.get("https://www.olx.in/items/q-bike")
        time.sleep(5)

        # Instead of guessing highly dynamic class names like 'EIR5N' which rotate constantly,
        # we generically target all list items and verify if they contain Rupee prices "₹"
        items = driver.find_elements(By.XPATH, "//li")

        records = []
        for item in items:
            try:
                raw_text = item.text
                if not raw_text or "₹" not in raw_text:
                    continue

                # Cleanly break the listing into components
                parts = [p.strip() for p in raw_text.split("\n") if p.strip()]
                
                # Target the exact chunk with the price
                price_str = next((p for p in parts if '₹' in p), "")
                if not price_str:
                    continue

                # Remove commas from the price block before regex so int(nums[0]) correctly extracts the entire price
                price_clean = price_str.replace(",", "")
                nums = re.findall(r'\d+', price_clean)
                if not nums:
                    continue

                price_val = int(nums[0])

                record = create_record(
                    source="olx",
                    commodity="vehicle",
                    location="india",
                    price=price_val,
                    text=" | ".join(parts),
                    signal_type="price",
                    confidence=0.9
                )
                
                # Primitive deduplication
                if record["text"] not in [r["text"] for r in records]:
                    records.append(record)

            except Exception:
                continue

        if records:
            with open("data/olx_data.json", "a", encoding='utf-8') as f:
                for r in records:
                    json.dump(r, f)
                    f.write("\n")
                    
        print(f"Saved {len(records)} OLX listings")

    except Exception:
        pass
    finally:
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    main()
