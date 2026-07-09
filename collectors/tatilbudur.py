from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

from utils.config_loader import get_ota_config

DEFAULT_URL = "https://www.tatilbudur.com/216-eagle-palace"


def clean_price(value):
    if not value:
        return None

    value = (
        str(value)
        .replace("TL", "")
        .replace("₺", "")
        .replace(".", "")
        .replace(",", ".")
        .strip()
    )

    try:
        return float(value)
    except ValueError:
        return None


def parse_tatilbudur_html(html):
    soup = BeautifulSoup(html, "html.parser")
    buttons = soup.select("a.v2-reservation-button")

    print("Tatilbudur buton sayısı:", len(buttons))

    rows = []
    seen = set()

    for button in buttons:
        room_name = button.get("roomname") or "-"
        meal_type = button.get("conceptname") or button.get("mealtype") or "-"
        amount = clean_price(button.get("amount"))
        poster_price = clean_price(button.get("poster_price"))
        currency = button.get("currency") or "TRY"
        stock_status = button.get("stockstatus") or "-"

        key = f"{room_name}-{amount}-{meal_type}"
        if key in seen:
            continue
        seen.add(key)

        if amount:
            rows.append({
                "OTA": "Tatilbudur",
                "Oda Tipi": room_name,
                "Fiyat": amount,
                "Kampanyalı Fiyat": amount,
                "Liste Fiyatı": poster_price,
                "Pansiyon": meal_type,
                "İptal": "Kontrol edilecek",
                "Kontenjan": "-",
                "Durum": "Başarılı",
                "Para Birimi": currency,
                "Stok": stock_status,
            })

    return rows


def click_visible_day(page, day):
    """
    Son çalışan Playwright akışına yakın seçim.
    Sadece ekranda görünen gün hücresine tıklar; ay gezdirmez.
    Böylece 2028'e kadar ileri gitme problemi oluşmaz.
    """
    page.get_by_role(
        "cell",
        name=re.compile(rf"^{day}( ●)?$")
    ).first.click(timeout=30000)


def get_tatilbudur_prices(hotel_config=None, check_in=None, check_out=None, adults=2):
    ota_config = get_ota_config(hotel_config, "tatilbudur")
    if ota_config and not ota_config.get("active", True):
        return []
    url = ota_config.get("url", DEFAULT_URL)
    html = ""

    with sync_playwright() as p:
        browser = p.chromium.launch(
    headless=False,
    args=[
        "--window-position=-32000,-32000",
        "--window-size=1400,900",
    ]
)

        context = browser.new_context(
            locale="tr-TR",
            viewport={"width": 1440, "height": 1000},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/150 Safari/537.36"
            ),
        )

        page = context.new_page()
        page.goto(url, wait_until="networkidle", timeout=60000)

        try:
            page.locator("#modal-background-2").click(timeout=3000)
        except Exception:
            pass

        page.get_by_text("Konaklama Tarihi Seçiniz").click(timeout=15000)
        page.wait_for_timeout(500)

        click_visible_day(page, check_in.day)
        page.wait_for_timeout(500)

        click_visible_day(page, check_out.day)
        page.wait_for_timeout(500)

        try:
            page.get_by_role("button", name="Uygula").click(timeout=5000, force=True)
        except Exception:
            pass
        page.wait_for_timeout(1000)

        with page.expect_response(
            lambda response: (
                "calculate-room-price" in response.url
                and response.request.method == "POST"
            ),
            timeout=60000,
        ) as response_info:
            page.get_by_role("button", name="Otel Ara").click(timeout=15000)

        response = response_info.value
        data = response.json()
        html = data.get("view", "")

        with open("tatilbudur_response.html", "w", encoding="utf-8") as f:
            f.write(html)

        context.close()
        browser.close()

    rows = parse_tatilbudur_html(html)

    print("Tatilbudur bulundu:", len(rows))
    print(rows)

    return rows
