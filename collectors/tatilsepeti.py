from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

from utils.config_loader import get_ota_config


def clean_price(text):
    if not text:
        return None

    text = text.replace(".", "").replace(",", "")
    match = re.search(r"\d+", text)
    return int(match.group()) if match else None


def get_tatilsepeti_prices(hotel_config=None, check_in=None, check_out=None, adults=2):
    ota_config = get_ota_config(hotel_config, "tatilsepeti")
    if ota_config and not ota_config.get("active", True):
        return []
    slug = ota_config.get("slug", "216-eagle-palace")
    results = []

    check_in_str = check_in.strftime("%d.%m.%Y")
    check_out_str = check_out.strftime("%d.%m.%Y")

    url = (
        f"https://www.tatilsepeti.com/{slug}"
        f"?ara=oda:{adults};tarih:{check_in_str},{check_out_str}"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="tr-TR")
        page = context.new_page()

        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(7000)

        soup = BeautifulSoup(page.content(), "html.parser")

        room_cards = soup.select("div.hotel-detail-cards.mt-10")

        for card in room_cards:
            room_name_el = card.select_one("h3")
            price_el = card.select_one(
                ".hotel-detail-cards__price-div__single__all-prices__discount-price"
            )
            list_price_el = card.select_one(
                ".hotel-detail-cards__price-div__single__all-prices__default-price"
            )
            pension_el = card.select_one(
                ".hotel-detail-cards__content-div__room-detail-info-upper__all-inclusive"
            )

            room_name = room_name_el.get_text(" ", strip=True) if room_name_el else "-"
            price = clean_price(price_el.get_text(" ", strip=True)) if price_el else None
            list_price = clean_price(list_price_el.get_text(" ", strip=True)) if list_price_el else None
            pension = pension_el.get_text(" ", strip=True) if pension_el else "-"

            if not price:
                continue

            text = card.get_text(" ", strip=True)

            results.append({
                "OTA": "Tatilsepeti",
                "Oda Tipi": room_name,
                "Fiyat": price,
                "Kampanyalı Fiyat": price,
                "Liste Fiyatı": list_price,
                "Pansiyon": pension,
                "İptal": "Ücretsiz iptal" if "Ücretsiz İptal" in text or "Ücretsiz iptal" in text else "-",
                "Kontenjan": "-",
                "Durum": "Başarılı",
                "Para Birimi": "TRY",
                "Stok": "-"
            })

        context.close()
        browser.close()

    return results