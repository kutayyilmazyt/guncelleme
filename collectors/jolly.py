from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
import re

from utils.config_loader import get_ota_config


URL = "https://www.jollytur.com/"


# -------------------------------------------------
# TEXT / PRICE HELPERS
# -------------------------------------------------
def clean_text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def clean_price(value):
    """
    Jolly fiyat metinlerini sayıya çevirir.
    Örnekler:
    - 2.646 TL -> 2646
    - 2646 TL -> 2646
    - 2,646 TL -> 2646
    """
    if not value:
        return None

    text = clean_text(value)
    text = (
        text.replace("₺", "")
        .replace("TL", "")
        .replace("tl", "")
        .replace(".", "")
        .replace(",", "")
        .strip()
    )

    match = re.search(r"(\d{3,7})", text)
    if not match:
        return None

    price = int(match.group(1))

    # Çok küçük değerleri taksit/adet/puan gibi kabul edip ele
    if price < 500:
        return None

    return price


def make_row(room_name, price, list_price=None, pension="-", cancel="-", stock="-"):
    return {
        "OTA": "Jolly",
        "Oda Tipi": clean_text(room_name) or "-",
        "Fiyat": price,
        "Kampanyalı Fiyat": price,
        "Liste Fiyatı": list_price,
        "Pansiyon": clean_text(pension) or "-",
        "İptal": clean_text(cancel) or "-",
        "Kontenjan": "-",
        "Durum": "Başarılı",
        "Para Birimi": "TRY",
        "Stok": stock or "-",
    }


# -------------------------------------------------
# ROOM NAME NORMALIZATION FOR JOLLY RAW NAMES
# -------------------------------------------------
def normalize_jolly_room_name(name):
    """
    Burada sadece Jolly'nin ham oda isimlerini kendi standart isimlerimize yaklaştırıyoruz.
    Asıl genel oda eşleştirme yine utils/room_mapper.py içinde normalize_room_name ile yapılacak.
    """
    original = clean_text(name)
    low = original.lower()

    if not original:
        return "-"

    if "fırsat" in low or "firsat" in low:
        return "Fırsat Oda"

    if "jakuz" in low or "jacuzz" in low or "suite room" in low:
        return "Jakuzili Oda"

    if "deluxe" in low:
        return "Deluxe Oda"

    if "twin" in low or "iki ayrı" in low:
        return "Classic Twin Room"

    if "double" in low or "çift" in low or "cift" in low:
        return "Çift Kişilik, Şehir Manzaralı"

    return original


# -------------------------------------------------
# HTML PARSER
# -------------------------------------------------
def extract_price_from_block_text(text):
    """
    Bir oda kartı/blok metninden en mantıklı TL fiyatını bulur.
    Jolly bazen aynı blokta kampanya, taksit ve liste fiyatı barındırıyor.
    Biz genelde rezervasyon butonuna yakın olan ana fiyatı yakalamak için
    tüm TL değerlerini okuyup makul olan en düşük fiyatı döndürüyoruz.
    """
    if not text:
        return None

    candidates = []

    patterns = [
        r"(\d{1,3}(?:\.\d{3})+|\d{4,7})\s*TL",
        r"TL\s*(\d{1,3}(?:\.\d{3})+|\d{4,7})",
        r"(\d{1,3}(?:\.\d{3})+|\d{4,7})\s*₺",
        r"₺\s*(\d{1,3}(?:\.\d{3})+|\d{4,7})",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            price = clean_price(match.group(1))
            if price:
                candidates.append(price)

    if not candidates:
        return None

    # Çok uç değerleri at
    candidates = [p for p in candidates if 500 <= p <= 100000]
    if not candidates:
        return None

    # Jolly oda fiyatlarında aynı kartta liste fiyatı da olabiliyor.
    # Ana fiyat genellikle en düşük satış fiyatı olduğu için min kullanıyoruz.
    return min(candidates)


def extract_list_price_from_block_text(text, sale_price):
    if not text or not sale_price:
        return None

    prices = []
    for match in re.finditer(r"(\d{1,3}(?:\.\d{3})+|\d{4,7})\s*TL", text, flags=re.IGNORECASE):
        p = clean_price(match.group(1))
        if p and p >= sale_price:
            prices.append(p)

    if len(prices) <= 1:
        return None

    return max(prices)


def detect_pension(text):
    low = clean_text(text).lower()

    if "sadece oda" in low:
        return "Sadece Oda"
    if "oda kahvaltı" in low or "oda kahvalti" in low:
        return "Oda Kahvaltı"
    if "kahvaltı dahil" in low or "kahvalti dahil" in low:
        return "Oda Kahvaltı"

    return "-"


def detect_cancel(text):
    low = clean_text(text).lower()

    if "ücretsiz iptal" in low or "ucretsiz iptal" in low:
        return "Ücretsiz iptal"
    if "iptal edilemez" in low or "iade edilmez" in low:
        return "İptal edilemez"
    if "iptal" in low:
        return "İptal kontrol edilecek"

    return "İptal kontrol edilecek"


def detect_stock(text):
    low = clean_text(text).lower()

    if "tükendi" in low or "satışa kapalı" in low or "musait değil" in low or "müsait değil" in low:
        return "Kapalı"

    if "rezervasyon" in low or "satın al" in low or "hemen al" in low:
        return "Satışa Açık"

    return "-"


def get_candidate_room_cards(soup):
    """
    Jolly sayfasındaki oda kartlarını farklı class varyasyonlarına göre bulur.
    Tasarım değişirse bile geniş bir seçim havuzu bırakıyoruz.
    """
    selectors = [
        ".room-card",
        ".room-item",
        ".hotel-room-item",
        ".room-list-item",
        ".room-detail",
        ".room-box",
        ".room-wrapper",
        ".reservation-room",
        ".hotel-room",
        "[class*='room-card']",
        "[class*='roomCard']",
        "[class*='room-item']",
        "[class*='roomItem']",
        "[class*='room-list']",
        "[class*='roomList']",
        "[class*='room-detail']",
        "[class*='roomDetail']",
        "[class*='room']",
    ]

    cards = []
    seen_ids = set()

    for selector in selectors:
        for card in soup.select(selector):
            text = clean_text(card.get_text(" ", strip=True))
            if len(text) < 20:
                continue

            # Oda kartı olmayan çok büyük containerları ele
            if len(text) > 2500:
                continue

            # Fiyat ve oda çağrışımı yoksa ele
            low = text.lower()
            has_room_word = any(word in low for word in [
                "oda", "room", "suite", "deluxe", "twin", "double", "fırsat", "firsat", "jakuz"
            ])
            has_price = bool(re.search(r"(\d{1,3}(?:\.\d{3})+|\d{4,7})\s*TL", text, flags=re.I))

            if not has_room_word or not has_price:
                continue

            obj_id = id(card)
            if obj_id in seen_ids:
                continue

            seen_ids.add(obj_id)
            cards.append(card)

    return cards


def extract_room_name_from_card(card):
    """
    Önce başlık elementlerinden oda adını almaya çalışır.
    Olmazsa kart metnindeki bilinen oda isimlerini yakalar.
    """
    title_selectors = [
        ".room-title",
        ".room-name",
        ".title",
        ".name",
        "h2",
        "h3",
        "h4",
        "strong",
        "b",
        "[class*='room-title']",
        "[class*='roomTitle']",
        "[class*='room-name']",
        "[class*='roomName']",
        "[class*='title']",
        "[class*='name']",
    ]

    for selector in title_selectors:
        el = card.select_one(selector)
        if el:
            title = clean_text(el.get_text(" ", strip=True))
            if is_probable_room_name(title):
                return title

    text = clean_text(card.get_text(" ", strip=True))

    known_names = [
        "Jakuzili Suite Room",
        "Jakuzili Suite",
        "Jakuzili Oda",
        "Deluxe Room",
        "Deluxe Oda",
        "Twin Oda",
        "Twin Room",
        "Classic Twin Room",
        "Double Room",
        "Double Oda",
        "Fırsat Oda",
        "Firsat Oda",
    ]

    for name in known_names:
        if re.search(re.escape(name), text, flags=re.IGNORECASE):
            return name

    # Genel fallback: fiyat öncesindeki kısa oda adını bulmaya çalış
    match = re.search(
        r"((?:[A-ZÇĞİÖŞÜa-zçğıöşü0-9+ ]{3,45})\s(?:Oda|Room|Suite))",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return clean_text(match.group(1))

    return "-"


def is_probable_room_name(text):
    if not text:
        return False

    low = clean_text(text).lower()

    if len(low) > 80:
        return False

    keywords = ["oda", "room", "suite", "deluxe", "twin", "double", "fırsat", "firsat", "jakuz"]
    return any(k in low for k in keywords)


def parse_jolly_html_by_cards(html):
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    seen = set()

    cards = get_candidate_room_cards(soup)

    for card in cards:
        block_text = clean_text(card.get_text(" ", strip=True))

        raw_room_name = extract_room_name_from_card(card)
        room_name = normalize_jolly_room_name(raw_room_name)

        price = extract_price_from_block_text(block_text)
        if not price:
            continue

        list_price = extract_list_price_from_block_text(block_text, price)
        pension = detect_pension(block_text)
        cancel = detect_cancel(block_text)
        stock = detect_stock(block_text)

        key = (room_name.lower(), price)
        if key in seen:
            continue

        seen.add(key)
        rows.append(make_row(room_name, price, list_price, pension, cancel, stock))

    return rows


def parse_jolly_html_by_text_fallback(html):
    """
    DOM kartları yakalanamazsa metin üzerinden ikinci güvenlik ağı.
    Özellikle Jolly'nin class yapısı değişirse devreye girer.
    """
    soup = BeautifulSoup(html, "html.parser")
    text = clean_text(soup.get_text(" ", strip=True))

    rows = []
    seen = set()

    room_names = [
        "Jakuzili Suite Room",
        "Jakuzili Suite",
        "Jakuzili Oda",
        "Deluxe Room",
        "Deluxe Oda",
        "Twin Oda",
        "Twin Room",
        "Classic Twin Room",
        "Double Room",
        "Double Oda",
        "Fırsat Oda",
        "Firsat Oda",
    ]

    for raw_name in room_names:
        pattern = re.compile(
            rf"({re.escape(raw_name)})(.{{0,900}}?)(\d{{1,3}}(?:\.\d{{3}})+|\d{{4,7}})\s*TL",
            flags=re.IGNORECASE | re.DOTALL,
        )

        for match in pattern.finditer(text):
            room_name = normalize_jolly_room_name(match.group(1))
            area = clean_text(match.group(2))
            price = clean_price(match.group(3))

            if not price:
                continue

            key = (room_name.lower(), price)
            if key in seen:
                continue

            seen.add(key)
            rows.append(
                make_row(
                    room_name=room_name,
                    price=price,
                    list_price=None,
                    pension=detect_pension(area),
                    cancel=detect_cancel(area),
                    stock=detect_stock(area),
                )
            )

    return rows


def parse_jolly_html(html):
    rows = parse_jolly_html_by_cards(html)

    if not rows:
        rows = parse_jolly_html_by_text_fallback(html)

    # Aynı normalize oda için birden fazla aynı fiyat geldiyse temizle
    cleaned = []
    seen = set()
    for row in rows:
        key = (row["Oda Tipi"].lower(), row["Kampanyalı Fiyat"])
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(row)

    return cleaned


# -------------------------------------------------
# PLAYWRIGHT FLOW
# -------------------------------------------------
def click_day(page, selected_date):
    """
    Jolly datepicker için öncelik tam tarih data attribute'u.
    Bulamazsa codegen'deki gibi gün numarasına fallback yapar.
    """
    day = str(selected_date.day)

    selectors = [
        f'[data-date="{selected_date.strftime("%Y-%m-%d")}"]',
        f'[data-date="{selected_date.strftime("%Y.%m.%d")}"]',
        f'[data-day="{selected_date.day}"][data-month="{selected_date.month}"][data-year="{selected_date.year}"]',
        f'[data-day="{selected_date.day}"][data-month="{selected_date.month - 1}"][data-year="{selected_date.year}"]',
    ]

    for selector in selectors:
        loc = page.locator(selector)
        try:
            if loc.count() > 0:
                loc.first.click(timeout=5000, force=True)
                return
        except Exception:
            pass

    page.get_by_role("link", name=day, exact=True).click(timeout=15000)


def get_jolly_prices(hotel_config=None, check_in=None, check_out=None, adults=2):
    ota_config = get_ota_config(hotel_config, "jolly")
    if ota_config and not ota_config.get("active", True):
        return []
    search_name = ota_config.get("search_name", "216 eagle")
    result_text = ota_config.get("result_text", "216 Eagle Palace")
    rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="tr-TR",
            viewport={"width": 1440, "height": 1100},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/150.0.0.0 Safari/537.36"
            ),
        )

        page = context.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)

        # Otel ara
        page.get_by_role("searchbox", name=re.compile("Gidilecek Yer", re.I)).click(timeout=15000)
        page.get_by_role("searchbox", name=re.compile("Gidilecek Yer", re.I)).fill(search_name)
        page.wait_for_timeout(1500)

        clicked = False
        for candidate in [result_text, search_name]:
            try:
                page.get_by_role("link", name=re.compile(re.escape(candidate), re.I)).first.click(timeout=7000)
                clicked = True
                break
            except Exception:
                pass

        if not clicked:
            # Son çare: öneri listesindeki ilk linki seç.
            page.keyboard.press("ArrowDown")
            page.keyboard.press("Enter")

        page.wait_for_timeout(1000)

        # Tarih seç
        page.get_by_text("Tarih Seçiniz").first.click(timeout=15000)
        page.wait_for_timeout(1000)

        click_day(page, check_in)
        page.wait_for_timeout(500)

        click_day(page, check_out)
        page.wait_for_timeout(500)

        # Ara
        page.get_by_text("Hemen Ara").first.click(timeout=20000)

        try:
            page.wait_for_load_state("networkidle", timeout=30000)
        except PlaywrightTimeoutError:
            pass

        page.wait_for_timeout(6000)

        # Diğer odaları aç
        try:
            other_rooms = page.get_by_role("link", name=re.compile("DİĞER ODALAR|DIĞER ODALAR|DİGER ODALAR|OTHER ROOMS", re.I))
            if other_rooms.count() > 0:
                other_rooms.first.click(timeout=7000, force=True)
                page.wait_for_timeout(3000)
        except Exception:
            pass

        # Bazı yapılarda oda kartları lazy gelir; biraz scroll iyi olur.
        try:
            page.mouse.wheel(0, 1800)
            page.wait_for_timeout(1000)
            page.mouse.wheel(0, -1200)
            page.wait_for_timeout(1000)
        except Exception:
            pass

        html = page.content()

        with open("jolly.html", "w", encoding="utf-8") as f:
            f.write(html)

        rows = parse_jolly_html(html)

        print("Jolly bulunan oda sayısı:", len(rows))
        print(rows)

        context.close()
        browser.close()

    return rows
