import requests

from utils.config_loader import get_ota_config

HOTEL_ID = "sxkb8qc5e52c"
API_URL = "https://www.etstur.com/services/api/room"


def get_ets_prices(hotel_config=None, check_in=None, check_out=None, adults=2):
    ota_config = get_ota_config(hotel_config, "ets")
    if ota_config and not ota_config.get("active", True):
        return [{
            "OTA": "Etstur",
            "Oda Tipi": "-",
            "Fiyat": None,
            "Kampanyalı Fiyat": None,
            "Liste Fiyatı": None,
            "Pansiyon": "-",
            "İptal": "-",
            "Kontenjan": "-",
            "Durum": "Etstur hotel_id gerekli",
            "Para Birimi": "TRY",
            "Stok": "-",
        }]

    # DİKKAT: hotel_config varsa boş hotel_id için Eagle Palace ID'sine düşmeyiz.
    # Aksi halde diğer otellerde yanlışlıkla Eagle Palace fiyatı gösterilir.
    hotel_id = ota_config.get("hotel_id") if hotel_config else HOTEL_ID
    referer = ota_config.get("referer") or "https://www.etstur.com/216-Eagle-Palace"
    if not hotel_id:
        return []
    payload = {
        "hotelId": hotel_id,
        "checkIn": str(check_in),
        "checkOut": str(check_out),
        "room": {
            "adultCount": adults,
            "childCount": 0,
            "childAges": [],
            "infantCount": 0
        }
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://www.etstur.com",
        "Referer": referer
    }

    response = requests.post(API_URL, json=payload, headers=headers, timeout=20)
    response.raise_for_status()

    data = response.json()
    rows = []

    rooms = data.get("result", {}).get("rooms", [])

    for room in rooms:
        room_name = room.get("roomName", "")

        for board in room.get("subBoards", []):
            price = board.get("price", {})
            campaign = board.get("campaignHighlightedPrice")

            normal_price = price.get("amount")
            discounted_price = price.get("discountedPrice") or normal_price

            campaign_price = None
            if campaign:
                campaign_price = campaign.get("price", {}).get("amount")

            rows.append({
                "OTA": "Etstur",
                "Oda Tipi": room_name,
                "Fiyat": discounted_price,
                "Kampanyalı Fiyat": campaign_price or discounted_price,
                "İptal": board.get("cancellation"),
                "Kontenjan": board.get("lastAllotmentCount"),
                "Durum": "Başarılı"
            })

    return rows