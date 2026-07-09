import json
from pathlib import Path


def get_base_dir():
    return Path(__file__).resolve().parent.parent


def load_hotels():
    hotels_path = get_base_dir() / "hotels.json"
    with open(hotels_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_hotel_config(hotel_name):
    return load_hotels().get(hotel_name)


def get_ota_config(hotel_config, ota_key):
    if not hotel_config:
        return {}
    return hotel_config.get("ota", {}).get(ota_key, {}) or {}
