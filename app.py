import time
import json
from pathlib import Path
from datetime import date, timedelta, datetime
from concurrent.futures import ProcessPoolExecutor  # Gerçek paralellik için eklendi

import pandas as pd
import streamlit as st

from utils.config_loader import load_hotels, get_hotel_config
from collectors.ets import get_ets_prices
from collectors.tatilbudur import get_tatilbudur_prices
from collectors.enuygun import get_enuygun_prices
from collectors.tatilsepeti import get_tatilsepeti_prices
from collectors.otelfiyat import get_otelfiyat_prices
from collectors.jolly import get_jolly_prices
from utils.room_mapper import normalize_room_name


st.set_page_config(
    page_title="216 Hotels Revenue Manager v2.0",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -------------------------------------------------
# SPLASH SCREEN
# -------------------------------------------------
if "splash_done" not in st.session_state:
    st.markdown(
        """
        <style>
            html, body, [data-testid="stAppViewContainer"] {
                background: #020509 !important;
            }
            [data-testid="stHeader"] { background: transparent !important; }
            .block-container {
                max-width: 100% !important;
                padding: 0 !important;
            }
            .splash-wrap {
                height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                background:
                    radial-gradient(circle at center, rgba(242,195,91,.13), transparent 32%),
                    linear-gradient(180deg, #010307 0%, #07111c 100%);
                color: #f2c35b;
                text-align: center;
                font-family: Georgia, 'Times New Roman', serif;
            }
            .splash-title {
                font-size: 42px;
                line-height: 1.25;
                font-weight: 900;
                letter-spacing: .02em;
                text-shadow: 0 0 30px rgba(242,195,91,.22);
            }
            .splash-sub {
                margin-top: 22px;
                color: rgba(255,255,255,.76);
                font-size: 18px;
                font-weight: 600;
                font-family: Arial, sans-serif;
            }
            .rgb-text {
                display: inline-block;
                font-weight: 900;
                animation: rgbFlow 2.2s linear infinite;
                text-shadow: 0 0 18px currentColor;
            }
            @keyframes rgbFlow {
                0% { color: rgb(255, 40, 40); }
                16% { color: rgb(255, 180, 40); }
                32% { color: rgb(255, 245, 70); }
                48% { color: rgb(60, 255, 120); }
                64% { color: rgb(60, 190, 255); }
                80% { color: rgb(190, 90, 255); }
                100% { color: rgb(255, 40, 40); }
            }
            .splash-line {
                width: 380px;
                height: 1px;
                margin: 28px auto 0 auto;
                background: linear-gradient(90deg, transparent, #f2c35b, transparent);
            }
        </style>
        <div class="splash-wrap">
            <div>
                <div class="splash-title">216 Hotels OTA denetimine Hoş Geldiniz.</div>
                <div class="splash-sub">¨ <span class="rgb-text">Biz de yazılımcıyız...</span></div>
                <div class="splash-line"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    time.sleep(3)
    st.session_state["splash_done"] = True
    st.rerun()


# -------------------------------------------------
# STYLE
# -------------------------------------------------
st.markdown(
    """
    <style>
        :root {
            --bg: #070b11;
            --panel: rgba(16, 26, 40, .92);
            --panel-2: rgba(21, 32, 48, .96);
            --line: rgba(242,195,91,.26);
            --text: #f5f7fb;
            --muted: #aeb9c8;
            --gold: #f2c35b;
            --gold-2: #d4a941;
            --green: #4ade80;
            --red: #ef4444;
            --blue: #60a5fa;
            --purple: #a78bfa;
        }
        html, body, [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at 15% 5%, rgba(242,195,91,.10), transparent 24%),
                radial-gradient(circle at 88% 4%, rgba(93,168,255,.10), transparent 28%),
                linear-gradient(180deg, #05080d 0%, #08111d 100%) !important;
            color: var(--text);
        }
        [data-testid="stHeader"] { background: transparent !important; }
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
            max-width: 1920px !important;
        }
        .designer-badge {
            position: fixed;
            right: 18px;
            bottom: 14px;
            z-index: 9999;
            padding: 8px 14px;
            border-radius: 999px;
            background: rgba(8, 13, 20, .88);
            color: var(--gold);
            border: 1px solid rgba(242,195,91,.28);
            font-size: 13px;
            font-weight: 800;
            box-shadow: 0 10px 30px rgba(0,0,0,.35);
        }
        .hero {
            padding: 24px 26px;
            border-radius: 18px;
            background: linear-gradient(145deg, rgba(17,28,42,.96), rgba(8,15,24,.96));
            border: 1px solid var(--line);
            box-shadow: 0 24px 70px rgba(0,0,0,.34), inset 0 1px 0 rgba(255,255,255,.04);
            margin-bottom: 16px;
        }
        .hero-title {
            color: var(--gold);
            font-size: 34px;
            font-weight: 950;
            margin: 0;
            letter-spacing: .01em;
        }
        .hero-sub {
            color: var(--muted);
            margin-top: 8px;
            font-size: 15px;
            font-weight: 650;
        }

        .hotel-picker-card {
            padding: 14px 15px;
            border-radius: 16px;
            background: linear-gradient(145deg, rgba(17,28,42,.96), rgba(8,15,24,.96));
            border: 1px solid rgba(242,195,91,.24);
            box-shadow: 0 16px 40px rgba(0,0,0,.26), inset 0 1px 0 rgba(255,255,255,.04);
            min-height: 112px;
        }
        .hotel-picker-title {
            color: var(--gold);
            font-weight: 950;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: .04em;
            margin-bottom: 9px;
        }
        .hotel-active {
            color: #ffffff;
            font-size: 15px;
            font-weight: 950;
            padding: 9px 11px;
            border-radius: 10px;
            background: rgba(242,195,91,.13);
            border: 1px solid rgba(242,195,91,.32);
            margin-bottom: 9px;
        }
        .hotel-list {
            max-height: 94px;
            overflow-y: auto;
            padding-right: 6px;
        }
        .hotel-option {
            color: #ffffff;
            font-size: 12px;
            font-weight: 750;
            padding: 3px 0;
            line-height: 1.35;
        }
        .hotel-option .gold-name {
            color: var(--gold);
            font-weight: 950;
        }
        .hotel-option .soon {
            color: rgba(239, 68, 68, .82);
            font-weight: 950;
            margin-left: 5px;
        }
        .hotel-option.active-row {
            color: #ffffff;
            font-weight: 950;
        }
        .stButton > button {
            width: 100%;
            height: 48px;
            border-radius: 12px;
            border: 1px solid rgba(255,220,140,.8);
            color: #111;
            background: linear-gradient(180deg, #f9d978, #d6a647);
            font-weight: 950;
            box-shadow: 0 10px 26px rgba(221,171,65,.20);
        }
        .stButton > button:hover {
            color: #000;
            background: linear-gradient(180deg, #ffe193, #e2b351);
            border: 1px solid #ffe6ac;
        }
        .stDateInput label, .stNumberInput label, .stSelectbox label {
            color: #f5f7fb !important;
            font-weight: 900 !important;
        }
        .stDateInput input, .stNumberInput input {
            color: #fff !important;
            background: rgba(16, 27, 43, .98) !important;
        }
        div[data-baseweb="select"] > div {
            color: #ffffff !important;
            background-color: rgba(16, 27, 43, .98) !important;
            border-color: rgba(242,195,91,.30) !important;
            border-radius: 12px !important;
        }
        .hotel-status-box {
            margin-top: 8px;
            padding: 10px 12px;
            border-radius: 12px;
            background: linear-gradient(145deg, rgba(17,28,42,.96), rgba(8,15,24,.96));
            border: 1px solid rgba(242,195,91,.24);
            min-height: 42px;
        }
        .hotel-status-active {
            color: #ffffff;
            font-weight: 950;
            font-size: 13px;
        }
        .hotel-status-gold {
            color: var(--gold);
            font-weight: 950;
        }
        .hotel-status-soon {
            color: rgba(239, 68, 68, .86);
            font-weight: 950;
            font-size: 12px;
            margin-left: 6px;
        }
        .hotel-small-note {
            margin-top: 4px;
            color: var(--muted);
            font-size: 11px;
            font-weight: 750;
        }
        .card {
            background: linear-gradient(145deg, rgba(17,28,42,.96), rgba(8,15,24,.96));
            border: 1px solid rgba(242,195,91,.22);
            border-radius: 16px;
            box-shadow: 0 18px 48px rgba(0,0,0,.30), inset 0 1px 0 rgba(255,255,255,.04);
        }
        .kpi-card {
            min-height: 142px;
            padding: 20px 22px;
            position: relative;
            overflow: hidden;
        }
        .kpi-label {
            color: #ffffff;
            font-weight: 950;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: .04em;
            margin-bottom: 8px;
        }
        .kpi-value {
            color: var(--gold);
            font-size: 27px;
            font-weight: 950;
            line-height: 1.08;
        }
        .kpi-value.green { color: var(--green); }
        .kpi-value.red { color: var(--red); }
        .kpi-value.blue { color: var(--blue); }
        .kpi-note {
            color: var(--muted);
            margin-top: 8px;
            font-size: 13px;
            font-weight: 650;
        }
        .section {
            padding: 18px;
            margin-top: 14px;
        }
        .section-title {
            color: var(--gold);
            font-size: 19px;
            font-weight: 950;
            margin-bottom: 14px;
            text-transform: uppercase;
            letter-spacing: .02em;
        }
        table.rate-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            overflow: hidden;
            border: 1px solid rgba(147,162,184,.16);
            border-radius: 10px;
            color: var(--text);
            font-size: 14px;
        }
        table.rate-table th {
            background: rgba(28,40,58,.9);
            color: #fff;
            padding: 13px 10px;
            border-bottom: 1px solid rgba(242,195,91,.18);
            border-right: 1px solid rgba(147,162,184,.12);
            text-align: center;
            font-weight: 950;
        }
        table.rate-table td {
            padding: 13px 10px;
            border-bottom: 1px solid rgba(147,162,184,.12);
            border-right: 1px solid rgba(147,162,184,.10);
            text-align: center;
            background: rgba(10,20,33,.48);
        }
        table.rate-table th:first-child, table.rate-table td:first-child { text-align: left; font-weight: 900; }
        .lowest-badge {
            display: inline-block;
            padding: 7px 12px;
            border-radius: 8px;
            color: #fff;
            background: linear-gradient(180deg, #bd2328, #7b1115);
            font-weight: 950;
            box-shadow: inset 0 1px 0 rgba(255,255,255,.16);
        }
        .min-price { color: var(--green); font-weight: 950; }
        .max-price { color: var(--red); font-weight: 950; }
        .insight-list {
            color: #dbe4f0;
            line-height: 1.8;
            font-size: 15px;
            font-weight: 650;
        }
        .insight-list b { color: var(--gold); }
        .score-wrap {
            margin-top: 8px;
            background: rgba(255,255,255,.08);
            border-radius: 999px;
            overflow: hidden;
            height: 18px;
        }
        .score-bar {
            height: 18px;
            background: linear-gradient(90deg, #ef4444, #f2c35b, #4ade80);
        }
        .mini-table {
            width: 100%;
            border-collapse: collapse;
            color: var(--text);
            font-size: 14px;
        }
        .mini-table th {
            background: rgba(28,40,58,.72);
            padding: 11px 10px;
            color: #fff;
            border-bottom: 1px solid rgba(242,195,91,.16);
            text-align: left;
        }
        .mini-table td {
            padding: 10px;
            border-bottom: 1px solid rgba(147,162,184,.12);
        }
        .info-box {
            background: rgba(40,116,166,.25);
            border: 1px solid rgba(93,168,255,.24);
            color: #9bd0ff;
            border-radius: 12px;
            padding: 16px 18px;
            font-weight: 800;
        }
        div[data-testid="stDataFrame"] {
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid rgba(147,162,184,.16);
        }
        .footer {
            margin-top: 26px;
            display:flex;
            gap:22px;
            align-items:center;
            justify-content:center;
            color:var(--gold);
            font-weight:950;
        }
        .footer-line {
            width: 32%; height:1px;
            background:linear-gradient(90deg, transparent, rgba(242,195,91,.8), transparent);
        }
    </style>
    <div class="designer-badge">216 Hotels Revenue Manager v2.0</div>
    """,
    unsafe_allow_html=True,
)


# -------------------------------------------------
# HELPERS
# -------------------------------------------------
def not_ready_collector(ota_name):
    return [{
        "OTA": ota_name,
        "Oda Tipi": "-",
        "Fiyat": None,
        "Kampanyalı Fiyat": None,
        "Liste Fiyatı": None,
        "Pansiyon": "-",
        "İptal": "-",
        "Kontenjan": "-",
        "Durum": "Entegrasyon bekliyor",
        "Para Birimi": "TRY",
        "Stok": "-",
    }]


def money(value):
    if pd.isna(value) or value is None:
        return "-"
    return f"{float(value):,.0f} TL".replace(",", ".")


def safe_text(value):
    if value is None or pd.isna(value):
        return "-"
    return str(value)


def discount_rate(row):
    list_price = row.get("Liste Fiyatı")
    sale_price = row.get("Kampanyalı Fiyat")
    if pd.isna(list_price) or pd.isna(sale_price) or not list_price or list_price <= 0:
        return None
    if list_price <= sale_price:
        return 0.0
    return ((list_price - sale_price) / list_price) * 100


def normalize_dataframe(df):
    required_columns = [
        "OTA", "Oda Tipi", "Fiyat", "Kampanyalı Fiyat", "Liste Fiyatı",
        "Pansiyon", "İptal", "Kontenjan", "Durum", "Para Birimi", "Stok"
    ]
    for col in required_columns:
        if col not in df.columns:
            df[col] = None

    df = df[required_columns].copy()
    
    # İlk normalizasyon ve veri tipi dönüşümleri
    df["Oda Tipi"] = df["Oda Tipi"].fillna("-").apply(normalize_room_name)
    df["Fiyat"] = pd.to_numeric(df["Fiyat"], errors="coerce")
    df["Kampanyalı Fiyat"] = pd.to_numeric(df["Kampanyalı Fiyat"], errors="coerce")
    df["Liste Fiyatı"] = pd.to_numeric(df["Liste Fiyatı"], errors="coerce")
    df["Kontenjan"] = df["Kontenjan"].astype(str)

    # --- ENUYGUN LİSTE FİYATINI REFERANS ALMA MANTIĞI ---
    enuygun_df = df[(df["OTA"] == "Enuygun") & (df["Liste Fiyatı"].notna()) & (df["Liste Fiyatı"] > 0)]
    enuygun_fiyat_haritasi = dict(zip(enuygun_df["Oda Tipi"], enuygun_df["Liste Fiyatı"]))

    def fill_missing_list_price(row):
        current_list = row["Liste Fiyatı"]
        if pd.isna(current_list) or current_list <= 0:
            return enuygun_fiyat_haritasi.get(row["Oda Tipi"], current_list)
        return current_list

    df["Liste Fiyatı"] = df.apply(fill_missing_list_price, axis=1)
    # -----------------------------------------------------

    # Yeni doldurulan liste fiyatlarına göre indirim oranlarını hesapla
    df["İndirim Oranı"] = df.apply(discount_rate, axis=1)
    return df


def run_single_collector(args):
    ota_name, collector_func, hotel_config, check_in, check_out, adults = args
    try:
        data = collector_func(hotel_config, check_in, check_out, adults)
        if data:
            return data
        else:
            row = not_ready_collector(ota_name)[0]
            row["Durum"] = "Veri bulunamadı"
            return [row]
    except Exception as e:
        row = not_ready_collector(ota_name)[0]
        row["Durum"] = f"Hata: {e}"
        return [row]


def collect_ota_prices(hotel_config, check_in, check_out, adults):
    all_results = []
    
    collectors = [
        ("Etstur", get_ets_prices, hotel_config, check_in, check_out, adults),
        ("Tatilbudur", get_tatilbudur_prices, hotel_config, check_in, check_out, adults),
        ("Enuygun", get_enuygun_prices, hotel_config, check_in, check_out, adults),
        ("Tatilsepeti", get_tatilsepeti_prices, hotel_config, check_in, check_out, adults),
        ("Otelfiyat", get_otelfiyat_prices, hotel_config, check_in, check_out, adults),
        ("Jolly", get_jolly_prices, hotel_config, check_in, check_out, adults),
    ]

    with st.spinner("Tüm OTA kanalları paralel olarak sorgulanıyor, lütfen bekleyin..."):
        with ProcessPoolExecutor(max_workers=len(collectors)) as executor:
            results = executor.map(run_single_collector, collectors)
            for res in results:
                all_results.extend(res)

    for ota in ["Booking", "Agoda", "Trip.com", "Expedia", "Hotels.com"]:
        all_results.extend(not_ready_collector(ota))

    return all_results


def build_pivot(fiyatli_df):
    # Oda Tipi ve OTA bazında fiyatları matrise çeviren pivot fonksiyonu düzeltildi
    pivot_df = fiyatli_df.groupby(["Oda Tipi", "OTA"])["Kampanyalı Fiyat"].min().unstack().reset_index()
    return pivot_df


def pivot_html(pivot_df):
    ota_cols = [c for c in pivot_df.columns if c != "Oda Tipi"]
    rows = []
    for _, row in pivot_df.iterrows():
        numeric = pd.to_numeric(row[ota_cols], errors="coerce")
        valid = numeric.dropna()
        min_price = valid.min() if not valid.empty else None
        max_price = valid.max() if not valid.empty else None
        min_ota = valid.idxmin() if not valid.empty else "-"
        max_ota = valid.idxmax() if not valid.empty else "-"
        gap_pct = "-"
        if min_price and max_price and min_price > 0:
            gap_pct = f"%{((max_price - min_price) / min_price * 100):.1f}".replace(".", ",")

        cells = [f"<td>{safe_text(row['Oda Tipi'])}</td>"]
        for col in ota_cols:
            value = row[col]
            if pd.notna(value):
                cls = " class='min-price'" if min_price is not None and float(value) == float(min_price) else " class='max-price'" if max_price is not None and float(value) == float(max_price) and max_price != min_price else ""
                cells.append(f"<td{cls}>{money(value)}</td>")
            else:
                cells.append("<td>-</td>")
        lowest = f"<span class='lowest-badge'>{money(min_price)}<br><small>{min_ota}</small></span>" if min_price is not None else "-"
        cells.append(f"<td>{lowest}</td>")
        cells.append(f"<td>{max_ota}</td>")
        cells.append(f"<td>{gap_pct}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    headers = "".join([f"<th>{c}</th>" for c in ["Oda Tipi"] + ota_cols + ["En Ucuz", "En Pahalı OTA", "Fark %"]])
    return f"<table class='rate-table'><thead><tr>{headers}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def ota_summary_html(fiyatli_df):
    summary = fiyatli_df.groupby("OTA", as_index=False).agg(
        Min_Fiyat=("Kampanyalı Fiyat", "min"),
        Max_Fiyat=("Kampanyalı Fiyat", "max"),
        Ortalama=("Kampanyalı Fiyat", "mean"),
        Oda_Sayısı=("Oda Tipi", "nunique"),
    ).sort_values("Min_Fiyat")
    rows = []
    for _, r in summary.iterrows():
        rows.append(
            f"<tr><td>{r['OTA']}</td><td>{money(r['Min_Fiyat'])}</td><td>{money(r['Max_Fiyat'])}</td><td>{money(r['Ortalama'])}</td><td>{int(r['Oda_Sayısı'])}</td></tr>"
        )
    return f"""
    <table class='mini-table'>
        <thead><tr><th>OTA</th><th>Min</th><th>Max</th><th>Ortalama</th><th>Oda</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
    </table>
    """


def revenue_score(fiyatli_df):
    ota_min = fiyatli_df.groupby("OTA")["Kampanyalı Fiyat"].min()
    if ota_min.empty or ota_min.min() <= 0:
        return 0
    spread = (ota_min.max() - ota_min.min()) / ota_min.min()
    return max(0, min(100, round(100 - (spread * 100))))


def opportunity_discount_df(fiyatli_df):
    opportunity = fiyatli_df[fiyatli_df["Oda Tipi"].str.lower().str.contains("fırsat|firsat", na=False)].copy()
    if opportunity.empty:
        return pd.DataFrame(columns=["OTA", "Oda Tipi", "Liste Fiyatı", "Kampanyalı Fiyat", "İndirim Oranı"])
    opportunity = opportunity.sort_values(["OTA", "Kampanyalı Fiyat"])
    opportunity = opportunity.groupby("OTA", as_index=False).first()
    
    # Formatlama yapmadan önce kopyasını alıp üzerinde işlem yapıyoruz
    display_opp = opportunity.copy()
    display_opp["İndirim Oranı"] = display_opp["İndirim Oranı"].apply(lambda x: "-" if pd.isna(x) else f"%{x:.1f}".replace(".", ","))
    display_opp["Liste Fiyatı"] = display_opp["Liste Fiyatı"].apply(money)
    display_opp["Campanyalı Fiyat"] = display_opp["Kampanyalı Fiyat"].apply(money)
    return display_opp[["OTA", "Oda Tipi", "Liste Fiyatı", "Kampanyalı Fiyat", "İndirim Oranı"]]




# -------------------------------------------------
# COMPETITOR ANALYSIS HELPERS
# -------------------------------------------------
def load_competitors():
    path = Path(__file__).resolve().parent / "competitors.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def competitor_hotel_config(comp):
    """Rakip oteli mevcut collector formatına çevirir."""
    slug = comp.get("tatilsepeti_slug")
    return {
        "display_name": comp.get("name", "Rakip Otel"),
        "status": "active",
        "ota": {
            "tatilsepeti": {
                "active": bool(slug),
                "slug": slug or "",
            }
        },
    }


def collect_single_competitor(comp, check_in, check_out, adults):
    name = comp.get("name", "Rakip Otel")
    segment = comp.get("segment", "-")
    area = comp.get("area", "-")
    ota = comp.get("primary_ota", "Tatilsepeti")

    try:
        cfg = competitor_hotel_config(comp)
        rows = get_tatilsepeti_prices(cfg, check_in, check_out, adults)
        fiyatli = [r for r in rows if r.get("Kampanyalı Fiyat") or r.get("Fiyat")]

        if not fiyatli:
            return {
                "Rakip Otel": name,
                "Bölge": area,
                "Segment": segment,
                "OTA": ota,
                "En Düşük Fiyat": None,
                "Oda Tipi": "-",
                "Durum": "Veri bulunamadı",
            }

        best = min(fiyatli, key=lambda r: float(r.get("Kampanyalı Fiyat") or r.get("Fiyat") or 10**12))
        price = best.get("Kampanyalı Fiyat") or best.get("Fiyat")
        return {
            "Rakip Otel": name,
            "Bölge": area,
            "Segment": segment,
            "OTA": best.get("OTA", ota),
            "En Düşük Fiyat": price,
            "Oda Tipi": best.get("Oda Tipi", "-"),
            "Durum": "Başarılı",
        }
    except Exception as e:
        return {
            "Rakip Otel": name,
            "Bölge": area,
            "Segment": segment,
            "OTA": ota,
            "En Düşük Fiyat": None,
            "Oda Tipi": "-",
            "Durum": f"Hata: {e}",
        }


def collect_competitor_prices(base_hotel_name, check_in, check_out, adults):
    competitors_map = load_competitors()
    competitors = competitors_map.get(base_hotel_name, [])
    results = []
    progress = st.progress(0, text="Rakip oteller hazırlanıyor...")

    total = max(len(competitors), 1)
    for idx, comp in enumerate(competitors, start=1):
        progress.progress(idx / total, text=f"Rakip analiz ediliyor: {comp.get('name', 'Rakip Otel')}")
        results.append(collect_single_competitor(comp, check_in, check_out, adults))

    progress.empty()
    return results


def render_competitor_analysis(selected_hotel, hotel_config, check_in, check_out, adults):
    if check_out <= check_in:
        st.error("Çıkış tarihi, giriş tarihinden sonra olmalı.")
        return

    st.markdown("<div class='card section'><div class='section-title'>Rakip Otel Analizi</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='info-box'>Bu modül şimdilik Tatilsepeti üzerinden rakip otellerin en düşük fiyatını çeker. Sonraki aşamada Etstur, Jolly, Otelfiyat ve Booking tarafı da eklenebilir.</div>",
        unsafe_allow_html=True,
    )

    with st.spinner("Önce 216 Eagle Palace fiyatı, sonra rakip oteller sorgulanıyor..."):
        own_rows = collect_ota_prices(hotel_config, check_in, check_out, adults)
        own_df = normalize_dataframe(pd.DataFrame(own_rows))
        own_prices = own_df[own_df["Kampanyalı Fiyat"].notna()].copy()

    if own_prices.empty:
        st.warning("216 Eagle Palace için fiyat bulunamadı. Önce kendi OTA collector çıktısını kontrol et.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    own_best = own_prices.sort_values("Kampanyalı Fiyat").iloc[0]
    own_price = float(own_best["Kampanyalı Fiyat"])

    competitor_rows = collect_competitor_prices(selected_hotel, check_in, check_out, adults)
    comp_df = pd.DataFrame(competitor_rows)

    if comp_df.empty:
        st.warning("competitors.json içinde bu otel için rakip tanımı bulunamadı.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    comp_df["En Düşük Fiyat"] = pd.to_numeric(comp_df["En Düşük Fiyat"], errors="coerce")
    priced = comp_df[comp_df["En Düşük Fiyat"].notna()].copy()

    if priced.empty:
        st.warning("Rakiplerden fiyat alınamadı. Slug/URL veya OTA sayfa yapısını kontrol etmek gerekebilir.")
        st.dataframe(comp_df, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
        return

    market_avg = priced["En Düşük Fiyat"].mean()
    market_min = priced["En Düşük Fiyat"].min()
    market_max = priced["En Düşük Fiyat"].max()
    cheaper_count = int((priced["En Düşük Fiyat"] > own_price).sum())
    expensive_count = int((priced["En Düşük Fiyat"] < own_price).sum())
    market_gap = own_price - market_avg
    market_gap_pct = (market_gap / market_avg * 100) if market_avg else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    kpis = [
        ("Bizim En İyi Fiyat", money(own_price), f"{own_best['OTA']} • {own_best['Oda Tipi']}", "green"),
        ("Rakip Ortalama", money(market_avg), "Fiyat bulunan rakipler", "blue"),
        ("Rakip Min", money(market_min), "Pazardaki en düşük rakip", ""),
        ("Rakip Max", money(market_max), "Pazardaki en yüksek rakip", "red"),
        ("Pazar Konumu", f"%{market_gap_pct:.1f}".replace(".", ","), "Ortalamaya göre fark", "green" if market_gap < 0 else "red"),
    ]
    for col, (label, value, note, cls) in zip([c1, c2, c3, c4, c5], kpis):
        with col:
            st.markdown(
                f"""
                <div class='card kpi-card'>
                    <div class='kpi-label'>{label}</div>
                    <div class='kpi-value {cls}'>{value}</div>
                    <div class='kpi-note'>{note}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    priced["Bizden Fark TL"] = priced["En Düşük Fiyat"] - own_price
    priced["Bizden Fark %"] = priced["Bizden Fark TL"] / own_price * 100
    priced = priced.sort_values("En Düşük Fiyat")

    insight_color = "green" if market_gap < 0 else "red"
    position_text = "pazar ortalamasının altındasınız" if market_gap < 0 else "pazar ortalamasının üstündesiniz"
    st.markdown(
        f"""
        <div class='insight-list'>
            • <b>{selected_hotel}</b> en iyi fiyatı: <b>{money(own_price)}</b> ({own_best['OTA']}).<br>
            • Fiyat bulunan rakip sayısı: <b>{len(priced)}</b>.<br>
            • <b>{cheaper_count}</b> rakip sizden pahalı, <b>{expensive_count}</b> rakip sizden ucuz.<br>
            • Rakip ortalaması <b>{money(market_avg)}</b>; şu an <b class='{insight_color}'>{position_text}</b>.
        </div>
        """,
        unsafe_allow_html=True,
    )

    display_df = priced.copy()
    display_df["En Düşük Fiyat"] = display_df["En Düşük Fiyat"].apply(money)
    display_df["Bizden Fark TL"] = display_df["Bizden Fark TL"].apply(lambda x: ("+" if x > 0 else "") + money(x))
    display_df["Bizden Fark %"] = display_df["Bizden Fark %"].apply(lambda x: ("+" if x > 0 else "") + f"%{x:.1f}".replace(".", ","))

    st.dataframe(display_df, use_container_width=True, hide_index=True, height=360)

    csv_data = priced.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="Rakip analizi CSV indir",
        data=csv_data,
        file_name=f"216_rakip_analizi_{check_in}_{check_out}.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


# Otel listesi artık hotels.json üzerinden yönetiliyor.
hotels = load_hotels()
HOTEL_NAMES = list(hotels.keys())


def is_eagle_palace(name):
    return name.strip().lower() == "216 eagle palace"


def get_status_meta(name):
    # Şimdilik canlı denetim yalnızca 216 Eagle Palace için açık.
    # hotels.json içinde başka oteller active olsa bile burada bilinçli olarak Yakında gösteriyoruz.
    cfg = hotels.get(name, {})
    active = is_eagle_palace(name)
    return {
        "soon": not active,
        "gold": bool(cfg.get("gold", False)) or active,
        "note": "Aktif otel. Canlı OTA denetimi çalışır." if active else "Yakında aktif edilecek. Şimdilik canlı OTA denetimi kapalı.",
    }


def hotel_select_label(name):
    meta = get_status_meta(name)
    suffix = "  Yakında..." if meta.get("soon") else ""
    return f"{name}{suffix}"


# -------------------------------------------------
# LEFT MENU / HEADER
# -------------------------------------------------
if "selected_module" not in st.session_state:
    st.session_state["selected_module"] = "OTA Denetimi"
if "hotelim_open" not in st.session_state:
    st.session_state["hotelim_open"] = False
if "pazar_open" not in st.session_state:
    st.session_state["pazar_open"] = False

st.markdown(
    """
    <style>
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #05080d 0%, #0b1420 100%) !important;
            border-right: 1px solid rgba(242,195,91,.22);
            width: 320px !important;
        }
        [data-testid="stSidebar"] > div:first-child {
            padding-top: 18px;
            padding-left: 14px;
            padding-right: 14px;
        }
        .side-panel {
            padding: 18px 14px 16px 14px;
            border-radius: 18px;
            background: linear-gradient(145deg, rgba(17,28,42,.96), rgba(8,15,24,.96));
            border: 1px solid rgba(242,195,91,.28);
            box-shadow: 0 18px 48px rgba(0,0,0,.30), inset 0 1px 0 rgba(255,255,255,.04);
            margin-bottom: 18px;
        }
        .side-brand {
            padding: 18px 16px 16px 16px;
            border-radius: 15px;
            background: rgba(7, 14, 23, .70);
            border: 1px solid rgba(242,195,91,.22);
        }
        .side-brand-title {
            color: #f2c35b;
            font-size: 24px;
            font-weight: 950;
            line-height: 1.15;
        }
        .side-brand-sub {
            color: #aeb9c8;
            font-size: 12px;
            font-weight: 800;
            margin-top: 8px;
        }
        [data-testid="stSidebar"] .stButton > button {
            height: 34px;
            justify-content: center;
            text-align: center;
            border-radius: 8px;
            background: transparent !important;
            border: 0 !important;
            color: #f5f7fb !important;
            box-shadow: none !important;
            font-weight: 950;
            padding: 0 6px !important;
            margin: 0 !important;
        }
        [data-testid="stSidebar"] .stButton > button:hover {
            background: rgba(242,195,91,.08) !important;
            color: #f2c35b !important;
        }
        [data-testid="stSidebar"] .stButton > button:focus {
            box-shadow: none !important;
            outline: none !important;
        }
        [data-testid="stSidebar"] .stButton > button p {
            font-size: 13px;
            font-weight: 950;
            margin: 0 !important;
        }
        .menu-spacer { height: 10px; }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown(
        """
        <div class="side-panel">
            <div class="side-brand">
                <div class="side-brand-title">216 Hotels</div>
                <div class="side-brand-sub">Revenue Manager v2.0</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("OTELİM", use_container_width=True, key="cat_hotelim"):
        st.session_state["hotelim_open"] = not st.session_state.get("hotelim_open", False)
        st.rerun()

    if st.session_state.get("hotelim_open", False):
        if st.button("› OTA Denetimi", use_container_width=True, key="menu_ota"):
            st.session_state["selected_module"] = "OTA Denetimi"
            st.rerun()

    st.markdown('<div class="menu-spacer"></div>', unsafe_allow_html=True)

    if st.button("PAZAR", use_container_width=True, key="cat_pazar"):
        st.session_state["pazar_open"] = not st.session_state.get("pazar_open", False)
        st.rerun()

    if st.session_state.get("pazar_open", False):
        if st.button("› Rakip Analizi", use_container_width=True, key="menu_competitor"):
            st.session_state["selected_module"] = "Rakip Analizi"
            st.rerun()

if True:
    active_module = st.session_state.get("selected_module", "OTA Denetimi")
    hero_sub = (
        "OTA fiyatlarını denetle, en ucuz ve en pahalı kanalı gör, oda bazlı fiyat farklarını analiz et."
        if active_module == "OTA Denetimi"
        else "Kartal-Maltepe hattındaki yakın rakipleri analiz et, pazar ortalamasına göre konumunu gör."
    )

    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-title">216 Hotels Revenue Manager v2.0</div>
            <div class="hero-sub">{hero_sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    filter_col0, filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns([1.65, 1, 1, .78, 1.35, .75])
    with filter_col0:
        selected_hotel = st.selectbox(
            "Otel seçimi",
            HOTEL_NAMES,
            index=0,
            format_func=hotel_select_label,
            key="selected_hotel",
        )

        selected_meta = get_status_meta(selected_hotel)
        selected_class = "hotel-status-gold" if selected_meta.get("gold") else "hotel-status-active"
        soon_html = "<span class='hotel-status-soon'>Yakında...</span>" if selected_meta.get("soon") else ""
        note = selected_meta.get("note") or ("Aktif otel. Canlı OTA denetimi çalışır." if not selected_meta.get("soon") else "Bu otel seçilebilir, canlı OTA entegrasyonu yakında aktif edilecek.")
        st.markdown(
            f"""
            <div class="hotel-status-box">
                <span class="{selected_class}">{selected_hotel}</span>{soon_html}
                <div class="hotel-small-note">{note}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with filter_col1:
        check_in = st.date_input("Giriş tarihi", date.today() + timedelta(days=1), format="DD/MM/YYYY")
    with filter_col2:
        check_out = st.date_input("Çıkış tarihi", date.today() + timedelta(days=2), format="DD/MM/YYYY")
    with filter_col3:
        adults = st.number_input("Yetişkin", min_value=1, max_value=4, value=2)

    selected_is_active = is_eagle_palace(selected_hotel)
    with filter_col4:
        st.write("")
        st.write("")
        if active_module == "OTA Denetimi":
            run_button = st.button(
                "OTA Fiyatlarını Denetle",
                use_container_width=True,
                disabled=not selected_is_active,
            )
            competitor_button = False
        else:
            competitor_button = st.button(
                "Rakipleri Analiz Et",
                use_container_width=True,
                disabled=not selected_is_active,
            )
            run_button = False
    with filter_col5:
        st.write("")
        st.write("")
        refresh_button = st.button("Yenile", use_container_width=True)

    if refresh_button:
        st.rerun()

    if not selected_is_active:
        st.warning(f"{selected_hotel} yakında aktif olacak. Şimdilik canlı denetim yalnızca 216 Eagle Palace için açık.")

    hotel_config = hotels.get(selected_hotel) or get_hotel_config(selected_hotel)

    # -------------------------------------------------
    # OTA DENETİMİ MODULE
    # -------------------------------------------------
    if active_module == "OTA Denetimi":
        if run_button:
            if not hotel_config:
                st.error("Seçilen otel hotels.json içinde bulunamadı.")
                st.stop()

            if not selected_is_active:
                st.warning(f"{selected_hotel} yakında aktif olacak. Şimdilik canlı OTA denetimi yalnızca 216 Eagle Palace için açık.")
                st.stop()

            if check_out <= check_in:
                st.error("Çıkış tarihi, giriş tarihinden sonra olmalı.")
                st.stop()

            all_results = collect_ota_prices(hotel_config, check_in, check_out, adults)
            df = normalize_dataframe(pd.DataFrame(all_results))
            fiyatli_df = df[df["Kampanyalı Fiyat"].notna()].copy()

            if fiyatli_df.empty:
                st.warning("Hiç fiyat bulunamadı. Collector çıktılarınızı kontrol edin.")
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.stop()

            min_by_ota = fiyatli_df.groupby("OTA", as_index=False)["Kampanyalı Fiyat"].min().sort_values("Kampanyalı Fiyat")
            cheapest_ota = min_by_ota.iloc[0]
            expensive_ota = min_by_ota.iloc[-1]
            min_row = fiyatli_df.sort_values("Kampanyalı Fiyat").iloc[0]
            max_row = fiyatli_df.sort_values("Kampanyalı Fiyat", ascending=False).iloc[0]
            avg_price = fiyatli_df["Kampanyalı Fiyat"].mean()
            score = revenue_score(fiyatli_df)
            last_update = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

            k1, k2, k3, k4, k5, k6 = st.columns(6)
            kpis = [
                ("En Ucuz OTA", cheapest_ota["OTA"], money(cheapest_ota["Kampanyalı Fiyat"]), "green"),
                ("En Pahalı OTA", expensive_ota["OTA"], money(expensive_ota["Kampanyalı Fiyat"]), "red"),
                ("En Düşük Fiyat", money(min_row["Kampanyalı Fiyat"]), f"{min_row['OTA']} • {min_row['Oda Tipi']}", ""),
                ("En Yüksek Fiyat", money(max_row["Kampanyalı Fiyat"]), f"{max_row['OTA']} • {max_row['Oda Tipi']}", "red"),
                ("Ortalama Fiyat", money(avg_price), "Tüm bulunan fiyatlar", "blue"),
                ("Revenue Score", f"{score}%", "OTA fiyat uyum skoru", "green" if score >= 80 else ""),
            ]
            for col, (label, value, note, cls) in zip([k1, k2, k3, k4, k5, k6], kpis):
                with col:
                    st.markdown(
                        f"""
                        <div class='card kpi-card'>
                            <div class='kpi-label'>{label}</div>
                            <div class='kpi-value {cls}'>{value}</div>
                            <div class='kpi-note'>{note}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            gap = expensive_ota["Kampanyalı Fiyat"] - cheapest_ota["Kampanyalı Fiyat"]
            gap_pct = (gap / cheapest_ota["Kampanyalı Fiyat"] * 100) if cheapest_ota["Kampanyalı Fiyat"] else 0
            if gap_pct > 5.0:
                st.error(
                    f"⚠️ **KRİTİK PARİTE İHLALİ!** "
                    f"Acenteler arasındaki fiyat farkı **%{gap_pct:.1f}** seviyesine ulaştı. "
                    f"En ucuz kanal ({cheapest_ota['OTA']}) ile en pahalı kanal ({expensive_ota['OTA']}) arasındaki makas açık."
                )

            st.markdown("<div class='card section'><div class='section-title'>Revenue Insight</div>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div class='insight-list'>
                    • En ucuz kanal <b>{cheapest_ota['OTA']}</b>, fiyat <b>{money(cheapest_ota['Kampanyalı Fiyat'])}</b>.<br>
                    • En pahalı kanal <b>{expensive_ota['OTA']}</b>, minimum fiyatı <b>{money(expensive_ota['Kampanyalı Fiyat'])}</b>.<br>
                    • OTA minimum fiyat farkı <b>{money(gap)}</b>, oransal fark <b>%{gap_pct:.1f}</b>.<br>
                    • Ortalama fiyat <b>{money(avg_price)}</b>. Revenue Score: <b>{score}%</b>.
                    <div class='score-wrap'><div class='score-bar' style='width:{score}%'></div></div>
                </div>
                """.replace("%{gap_pct:.1f}", f"%{gap_pct:.1f}".replace(".", ",")),
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

            pivot_df = build_pivot(fiyatli_df)
            st.markdown("<div class='card section'><div class='section-title'>Oda Bazlı OTA Karşılaştırması</div>", unsafe_allow_html=True)
            st.markdown(pivot_html(pivot_df), unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            c1, c2 = st.columns([1.1, 1.4])
            with c1:
                st.markdown("<div class='card section'><div class='section-title'>OTA Özet Tablosu</div>", unsafe_allow_html=True)
                st.markdown(ota_summary_html(fiyatli_df), unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with c2:
                st.markdown("<div class='card section'><div class='section-title'>Fırsat Oda İçin Yapılan İndirim Oranları</div>", unsafe_allow_html=True)
                opp_df = opportunity_discount_df(fiyatli_df)
                st.dataframe(opp_df, use_container_width=True, hide_index=True, height=240)
                st.markdown("</div>", unsafe_allow_html=True)

            csv_data = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="Excel için CSV indir",
                data=csv_data,
                file_name=f"216_revenue_manager_{check_in}_{check_out}.csv",
                mime="text/csv",
                use_container_width=True,
            )

            st.markdown(f"<div class='info-box'>Son güncelleme: {last_update} • {fiyatli_df['OTA'].nunique()} OTA başarıyla analiz edildi.</div>", unsafe_allow_html=True)

        else:
            st.markdown("<div class='info-box'>OTELİM > OTA Denetimi ekranındasın. Tarihleri seçip OTA Fiyatlarını Denetle butonuna basınca Revenue Dashboard oluşacak.</div>", unsafe_allow_html=True)

    # -------------------------------------------------
    # RAKİP ANALİZİ MODULE
    # -------------------------------------------------
    else:
        st.markdown("<div class='card section'><div class='section-title'>PAZAR / Rakip Analizi</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='insight-list'>216 Eagle Palace için Kartal-Maltepe hattındaki yakın rakipleri tarih bazlı kontrol eder. Rakip listesi <b>competitors.json</b> dosyasından yönetilir.</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        if competitor_button:
            if not hotel_config:
                st.error("Seçilen otel hotels.json içinde bulunamadı.")
                st.stop()
            render_competitor_analysis(selected_hotel, hotel_config, check_in, check_out, adults)
        else:
            st.markdown("<div class='info-box'>PAZAR > Rakip Analizi ekranındasın. Tarihleri seçip Rakipleri Analiz Et butonuna basınca pazar karşılaştırması oluşacak.</div>", unsafe_allow_html=True)

    st.markdown("<div class='footer'><div class='footer-line'></div><div>Designed by 216 Hotels</div><div class='footer-line'></div></div>", unsafe_allow_html=True)