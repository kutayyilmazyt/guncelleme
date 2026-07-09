import json
import re
import urllib.request
from html import unescape

from utils.config_loader import get_ota_config

DEFAULT_PATH = "/tr/otel/216-eagle-palace-istanbul"
URL_TEMPLATE = (
    "https://otelfiyat.com{path}"
    "?checkIn={check_in}&checkOut={check_out}&adults={adults}&children=0&_rsc=1kqid"
)


def fix_text(value):
    if not isinstance(value, str):
        return value
    value = unescape(value)
    try:
        value = value.encode("latin1").decode("utf-8")
    except Exception:
        pass
    return value.strip()


def fetch_rsc(url, next_url=DEFAULT_PATH):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "tr-TR,tr;q=0.9",
            "Rsc": "1",
            "Next-Url": next_url,
        },
    )

    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read().decode("utf-8", errors="ignore")


def extract_rooms_json(text):
    key = '"rooms":'
    start_key = text.find(key)

    if start_key == -1:
        print("Otelfiyat: rooms bulunamadı.")
        return []

    start = text.find("[", start_key)
    if start == -1:
        print("Otelfiyat: rooms array başlangıcı bulunamadı.")
        return []

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(text)):
        ch = text[i]

        if escape:
            escape = False
            continue

        if ch == "\\":
            escape = True
            continue

        if ch == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1

            if depth == 0:
                raw = text[start:i + 1]
                try:
                    return json.loads(raw)
                except Exception as e:
                    print("Otelfiyat JSON parse hatası:", e)
                    return []

    return []


def best_price(payment):
    return (
        payment.get("percentDiscount5Price")
        or payment.get("couponPrice")
        or payment.get("paymentAmount")
        or payment.get("discountedPrice")
        or payment.get("nonDiscountedPrice")
    )


def parse_rooms(rooms):
    rows = []
    seen = set()

    for room in rooms:
        room_name = fix_text(room.get("title", "-"))

        for payment_type in room.get("paymentTypes", []):
            for concept in payment_type.get("concepts", []):
                payment = concept.get("payment") or {}
                price = best_price(payment)

                if not price:
                    continue

                concept_name = fix_text(concept.get("title", "-"))
                list_price = payment.get("nonDiscountedPrice")
                cancel_text = fix_text(payment.get("message") or "Kontrol edilecek")
                currency = payment.get("currency") or "TRY"
                available = concept.get("availableForReservation", True)

                key = (room_name, concept_name, price)
                if key in seen:
                    continue
                seen.add(key)

                rows.append({
                    "OTA": "Otelfiyat",
                    "Oda Tipi": room_name,
                    "Fiyat": price,
                    "Kampanyalı Fiyat": price,
                    "Liste Fiyatı": list_price,
                    "Pansiyon": concept_name,
                    "İptal": cancel_text,
                    "Kontenjan": "-",
                    "Durum": "Başarılı" if available else "Satışa kapalı",
                    "Para Birimi": currency,
                    "Stok": "Satışa Açık" if available else "Kapalı",
                })

    return rows


def get_otelfiyat_prices(hotel_config=None, check_in=None, check_out=None, adults=2):
    ota_config = get_ota_config(hotel_config, "otelfiyat")
    if ota_config and not ota_config.get("active", True):
        return []
    path = ota_config.get("path", DEFAULT_PATH)
    url = URL_TEMPLATE.format(
        path=path,
        check_in=check_in.strftime("%Y-%m-%d"),
        check_out=check_out.strftime("%Y-%m-%d"),
        adults=adults,
    )

    rsc_text = fetch_rsc(url, next_url=path)

    with open("otelfiyat_rsc.txt", "w", encoding="utf-8") as f:
        f.write(rsc_text)

    rooms = extract_rooms_json(rsc_text)
    rows = parse_rooms(rooms)

    print("Otelfiyat URL:", url)
    print("Otelfiyat oda sayısı:", len(rooms))
    print("Otelfiyat satır sayısı:", len(rows))

    return rows