ROOM_MAPPING = {
    # Fırsat Oda
    "Fırsat Oda, Manzarasız": "Fırsat Oda",
    "Fırsat Odası": "Fırsat Oda",
    "Standard Fırsat Odasi": "Fırsat Oda",
    "Fırsat Oda": "Fırsat Oda",

    # Standart Oda
    "Standart Oda": "Çift Kişilik, Şehir Manzaralı",
    "Standart oda": "Çift Kişilik, Şehir Manzaralı",
    "Double Oda": "Çift Kişilik, Şehir Manzaralı",
    "Double oda": "Çift Kişilik, Şehir Manzaralı",
    "Standard Cift Kişilik Yataklı Oda": "Çift Kişilik, Şehir Manzaralı",
    "Standard Çift Kişilik Yataklı Oda": "Çift Kişilik, Şehir Manzaralı",
    "Çift Kişilik, Şehir Manzaralı": "Çift Kişilik, Şehir Manzaralı",
    "Çift Kişilik, Şehir Manzaralı,": "Çift Kişilik, Şehir Manzaralı",

    # Classic Twin
    "Aile Odası, Manzarasız, Balkonsuz": "Classic Twin Room",
    "Standard İki Ayrı Yataklı Oda": "Classic Twin Room",
    "Classic Twin Room": "Classic Twin Room",

    # Deluxe
    "Deluxe Room, Şehir Manzaralı, Balkonlu": "Deluxe Oda",
    "Deluxe Oda": "Deluxe Oda",
    "1+0 Deluxe Oda": "Deluxe Oda",

    # Jakuzili
    "Jakuzili Suit Oda, Şehir Manzaralı": "Jakuzili Oda",
    "Jakuzili Suite": "Jakuzili Oda",
    "Jakuzili Suite Oda": "Jakuzili Oda",
    "Jakuzili Oda": "Jakuzili Oda",

    # Twin
    "twin room": "Classic Twin Room",
    "classic twin room": "Classic Twin Room",
    "classic room twin": "Classic Twin Room",
    "standard twin room": "Classic Twin Room",
    "superior twin room": "Classic Twin Room",

    # Deluxe
    "deluxe room": "Deluxe Oda",
    "1+0 deluxe oda": "Deluxe Oda",
    "deluxe oda": "Deluxe Oda",

    # Fırsat
    "fırsat oda": "Fırsat Oda",
    "firsat oda": "Fırsat Oda",
    "economy room": "Fırsat Oda",
    "ekonomi oda": "Fırsat Oda",

    # Jakuzili
    "jakuzili oda": "Jakuzili Oda",
    "jacuzzi room": "Jakuzili Oda",
    "spa room": "Jakuzili Oda",

    # Şehir Manzaralı
    "çift kişilik şehir manzaralı": "Classic Twin Room",
    "city view room": "Classic Twin Room",
    "double city view": "Classic Twin Room",

}

def normalize_room_name(name):
    if not isinstance(name, str):
        return name

    name = (
        name.strip()
        .replace("  ", " ")
        .rstrip(",")
    )

    return ROOM_MAPPING.get(name, name)

# Akıllı normalize (fallback)
def normalize_room_name(name):
    if not isinstance(name, str):
        return name

    original = (
        name.strip()
        .replace("  ", " ")
        .rstrip(",")
    )

    # Tam eşleşme
    if original in ROOM_MAPPING:
        return ROOM_MAPPING[original]

    room = original.lower()

    # Twin varyasyonları
    if "twin" in room:
        return "Classic Twin Room"

    if "iki ayrı yatak" in room:
        return "Classic Twin Room"

    if "city view" in room:
        return "Classic Twin Room"

    if "şehir manzaralı" in room and "jakuzi" not in room:
        return "Classic Twin Room"

    # Deluxe
    if "deluxe" in room:
        return "Deluxe Oda"

    # Jakuzili
    if "jakuzi" in room or "jakuzili" in room or "jacuzzi" in room or "spa room" in room:
        return "Jakuzili Oda"

    # Fırsat
    if "fırsat" in room or "firsat" in room or "economy" in room or "ekonomi" in room:
        return "Fırsat Oda"

    # Double / Standard
    if "double" in room:
        return "Çift Kişilik, Şehir Manzaralı"

    if "standart" in room or "standard" in room:
        return "Çift Kişilik, Şehir Manzaralı"

    return original
