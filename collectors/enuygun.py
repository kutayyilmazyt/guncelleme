from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

from utils.config_loader import get_ota_config

URL = "https://www.enuygun.com/otel/"


def clean_price(text):
    if not text:
        return None

    text = str(text)
    text = text.replace("TL", "").replace("₺", "")
    text = text.replace(".", "").replace(",", ".").strip()

    match = re.search(r"\d+", text)
    if not match:
        return None

    try:
        return float(match.group(0))
    except ValueError:
        return None


def parse_html(html):
    soup = BeautifulSoup(html, "html.parser")
    rows = []

    cards = soup.select('[data-testid="room-card-wrapper"]')

    print("Enuygun oda kartı sayısı:", len(cards))

    for card in cards:
        room_tag = card.select_one('[data-testid="room-name"]')
        price_tag = card.select_one('[data-testid="offer-price"]')
        list_price_tag = card.select_one('[data-testid="offer-discount-price"]')

        room_name = room_tag.get_text(" ", strip=True) if room_tag else "-"
        final_price = clean_price(price_tag.get_text(" ", strip=True)) if price_tag else None
        list_price = clean_price(list_price_tag.get_text(" ", strip=True)) if list_price_tag else None

        card_text = card.get_text(" ", strip=True)

        meal = "-"
        if "Sadece Oda" in card_text:
            meal = "Sadece Oda"
        elif "Kahvaltı" in card_text:
            meal = "Kahvaltı"

        cancellation = "Ücretsiz İptal" if "Ücretsiz İptal" in card_text else "-"

        if final_price:
            rows.append({
                "OTA": "Enuygun",
                "Oda Tipi": room_name,
                "Fiyat": final_price,
                "Kampanyalı Fiyat": final_price,
                "Liste Fiyatı": list_price,
                "Pansiyon": meal,
                "İptal": cancellation,
                "Kontenjan": "-",
                "Durum": "Başarılı",
                "Para Birimi": "TRY",
                "Stok": "in_stock",
            })

    return rows


def get_enuygun_prices(hotel_config=None, check_in=None, check_out=None, adults=2):
    ota_config = get_ota_config(hotel_config, "enuygun")
    if ota_config and not ota_config.get("active", True):
        return []
    search_name = ota_config.get("search_name", "216 Eagle Palace")
    result_text = ota_config.get("result_text", "Eagle Palace Kartal, İstanbul")
    check_in_iso = str(check_in)
    check_out_iso = str(check_out)

    with sync_playwright() as p:
        browser = p.chromium.launch(
    headless=True,
    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
)
        context = browser.new_context()
        page = context.new_page()

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        page.get_by_test_id("endesign-hotel-autosuggestion").get_by_test_id("hotel-label").click()
        page.get_by_test_id("endesign-hotel-autosuggestion-input").fill(search_name)
        page.wait_for_timeout(1500)

        clicked = False
        for candidate in [result_text, search_name]:
            try:
                page.get_by_text(candidate, exact=False).first.click(timeout=5000)
                clicked = True
                break
            except Exception:
                pass

        if not clicked:
            # Son çare: açılan öneri listesindeki ilk otel sonucunu seç.
            page.keyboard.press("ArrowDown")
            page.keyboard.press("Enter")

        page.get_by_test_id("hotel-datepicker-input").click()

        page.get_by_role(
            "button",
            name=str(check_in.day),
            description=check_in_iso
        ).click()

        page.get_by_role(
            "button",
            name=str(check_out.day),
            description=check_out_iso
        ).click()

        page.get_by_test_id("hotel-submit-search-button").click()

        page.wait_for_timeout(10000)

        html = page.content()

        with open("enuygun_page.html", "w", encoding="utf-8") as f:
            f.write(html)

        browser.close()

    rows = parse_html(html)

    print("Enuygun bulundu:", len(rows))
    print(rows)

    return rows