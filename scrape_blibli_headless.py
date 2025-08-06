import asyncio
import pandas as pd
from playwright.async_api import async_playwright

API_KEY = "723c00c67400b1b6c333288d476d6b94"  # Not used here but kept for reference
KATA_KUNCI = "pc gaming"
TARGET_URL_FORMAT = "https://www.blibli.com/cari/{keyword}"
NAMA_FILE_CSV = "hasil_scrape_headless.csv"

async def scrape_blibli(keyword: str):
    keyword_encoded = keyword.replace(" ", "%20")
    url = TARGET_URL_FORMAT.format(keyword=keyword_encoded)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print(f"Navigating to {url}")
        await page.goto(url, wait_until="networkidle")

        # Wait for product cards to load - selector based on current Blibli.com structure
        # Inspecting the site shows product cards have attribute data-testid="product-item"
        await page.wait_for_selector('div[data-testid="product-item"]', timeout=10000)

        products = await page.query_selector_all('div[data-testid="product-item"]')
        print(f"Found {len(products)} product cards.")

        produk_ditemukan = []

        for product in products:
            try:
                # Extract product name
                nama_tag = await product.query_selector('a[data-testid="product-title"]')
                nama_produk = (await nama_tag.inner_text()).strip() if nama_tag else "N/A"

                # Extract price
                harga_tag = await product.query_selector('span[data-testid="product-price"]')
                harga_produk = (await harga_tag.inner_text()).strip() if harga_tag else "N/A"

                # Extract seller/store name
                penjual_tag = await product.query_selector('div[data-testid="store-name"]')
                penjual = (await penjual_tag.inner_text()).strip() if penjual_tag else "N/A"

                if nama_produk != "N/A" and not any(p['Nama Produk'] == nama_produk for p in produk_ditemukan):
                    produk_ditemukan.append({
                        "Nama Produk": nama_produk,
                        "Harga": harga_produk,
                        "Toko/Penjual": penjual,
                    })
            except Exception:
                continue

        await browser.close()

        if produk_ditemukan:
            df = pd.DataFrame(produk_ditemukan)
            df.to_csv(NAMA_FILE_CSV, index=False)
            print(f"\n✅ Scraping selesai. {len(df)} produk berhasil disimpan di '{NAMA_FILE_CSV}'.")
        else:
            print("\n❌ Tidak ada produk yang berhasil ditemukan.")

if __name__ == "__main__":
    asyncio.run(scrape_blibli(KATA_KUNCI))
