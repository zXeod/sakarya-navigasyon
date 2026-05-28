"""
Sakarya Akıllı Navigasyon Sistemi - Streamlit Arayüzü

Sol kolon: araç tipi, saat, başlangıç/bitiş noktaları
Sağ kolon: Folium haritası
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import math
from pathlib import Path
import requests
import time
from datetime import datetime
from typing import Optional, List, Dict
import pandas as pd
import json
import os
import streamlit.components.v1 as components

try:
    from streamlit_searchbox import st_searchbox
    _SEARCHBOX_OK = True
except ImportError:
    _SEARCHBOX_OK = False

# Projeyi path'e ekle
import sys
sys.path.insert(0, str(Path(__file__).parent))

from core.graph_loader import get_graph_cached, get_graph_info
from core.routing import SmartRouter
from profiles import vehicle_profiles as vp
from profiles.vehicle_profiles import list_vehicles
from profiles.vehicle_data import (
    VEHICLE_TYPES, CATALOG, BRAND_EMOJI,
    get_brands, get_models, get_engines, get_routing_profile, get_display_label
)


# ==================== GEO BUTTON (query_params tabanlı) ====================
def geo_button_html(field: str, color: str,
                    preserve_start: Optional[tuple] = None,
                    preserve_end: Optional[tuple] = None) -> None:
    """
    st.components.v1.html() ile geolocation butonu göster.
    Konum alındığında form submit ile sayfayı ?{field}_geo=lat,lon ile yeniler.
    Diğer koordinat varsa o da URL'de korunur.
    """
    # Diğer koordinatı URL'de koru
    preserve_html = ""
    if field == "start" and preserve_end:
        preserve_html = (
            f'<input type="hidden" name="end_geo" '
            f'value="{preserve_end[0]},{preserve_end[1]}">'
        )
    elif field == "end" and preserve_start:
        preserve_html = (
            f'<input type="hidden" name="start_geo" '
            f'value="{preserve_start[0]},{preserve_start[1]}">'
        )

    html = f"""
<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;padding:2px;background:transparent}}
.btn{{display:block;width:100%;padding:8px 12px;font-size:13px;cursor:pointer;
      border:none;border-radius:6px;color:white;background:{color};
      font-weight:500;transition:opacity .15s}}
.btn:hover:not(:disabled){{opacity:.85}}
.btn:disabled{{opacity:.5;cursor:default}}
#msg{{font-size:11px;margin-top:5px;min-height:14px;color:#888}}
</style></head><body>
<form id="gf" method="GET" target="_top">
  <input type="hidden" name="{field}_geo" id="coords">
  {preserve_html}
</form>
<button class="btn" id="btn" onclick="getGeo()">📍 Mevcut Konumu Kullan</button>
<div id="msg"></div>
<script>
function getGeo(){{
  var btn=document.getElementById('btn');
  var msg=document.getElementById('msg');
  btn.disabled=true;
  msg.style.color='#888';
  msg.textContent='⏳ Konum alınıyor...';
  if(!navigator.geolocation){{
    msg.style.color='#e53935';
    msg.textContent='❌ Tarayıcınız konum desteklemiyor';
    btn.disabled=false;return;
  }}
  navigator.geolocation.getCurrentPosition(
    function(pos){{
      var lat=pos.coords.latitude.toFixed(6);
      var lon=pos.coords.longitude.toFixed(6);
      msg.style.color='#2e7d32';
      msg.textContent='✅ '+lat+', '+lon;
      document.getElementById('coords').value=lat+','+lon;
      document.getElementById('gf').submit();
    }},
    function(err){{
      var m={{1:'❌ Konum izni reddedildi',2:'❌ Sinyal alınamadı',3:'❌ Zaman aşımı'}};
      msg.style.color='#e53935';
      msg.textContent=m[err.code]||('❌ '+err.message);
      btn.disabled=false;
    }},
    {{enableHighAccuracy:true,timeout:12000,maximumAge:0}}
  );
}}
</script>
</body></html>"""
    components.html(html, height=62)


# ==================== STREAMLIT AYARLARI ====================

st.set_page_config(
    page_title="🗺️ Sakarya Akıllı Navigasyon Sistemi",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Genel iyileştirmeler */
    .block-container { padding-top: 1.5rem !important; }

    /* Konum kartı */
    .loc-card {
        background: linear-gradient(135deg, #1a237e11, #1565C011);
        border: 1px solid #1565C033;
        border-radius: 8px;
        padding: 8px 12px;
        margin: 6px 0;
        font-size: 13px;
    }
    .loc-card-end {
        background: linear-gradient(135deg, #b71c1c11, #C6282811);
        border: 1px solid #C6282833;
    }
    .loc-label { font-weight: 600; color: #555; font-size: 11px; margin-bottom: 2px; }
    .loc-coords { font-family: monospace; font-size: 12px; color: #333; }

    /* Harita click mod */
    .click-hint {
        background: #fff9c4;
        border: 1px solid #f9a825;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
        color: #555;
        margin: 4px 0 8px;
    }

    /* Metrik kutular — dark/light mod uyumlu */
    [data-testid="stMetric"] {
        border: 1px solid rgba(128,128,128,0.25);
        border-radius: 8px;
        padding: 10px 14px !important;
    }

    /* Rota başarı banner */
    .route-banner {
        background: linear-gradient(90deg, #1b5e20, #2e7d32);
        border-radius: 8px;
        padding: 10px 16px;
        color: white;
        font-weight: 600;
        font-size: 15px;
        margin-bottom: 12px;
    }

    /* Sağ kolon sticky */
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child
        > [data-testid="stVerticalBlock"] {
        position: sticky !important;
        top: 3.5rem;
        max-height: calc(100vh - 3.5rem);
        overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)

# ==================== SESSİON STATE ====================

if 'graph' not in st.session_state:
    st.session_state.graph = None

if 'router' not in st.session_state:
    st.session_state.router = None

if 'last_route' not in st.session_state:
    st.session_state.last_route = None

if 'start_lat_live' not in st.session_state:
    st.session_state.start_lat_live = None

if 'start_lon_live' not in st.session_state:
    st.session_state.start_lon_live = None

if 'end_lat_live' not in st.session_state:
    st.session_state.end_lat_live = None

if 'end_lon_live' not in st.session_state:
    st.session_state.end_lon_live = None

if 'route_history' not in st.session_state:
    st.session_state.route_history = []

# Searchbox seçim sonuçları
if 'start_search_result' not in st.session_state:
    st.session_state.start_search_result = None

if 'end_search_result' not in st.session_state:
    st.session_state.end_search_result = None

# Harita tıklama
if '_last_map_click' not in st.session_state:
    st.session_state._last_map_click = None

# Araç karşılaştırma rotaları
if 'comparison_routes' not in st.session_state:
    st.session_state.comparison_routes = {}

if 'comparison_mode' not in st.session_state:
    st.session_state.comparison_mode = False

# Geolocation
if 'start_geo_lat' not in st.session_state:
    st.session_state.start_geo_lat = None

if 'start_geo_lon' not in st.session_state:
    st.session_state.start_geo_lon = None

if 'end_geo_lat' not in st.session_state:
    st.session_state.end_geo_lat = None

if 'end_geo_lon' not in st.session_state:
    st.session_state.end_geo_lon = None

# Araç Seçim Sistemi
if 'vehicle_selection_step' not in st.session_state:
    st.session_state.vehicle_selection_step = 'category'  # category, model, modification, confirm

if 'selected_category' not in st.session_state:
    st.session_state.selected_category = None

if 'selected_model' not in st.session_state:
    st.session_state.selected_model = None

if 'selected_modifications' not in st.session_state:
    st.session_state.selected_modifications = []

if 'saved_profile' not in st.session_state:
    st.session_state.saved_profile = None  # localStorage'dan yüklenecek

if 'app_page' not in st.session_state:
    st.session_state.app_page = 'welcome'  # welcome | select_type | select_brand | select_model | select_engine | select_mods | map

if 'sel_vehicle_type' not in st.session_state:
    st.session_state.sel_vehicle_type = None   # 'otomobil' | 'arazi_suv' | 'motosiklet'

if 'sel_brand' not in st.session_state:
    st.session_state.sel_brand = None

if 'sel_model' not in st.session_state:
    st.session_state.sel_model = None

if 'sel_engine' not in st.session_state:
    st.session_state.sel_engine = None

# Query paramlerinden GPS koordinatlarını oku (geo_button_html form submit'i)
def _read_geo_param(param_name: str) -> Optional[tuple]:
    try:
        raw = st.query_params.get(param_name, "")
        if not raw:
            return None
        lat, lon = map(float, raw.split(','))
        if 40.15 <= lat <= 41.05 and 29.8 <= lon <= 31.3:
            return (lat, lon)
    except Exception:
        pass
    return None

_sgeo = _read_geo_param('start_geo')
_egeo = _read_geo_param('end_geo')

if _sgeo:
    st.session_state.start_geo_lat = _sgeo[0]
    st.session_state.start_geo_lon = _sgeo[1]
    st.session_state.start_lat_live = _sgeo[0]
    st.session_state.start_lon_live = _sgeo[1]

if _egeo:
    st.session_state.end_geo_lat = _egeo[0]
    st.session_state.end_geo_lon = _egeo[1]
    st.session_state.end_lat_live = _egeo[0]
    st.session_state.end_lon_live = _egeo[1]

# URL'yi temizle (koordinatlar session_state'e alındı)
if _sgeo or _egeo:
    st.query_params.clear()


# Session state'teki bozuk koordinatları temizle (Sakarya dışı)
def _is_sakarya(lat, lon):
    return lat is not None and lon is not None and \
           40.15 <= lat <= 41.05 and 29.8 <= lon <= 31.3

for _k_lat, _k_lon in [
    ('start_lat_live', 'start_lon_live'),
    ('end_lat_live', 'end_lon_live'),
    ('start_geo_lat', 'start_geo_lon'),
    ('end_geo_lat', 'end_geo_lon'),
]:
    if not _is_sakarya(st.session_state.get(_k_lat), st.session_state.get(_k_lon)):
        st.session_state[_k_lat] = None
        st.session_state[_k_lon] = None


# ==================== YARDIMCI FONKSİYONLAR ====================

@st.cache_resource
def load_graph():
    """Graph'ı tek seferlik yükle"""
    with st.spinner("Sakarya yol ağı yükleniyor..."):
        return get_graph_cached()


def create_folium_map(graph, route_info=None, start_lat_live=None, start_lon_live=None,
                      end_lat_live=None, end_lon_live=None,
                      start_geo_lat=None, start_geo_lon=None,
                      end_geo_lat=None, end_geo_lon=None,
                      center_lat=40.76, center_lon=30.39, zoom=12,
                      comparison_routes: Optional[Dict] = None):
    """
    Folium haritası oluştur.
    comparison_routes: {vehicle_type: route_info} — karşılaştırma modunda birden fazla rota çizer.
    """

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom,
        tiles='OpenStreetMap'
    )

    # Geolocation marker'ları (mavi — GPS'ten alınan konum)
    if start_geo_lat is not None and start_geo_lon is not None:
        folium.Marker(
            location=[start_geo_lat, start_geo_lon],
            popup="📍 GPS Konumunuz (Başlangıç)",
            tooltip="GPS Konumunuz",
            icon=folium.Icon(color='blue', icon='map-marker'),
        ).add_to(m)

    if end_geo_lat is not None and end_geo_lon is not None:
        folium.Marker(
            location=[end_geo_lat, end_geo_lon],
            popup="📍 GPS Konumunuz (Bitiş)",
            tooltip="GPS Konumunuz",
            icon=folium.Icon(color='blue', icon='map-marker'),
        ).add_to(m)

    # ── Karşılaştırma modu: birden fazla rota ──────────────────────────────────
    if comparison_routes:
        _CMP_COLORS = {
            'binek':      '#1565C0',   # mavi
            'kamyon':     '#B71C1C',   # kırmızı
            'modifiye':   '#2E7D32',   # yeşil
            'motosiklet': '#E65100',   # turuncu
            'bisiklet':   '#6A1B9A',   # mor
        }
        _CMP_LABELS = {
            'binek': '🚗 Binek', 'kamyon': '🚛 Kamyon',
            'modifiye': '🚙 Modifiye', 'motosiklet': '🏍️ Motosiklet',
            'bisiklet': '🚲 Bisiklet',
        }
        _CMP_DASH = {
            'binek': None, 'kamyon': '10 5', 'modifiye': '6 4',
            'motosiklet': '3 6', 'bisiklet': '12 4 3 4',
        }

        all_cmp_pts = []
        for _vt, _ri in comparison_routes.items():
            _coords = _ri.get('coordinates', [])
            if not _coords:
                continue
            _color = _CMP_COLORS.get(_vt, '#555')
            _dash  = _CMP_DASH.get(_vt)
            _lbl   = _CMP_LABELS.get(_vt, _vt.capitalize())
            _dk    = _ri['total_distance_m'] / 1000
            _tm    = int(_ri['estimated_time_minutes'])
            folium.PolyLine(
                locations=_coords,
                color=_color,
                weight=5,
                opacity=0.85,
                dash_array=_dash,
                tooltip=f"{_lbl} | {_dk:.1f} km | {_tm} dk",
                popup=f"<b>{_lbl}</b><br>{_dk:.2f} km — {_tm} dk",
            ).add_to(m)
            all_cmp_pts.extend(_coords)

        # Start / End marker'ları (karşılaştırma için ilk rotadan al)
        _ref = next(iter(comparison_routes.values()))
        _sl, _slon = _ref['start_point']
        _el, _elon = _ref['end_point']
        folium.CircleMarker(location=[_sl, _slon], radius=12,
            popup="🟢 Başlangıç", tooltip="Başlangıç",
            color='white', fill=True, fillColor='#2E7D32', fillOpacity=1.0, weight=3,
        ).add_to(m)
        folium.CircleMarker(location=[_el, _elon], radius=12,
            popup="🔴 Bitiş", tooltip="Bitiş",
            color='white', fill=True, fillColor='#C62828', fillOpacity=1.0, weight=3,
        ).add_to(m)

        # Renk açıklaması (sağ alt köşe)
        legend_html = """
        <div style="position:fixed;bottom:30px;right:10px;z-index:9999;
                    background:rgba(255,255,255,0.92);border:1px solid #ccc;
                    border-radius:8px;padding:10px 14px;font-size:13px;
                    box-shadow:0 2px 8px rgba(0,0,0,.15);">
        <b>Araç Rotaları</b><br>"""
        for _vt, _ri in comparison_routes.items():
            _col = _CMP_COLORS.get(_vt, '#555')
            _lbl = _CMP_LABELS.get(_vt, _vt)
            legend_html += f'<span style="color:{_col};font-weight:700;">━━</span> {_lbl}<br>'
        legend_html += "</div>"
        m.get_root().html.add_child(folium.Element(legend_html))

        if all_cmp_pts:
            sw = [min(c[0] for c in all_cmp_pts), min(c[1] for c in all_cmp_pts)]
            ne = [max(c[0] for c in all_cmp_pts), max(c[1] for c in all_cmp_pts)]
            m.fit_bounds([sw, ne], padding=[55, 55])

        return m

    # ── Tekil rota modu ────────────────────────────────────────────────────────
    # Seçili konum marker'ları — SADECE rota yokken göster
    if route_info is None:
        if start_lat_live is not None and start_lon_live is not None:
            folium.CircleMarker(
                location=[start_lat_live, start_lon_live],
                radius=11,
                popup="📍 Başlangıç",
                tooltip="Başlangıç Noktası",
                color='white', fill=True,
                fillColor='#2E7D32', fillOpacity=1.0, weight=3,
            ).add_to(m)

        if end_lat_live is not None and end_lon_live is not None:
            folium.CircleMarker(
                location=[end_lat_live, end_lon_live],
                radius=11,
                popup="🏁 Bitiş",
                tooltip="Bitiş Noktası",
                color='white', fill=True,
                fillColor='#C62828', fillOpacity=1.0, weight=3,
            ).add_to(m)

    # Rota
    if route_info:
        start_lat, start_lon = route_info['start_point']
        end_lat, end_lon = route_info['end_point']

        coords = route_info.get('coordinates', [])

        # Rota çizgisi — edge geometry kullanır, yol üzerinde gider
        if coords:
            folium.PolyLine(
                locations=coords,
                color='#1565C0',
                weight=6,
                opacity=0.92,
                popup=f"📏 {route_info['total_distance_m']/1000:.2f} km"
            ).add_to(m)

            # Tüm rotayı gösterecek şekilde haritayı otomatik sığdır
            sw = [min(c[0] for c in coords), min(c[1] for c in coords)]
            ne = [max(c[0] for c in coords), max(c[1] for c in coords)]
            m.fit_bounds([sw, ne], padding=[55, 55])

        # Başlangıç marker (yeşil)
        folium.CircleMarker(
            location=[start_lat, start_lon],
            radius=12, popup="🟢 Başlangıç",
            tooltip="Başlangıç",
            color='white', fill=True,
            fillColor='#2E7D32', fillOpacity=1.0, weight=3,
        ).add_to(m)

        # Bitiş marker (kırmızı)
        folium.CircleMarker(
            location=[end_lat, end_lon],
            radius=12, popup="🔴 Bitiş",
            tooltip="Bitiş",
            color='white', fill=True,
            fillColor='#C62828', fillOpacity=1.0, weight=3,
        ).add_to(m)

    return m


def search_photon(query: str) -> List[Dict]:
    """Photon API ile Sakarya odaklı geocoding — çoklu şube/POI desteği."""
    if not query or len(query.strip()) < 2:
        return []

    # İki ayrı istek: isimli POI + bbox içi geniş arama
    searches = [
        {"q": f"{query} Sakarya", "limit": 10, "lang": "tr"},
        {"q": query,              "limit": 10, "lang": "tr",
         "bbox": "29.5,40.3,31.5,41.2"},
    ]

    # (osm_key, osm_value) tuple → ikon (çok daha doğru eşleşme)
    ICONS: Dict[tuple, str] = {
        ("amenity", "university"): "🎓", ("building", "university"): "🎓",
        ("amenity", "school"):     "🏫", ("building", "school"):     "🏫",
        ("amenity", "college"):    "🎓", ("amenity", "tutoring"):    "📚",
        ("amenity", "language_school"): "📚", ("amenity", "driving_school"): "🚗",
        ("amenity", "kindergarten"): "🧒",
        ("amenity", "hospital"):   "🏥", ("amenity", "clinic"):      "🏥",
        ("amenity", "pharmacy"):   "💊", ("amenity", "dentist"):     "🦷",
        ("amenity", "doctors"):    "👨‍⚕️",
        ("railway", "station"):    "🚂", ("railway", "halt"):        "🚉",
        ("amenity", "bus_station"): "🚌", ("highway", "bus_stop"):   "🚌",
        ("amenity", "fuel"):       "⛽", ("amenity", "parking"):     "🅿️",
        ("amenity", "restaurant"): "🍽️", ("amenity", "cafe"):       "☕",
        ("amenity", "fast_food"):  "🍔",
        ("shop",    "supermarket"): "🛒", ("amenity", "bank"):       "🏦",
        ("amenity", "atm"):        "💳", ("shop",    "mall"):        "🏬",
        ("amenity", "police"):     "👮", ("amenity", "fire_station"): "🚒",
        ("amenity", "post_office"): "📮", ("amenity", "townhall"):   "🏛️",
        ("amenity", "courthouse"): "⚖️",
        ("amenity", "mosque"):     "🕌", ("amenity", "place_of_worship"): "🕌",
        ("leisure", "sports_centre"): "🏋️", ("leisure", "stadium"): "🏟️",
        ("leisure", "park"):       "🌳",
        ("tourism", "hotel"):      "🏨", ("tourism", "motel"):       "🏨",
        ("place",   "city"):       "🏙️", ("place",   "town"):        "🏘️",
        ("place",   "village"):    "🏡", ("place",   "suburb"):      "📍",
        ("place",   "neighbourhood"): "📍",
    }

    all_features: list = []
    for params in searches:
        try:
            resp = requests.get(
                "https://photon.komoot.io/api/",
                params=params,
                timeout=5,
                headers={"User-Agent": "SakaryaNavApp/1.0"},
            )
            resp.raise_for_status()
            all_features.extend(resp.json().get("features", []))
        except Exception:
            continue

    results: List[Dict] = []
    seen_coords: set = set()
    seen_name_district: set = set()

    for f in all_features:
        props  = f.get("properties", {})
        coords = f.get("geometry", {}).get("coordinates", [])
        if len(coords) < 2:
            continue

        # Photon [lon, lat] sırasıyla döndürür
        lon, lat = float(coords[0]), float(coords[1])
        if not (40.3 <= lat <= 41.2 and 29.5 <= lon <= 31.5):
            continue

        # Koordinat deduplicate (~110 m hassasiyet)
        coord_key = (round(lat, 3), round(lon, 3))
        if coord_key in seen_coords:
            continue
        seen_coords.add(coord_key)

        osm_key     = props.get("osm_key", "")
        osm_value   = props.get("osm_value", "")
        name        = props.get("name", "")
        street      = props.get("street", "")
        housenumber = props.get("housenumber", "")
        city        = props.get("city") or props.get("county", "Sakarya")
        district    = props.get("district") or props.get("suburb", "")

        primary = name or street or "Bilinmeyen"

        # Farklı ilçedeki aynı isimli şubeler KALSIN; sadece isimsiz kopyaları at
        nd_key = f"{primary.lower()}_{district.lower()}"
        if nd_key in seen_name_district and not housenumber:
            continue
        seen_name_district.add(nd_key)

        icon = ICONS.get((osm_key, osm_value), "📍")

        # Alt satır: sokak + numara + ilçe + şehir
        addr_parts = []
        if street and name:
            addr_parts.append(f"{street} {housenumber}".strip())
        elif housenumber:
            addr_parts.append(f"No:{housenumber}")
        if district and district != primary:
            addr_parts.append(district)
        if city and city != primary:
            addr_parts.append(city)

        subtitle = ", ".join(addr_parts[:3])
        label    = f"{icon} {primary}"
        if subtitle:
            label += f"  ·  {subtitle}"

        results.append({
            "label": label,
            "lat":   lat,
            "lon":   lon,
            "display_name": f"{primary}, {district or city}",
        })

        if len(results) >= 8:
            break

    return results


def _photon_wrapper_start(query: str):
    """st_searchbox için (label, değer) tuple listesi döndürür."""
    return [(r["label"], r) for r in search_photon(query)]


def _photon_wrapper_end(query: str):
    return [(r["label"], r) for r in search_photon(query)]


# ==================== PROFIL YÖNETIMI ====================

def get_profiles_dir():
    """Profil dosyaları klasörünü al"""
    profiles_dir = Path(__file__).parent / "data" / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    return profiles_dir

def save_profile(profile_data: dict) -> bool:
    """Profili dosyaya kaydet"""
    try:
        profiles_dir = get_profiles_dir()
        
        # Profil adından dosya adı oluştur
        profile_name = profile_data.get('name', 'Profil')
        filename = f"{profile_name.replace(' ', '_').lower()}.json"
        filepath = profiles_dir / filename
        
        # Dosyaya kaydet
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        st.error(f"❌ Profil kaydı hatası: {str(e)}")
        return False

def load_saved_profiles() -> List[Dict]:
    """Tüm kaydedilmiş profilleri yükle"""
    try:
        profiles_dir = get_profiles_dir()
        profiles = []
        
        for file in profiles_dir.glob("*.json"):
            with open(file, 'r', encoding='utf-8') as f:
                profile = json.load(f)
                profiles.append(profile)
        
        return sorted(profiles, key=lambda x: x.get('timestamp', ''), reverse=True)
    except:
        return []

def load_profile_by_name(profile_name: str) -> Optional[Dict]:
    """Adına göre profil yükle"""
    try:
        profiles_dir = get_profiles_dir()
        filename = f"{profile_name.replace(' ', '_').lower()}.json"
        filepath = profiles_dir / filename
        
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    
    return None


def calculate_route(start_lat, start_lon, end_lat, end_lon,
                   vehicle_type, hour):
    """Rota hesapla ve geçmişe ekle"""
    # Sakarya sınır kontrolü — geçersiz koordinatları erkenden yakala
    SLAT = (40.15, 41.05)
    SLON = (29.8, 31.3)
    for lbl, la, lo in [("Başlangıç", start_lat, start_lon), ("Bitiş", end_lat, end_lon)]:
        if not (SLAT[0] <= la <= SLAT[1] and SLON[0] <= lo <= SLON[1]):
            st.error(
                f"❌ {lbl} koordinatı Sakarya dışında: {la:.4f}, {lo:.4f}\n\n"
                "Lütfen arama yaparak veya haritaya tıklayarak yeniden seçin."
            )
            return None
    try:
        router = SmartRouter(st.session_state.graph, vehicle_type, hour)
        st.session_state.router = router

        route_info = router.find_route(start_lat, start_lon, end_lat, end_lon)
        st.session_state.last_route = route_info
        
        # Geçmiş rotaya ekle
        history_item = {
            'vehicle': vehicle_type,
            'distance': route_info['total_distance_m'] / 1000,
            'time': f"{route_info['estimated_time_minutes']:.0f} dk",
            'hour': hour,
            'route_info': route_info,
            'timestamp': datetime.now().strftime('%H:%M')
        }
        
        st.session_state.route_history.insert(0, history_item)
        st.session_state.route_history = st.session_state.route_history[:5]
        
        return route_info
    except Exception as e:
        st.error(f"❌ Rota hesaplama hatası: {str(e)}")
        return None



# ==================== ANA ARAYÜZ ====================

# ── Sayfa: Hoşgeldiniz ──────────────────────────────────────────────────────
if st.session_state.app_page == 'welcome':
    st.markdown("""
    <div style='text-align:center; padding: 60px 20px 30px;'>
        <div style='font-size:80px; margin-bottom:16px;'>🗺️</div>
        <h1 style='font-size:2.8rem; font-weight:800; margin-bottom:8px;'>
            Sakarya Akıllı Navigasyon Sistemi
        </h1>
        <p style='font-size:1.1rem; color:#888; margin-bottom:40px;'>
            Araç tipinize göre optimize edilmiş rota planlama
        </p>
    </div>
    """, unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        if st.button("🚀  Başla — Aracını Seç", use_container_width=True, type="primary"):
            st.session_state.app_page = 'select_type'
            st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style='text-align:center; color:#999; font-size:13px;'>
        OSMnx • NetworkX • Folium • Streamlit<br>
        Sakarya Uygulamalı Bilimler Üniversitesi Kariyer Zirvesi 2026
        </div>
        """, unsafe_allow_html=True)

# ── Sayfa: Araç Tipi Seç ───────────────────────────────────────────────────
elif st.session_state.app_page == 'select_type':
    st.markdown("## 🚘 Vasıta Türünü Seçin")
    st.caption("Hangi araç ile gitmek istiyorsunuz?")
    st.markdown("---")

    _types = [
        ('otomobil', '🚗', 'Otomobil', 'Sedan, hatchback, steyşın'),
        ('arazi_suv', '🚙', 'Arazi / SUV / Pickup', 'SUV, crossover, pickup kamyonet'),
        ('motosiklet', '🏍️', 'Motosiklet', 'Naked, sport, scooter'),
    ]

    for _vtype, _emoji, _label, _desc in _types:
        _col1, _col2 = st.columns([1, 6])
        with _col1:
            st.markdown(f"<div style='font-size:48px; text-align:center; padding-top:4px;'>{_emoji}</div>",
                        unsafe_allow_html=True)
        with _col2:
            if st.button(f"**{_label}**\n\n{_desc}", use_container_width=True, key=f"type_{_vtype}"):
                st.session_state.sel_vehicle_type = _vtype
                st.session_state.sel_brand = None
                st.session_state.sel_model = None
                st.session_state.sel_engine = None
                st.session_state.app_page = 'select_brand'
                st.rerun()
        st.markdown("")

# ── Sayfa: Marka Seç ───────────────────────────────────────────────────────
elif st.session_state.app_page == 'select_brand':
    _vtype = st.session_state.sel_vehicle_type
    _type_label = get_display_label(_vtype)

    _back_col, _title_col = st.columns([1, 8])
    with _back_col:
        if st.button("← Geri"):
            st.session_state.app_page = 'select_type'
            st.rerun()
    with _title_col:
        st.markdown(f"## {_type_label} — Marka Seçin")

    st.caption("Sakarya'da popüler markalar")
    st.markdown("---")

    _brands = get_brands(_vtype)
    # 3'lü grid
    _rows = [_brands[i:i+3] for i in range(0, len(_brands), 3)]
    for _row in _rows:
        _cols = st.columns(3)
        for _ci, _brand in enumerate(_row):
            with _cols[_ci]:
                _bemoji = BRAND_EMOJI.get(_brand, '🚘')
                if st.button(f"{_bemoji} {_brand}", use_container_width=True, key=f"brand_{_brand}"):
                    st.session_state.sel_brand = _brand
                    st.session_state.sel_model = None
                    st.session_state.sel_engine = None
                    st.session_state.app_page = 'select_model'
                    st.rerun()

# ── Sayfa: Model Seç ───────────────────────────────────────────────────────
elif st.session_state.app_page == 'select_model':
    _vtype = st.session_state.sel_vehicle_type
    _brand = st.session_state.sel_brand

    _back_col, _title_col = st.columns([1, 8])
    with _back_col:
        if st.button("← Geri"):
            st.session_state.app_page = 'select_brand'
            st.rerun()
    with _title_col:
        _bemoji = BRAND_EMOJI.get(_brand, '🚘')
        st.markdown(f"## {_bemoji} {_brand} — Model Seçin")

    st.caption(f"Sakarya'da popüler {_brand} modelleri")
    st.markdown("---")

    _models = get_models(_vtype, _brand)
    _rows = [_models[i:i+3] for i in range(0, len(_models), 3)]
    for _row in _rows:
        _cols = st.columns(3)
        for _ci, _model in enumerate(_row):
            with _cols[_ci]:
                if st.button(_model, use_container_width=True, key=f"model_{_model}"):
                    st.session_state.sel_model = _model
                    st.session_state.sel_engine = None
                    st.session_state.app_page = 'select_engine'
                    st.rerun()

# ── Sayfa: Motor Seç ───────────────────────────────────────────────────────
elif st.session_state.app_page == 'select_engine':
    _vtype = st.session_state.sel_vehicle_type
    _brand = st.session_state.sel_brand
    _model = st.session_state.sel_model

    _back_col, _title_col = st.columns([1, 8])
    with _back_col:
        if st.button("← Geri"):
            st.session_state.app_page = 'select_model'
            st.rerun()
    with _title_col:
        st.markdown(f"## {_brand} {_model} — Motor Seçin")

    st.caption("Motor hacmi ve güç")
    st.markdown("---")

    _engines = get_engines(_vtype, _brand, _model)
    _rows = [_engines[i:i+2] for i in range(0, len(_engines), 2)]
    for _row in _rows:
        _cols = st.columns(2)
        for _ci, _eng in enumerate(_row):
            with _cols[_ci]:
                if st.button(f"⚙️ {_eng}", use_container_width=True, key=f"eng_{_eng}"):
                    st.session_state.sel_engine = _eng
                    st.session_state.app_page = 'select_mods'
                    st.rerun()

# ── Sayfa: Ek Tercihler / Modifikasyonlar ──────────────────────────────────
elif st.session_state.app_page == 'select_mods':
    _vtype = st.session_state.sel_vehicle_type
    _brand = st.session_state.sel_brand
    _model = st.session_state.sel_model
    _engine = st.session_state.sel_engine

    st.markdown(f"## ⚙️ {_brand} {_model} {_engine}")
    st.markdown("### Ek Tercihler (İsteğe Bağlı)")
    st.caption("Aracınızda modifikasyon var mı?")
    st.markdown("---")

    _available_mods = vp.get_modifications()
    _selected = list(st.session_state.selected_modifications)

    _mod_cols = st.columns(2)
    for _mi, (_mkey, _mdata) in enumerate(_available_mods.items()):
        with _mod_cols[_mi % 2]:
            _checked = st.checkbox(
                f"{_mdata.get('emoji','🔧')} {_mdata['name']}",
                value=_mkey in _selected,
                key=f"mod_{_mkey}",
                help=_mdata.get('effect','')
            )
            if _checked and _mkey not in _selected:
                _selected.append(_mkey)
            elif not _checked and _mkey in _selected:
                _selected.remove(_mkey)

    st.session_state.selected_modifications = _selected
    st.markdown("---")

    _btn_cols = st.columns(2)
    with _btn_cols[0]:
        if st.button("⏭️ Modifikasyon Yok, Devam Et", use_container_width=True):
            st.session_state.selected_modifications = []
            # Araç profilini ayarla
            _profile = get_routing_profile(_vtype)
            st.session_state.selected_category = _vtype
            st.session_state.selected_model = f"{_brand} {_model}"
            st.session_state.saved_profile = {
                'name': f"{_brand} {_model} {_engine}",
                'routing_profile': _profile,
                'modifications': [],
                'vehicle_display': f"{VEHICLE_TYPES[_vtype]['emoji']} {_brand} {_model}",
                'engine': _engine,
                'brand': _brand,
                'model_name': _model,
                'vtype': _vtype,
            }
            st.session_state.vehicle_selection_step = 'confirm'
            st.session_state.app_page = 'map'
            st.rerun()
    with _btn_cols[1]:
        if st.button("✅ Onayla ve Haritaya Git", use_container_width=True, type="primary"):
            _profile = get_routing_profile(_vtype)
            st.session_state.saved_profile = {
                'name': f"{_brand} {_model} {_engine}",
                'routing_profile': _profile,
                'modifications': _selected,
                'vehicle_display': f"{VEHICLE_TYPES[_vtype]['emoji']} {_brand} {_model}",
                'engine': _engine,
                'brand': _brand,
                'model_name': _model,
                'vtype': _vtype,
            }
            st.session_state.vehicle_selection_step = 'confirm'
            st.session_state.app_page = 'map'
            st.rerun()

# ── Sayfa: Harita ──────────────────────────────────────────────────────────
elif st.session_state.app_page == 'map':

    # ── Araç Bilgi Kartı (sol üst) ──
    if st.session_state.saved_profile:
        _sp = st.session_state.saved_profile
        _vemoji = VEHICLE_TYPES.get(_sp.get('vtype', ''), {}).get('emoji', '🚗')
        _card_col1, _card_col2, _card_col3 = st.columns([3, 6, 1])
        with _card_col1:
            st.markdown(
                f"<div style='background:linear-gradient(135deg,#1a237e18,#1565C018);"
                f"border:1px solid #1565C033;border-radius:10px;padding:10px 14px;"
                f"display:flex;align-items:center;gap:10px;'>"
                f"<span style='font-size:36px;'>{_vemoji}</span>"
                f"<div><div style='font-weight:700;font-size:14px;'>{_sp.get('brand','')} {_sp.get('model_name','')}</div>"
                f"<div style='font-size:11px;color:#888;'>&#9881;&#65039; {_sp.get('engine','')}</div></div>"
                f"</div>",
                unsafe_allow_html=True
            )
        with _card_col3:
            if st.button("↩️", help="Araç değiştir", key="change_vehicle_btn"):
                st.session_state.app_page = 'select_type'
                st.session_state.saved_profile = None
                st.session_state.last_route = None
                st.rerun()

    # Başlık + Yeni Rota Butonu
    col_title, col_btn = st.columns([4, 1])
    with col_title:
        st.title("🗺️ Sakarya Akıllı Navigasyon Sistemi")
        st.text("Araç tipi ve yol yüzeyi temelli optimal rota planlama")

    with col_btn:
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)  # Spacing
        if st.button("🔄 Yeni Rota", use_container_width=True, key="new_route_btn"):
            # Form sıfırla
            st.session_state.last_route = None
            st.session_state.start_lat_live = None
            st.session_state.start_lon_live = None
            st.session_state.end_lat_live = None
            st.session_state.end_lon_live = None
            # Adres ve arama state'ini sıfırla
            for key in list(st.session_state.keys()):
                if 'searchbox' in key or 'address' in key or 'lat_input' in key or 'lon_input' in key:
                    del st.session_state[key]
            st.session_state.start_search_result = None
            st.session_state.end_search_result = None
            st.session_state._last_map_click = None
            st.rerun()

    # Ana layout: sol ve sağ kolonlar
    col1, col2 = st.columns([1, 2.5], gap="large")

    # ==================== SOL KOLON ====================
    with col1:
        st.subheader("📋 Rota Planlama")

        # Graph yük kontrolü
        if st.session_state.graph is None:
            st.session_state.graph = load_graph()

        # Graph bilgisi
        with st.expander("ℹ️ Sistem Bilgisi"):
            graph_info = get_graph_info(st.session_state.graph)
            st.metric("İçinde Düğüm", f"{graph_info['nodes']:,}")
            st.metric("İçinde Kenar", f"{graph_info['edges']:,}")
            st.metric("Cache Boyutu", f"{graph_info['cache_size_mb']:.2f} MB")

        st.divider()

        # Aktif profili göster
        if st.session_state.saved_profile:
            with st.container(border=True):
                st.caption("✅ Aktif Araç Profili")
                _ap = st.session_state.saved_profile
                st.write(f"**{_ap.get('name', 'Bilinmiyor')}**")
                st.caption(f"Profil: {_ap.get('routing_profile', 'binek')}")
                vehicle_type = _ap['routing_profile']
        else:
            vehicle_type = 'binek'  # Default

        st.divider()

        # Saat seçimi (trafik için)
        st.subheader("🕐 Seyahat Saati")
        hour = st.slider(
            "Saati Seçin (Trafik Tahmini)",
            min_value=0,
            max_value=23,
            value=12,
            format="%d:00"
        )

        traffic_descriptions = {
            6: "🚨 Sabah Trafiği",
            7: "🚨 Sabah Trafiği (Yoğun)",
            8: "🚨 Sabah Trafiği (En Yoğun)",
            12: "✅ Normal Saatler",
            17: "🚨 Akşam Trafiği",
            18: "🚨 Akşam Trafiği (Yoğun)",
            19: "🚨 Akşam Trafiği (En Yoğun)",
        }

        if hour in traffic_descriptions:
            st.info(traffic_descriptions[hour])

        st.divider()

        # ==================== BAŞLANGIÇ NOKTASI ====================
        st.subheader("📍 Başlangıç Noktası")

        # GPS butonu — form submit ile query_params üzerinden çalışır
        _preserve_end = (
            (st.session_state.end_lat_live, st.session_state.end_lon_live)
            if st.session_state.end_lat_live else None
        )
        geo_button_html("start", "#1565C0", preserve_end=_preserve_end)

        # Seçili konum göster + temizle
        if st.session_state.start_lat_live:
            _sc1, _sc2 = st.columns([4, 1])
            with _sc1:
                st.markdown(
                    f"<div class='loc-card'>"
                    f"<div class='loc-label'>SEÇİLİ BAŞLANGIÇ</div>"
                    f"<div class='loc-coords'>📍 {st.session_state.start_lat_live:.5f}, {st.session_state.start_lon_live:.5f}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            with _sc2:
                st.markdown("<div style='margin-top:14px'></div>", unsafe_allow_html=True)
                if st.button("✕", key="clear_start", help="Başlangıç noktasını temizle", use_container_width=True):
                    st.session_state.start_lat_live = None
                    st.session_state.start_lon_live = None
                    st.session_state.start_geo_lat = None
                    st.session_state.start_geo_lon = None
                    st.rerun()

        # Adres arama — Photon autocomplete
        if _SEARCHBOX_OK:
            _start_sel = st_searchbox(
                _photon_wrapper_start,
                key="start_searchbox",
                placeholder="Ör: Sakarya Üniversitesi, Adapazarı Gar, Hastane...",
                label="🔍 Adres Ara",
                clear_on_submit=False,
                debounce=300,
                rerun_on_update=True,
            )
            if _start_sel is not None:
                st.session_state.start_lat_live = _start_sel["lat"]
                st.session_state.start_lon_live = _start_sel["lon"]
                st.session_state.start_search_result = _start_sel
                st.toast(f"📍 {_start_sel['display_name']} başlangıç olarak seçildi", icon="✅")
        else:
            # Fallback: searchbox yüklü değilse basit text_input
            _sq = st.text_input(
                "🔍 Adres Ara (Sakarya)",
                placeholder="Ör: Üniversite, Gar, Hastane...",
                key="start_address_query_fb",
            )
            if st.button("🔍 Ara", key="search_start_fb_btn"):
                _fb_results = search_photon(_sq)
                if _fb_results:
                    _r0 = _fb_results[0]
                    st.session_state.start_lat_live = _r0["lat"]
                    st.session_state.start_lon_live = _r0["lon"]
                    st.toast(f"📍 {_r0['display_name']} seçildi", icon="✅")
                    st.rerun()

        start_lat = st.session_state.start_lat_live if st.session_state.start_lat_live else 40.76
        start_lon = st.session_state.start_lon_live if st.session_state.start_lon_live else 30.39

        # ==================== BİTİŞ NOKTASI ====================
        st.subheader("🏁 Bitiş Noktası")

        # GPS butonu
        _preserve_start = (
            (st.session_state.start_lat_live, st.session_state.start_lon_live)
            if st.session_state.start_lat_live else None
        )
        geo_button_html("end", "#C62828", preserve_start=_preserve_start)

        # Seçili konum göster + temizle
        if st.session_state.end_lat_live:
            _ec1, _ec2 = st.columns([4, 1])
            with _ec1:
                st.markdown(
                    f"<div class='loc-card loc-card-end'>"
                    f"<div class='loc-label'>SEÇİLİ BİTİŞ</div>"
                    f"<div class='loc-coords'>🏁 {st.session_state.end_lat_live:.5f}, {st.session_state.end_lon_live:.5f}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            with _ec2:
                st.markdown("<div style='margin-top:14px'></div>", unsafe_allow_html=True)
                if st.button("✕", key="clear_end", help="Bitiş noktasını temizle", use_container_width=True):
                    st.session_state.end_lat_live = None
                    st.session_state.end_lon_live = None
                    st.session_state.end_geo_lat = None
                    st.session_state.end_geo_lon = None
                    st.rerun()

        # Adres arama — Photon autocomplete
        if _SEARCHBOX_OK:
            _end_sel = st_searchbox(
                _photon_wrapper_end,
                key="end_searchbox",
                placeholder="Ör: Hendek, Akyazı Devlet Hastanesi, Gar...",
                label="🔍 Adres Ara",
                clear_on_submit=False,
                debounce=300,
                rerun_on_update=True,
            )
            if _end_sel is not None:
                st.session_state.end_lat_live = _end_sel["lat"]
                st.session_state.end_lon_live = _end_sel["lon"]
                st.session_state.end_search_result = _end_sel
                st.toast(f"🏁 {_end_sel['display_name']} bitiş olarak seçildi", icon="✅")
        else:
            # Fallback
            _eq = st.text_input(
                "🔍 Adres Ara (Sakarya)",
                placeholder="Ör: Valilik, Gar, Hastane...",
                key="end_address_query_fb",
            )
            if st.button("🔍 Ara", key="search_end_fb_btn"):
                _fb_results = search_photon(_eq)
                if _fb_results:
                    _r0 = _fb_results[0]
                    st.session_state.end_lat_live = _r0["lat"]
                    st.session_state.end_lon_live = _r0["lon"]
                    st.toast(f"🏁 {_r0['display_name']} seçildi", icon="✅")
                    st.rerun()

        end_lat = st.session_state.end_lat_live if st.session_state.end_lat_live else 40.75
        end_lon = st.session_state.end_lon_live if st.session_state.end_lon_live else 30.40

        st.divider()

        # Rota hesapla düğmesi
        if st.button("🔍 Rota Hesapla", use_container_width=True, type="primary"):
            if st.session_state.start_lat_live is None:
                st.warning("⚠️ Lütfen önce bir **başlangıç noktası** seçin.")
            elif st.session_state.end_lat_live is None:
                st.warning("⚠️ Lütfen önce bir **bitiş noktası** seçin.")
            else:
                with st.spinner("Optimal rota hesaplanıyor..."):
                    route_info = calculate_route(
                        start_lat, start_lon,
                        end_lat, end_lon,
                        vehicle_type, hour
                    )
                    st.rerun()

        # Rota silme düğmesi
        if st.session_state.last_route:
            if st.button("🗑️ Rotayı Temizle", use_container_width=True):
                st.session_state.last_route = None
                st.rerun()

    # ==================== SAĞ KOLON ====================
    with col2:
        st.subheader("🗺️ Harita")

        _VEMOJI = {'binek': '🚗', 'kamyon': '🚚', 'motosiklet': '🏍️', 'bisiklet': '🚴', 'modifiye': '🚙'}

        # Geçmiş Rotalar (kompakt)
        if st.session_state.route_history:
            with st.expander(f"📜 Geçmiş Rotalar ({len(st.session_state.route_history)})", expanded=False):
                for idx, hist in enumerate(st.session_state.route_history):
                    _he = _VEMOJI.get(hist['vehicle'], '🚗')
                    _hc1, _hc2 = st.columns([1, 3])
                    with _hc1:
                        if st.button(_he, key=f"history_{idx}", use_container_width=True,
                                     help=f"{hist['distance']:.1f} km | {hist['time']}"):
                            st.session_state.last_route = hist['route_info']
                            st.rerun()
                    with _hc2:
                        st.caption(
                            f"**{hist['vehicle'].capitalize()}** · {hist['distance']:.1f} km · "
                            f"{hist['time']} · {hist['timestamp']}"
                        )

        if st.session_state.graph:
            # ── Haritayı oluştur ──
            _cmp_routes = (
                st.session_state.comparison_routes
                if st.session_state.comparison_mode and st.session_state.comparison_routes
                else None
            )
            if _cmp_routes:
                # Karşılaştırma modu: tüm araç rotalarını haritada göster
                folium_map = create_folium_map(
                    st.session_state.graph,
                    comparison_routes=_cmp_routes,
                    start_geo_lat=st.session_state.start_geo_lat,
                    start_geo_lon=st.session_state.start_geo_lon,
                    end_geo_lat=st.session_state.end_geo_lat,
                    end_geo_lon=st.session_state.end_geo_lon
                )
            elif st.session_state.last_route:
                folium_map = create_folium_map(
                    st.session_state.graph,
                    route_info=st.session_state.last_route,
                    start_lat_live=st.session_state.start_lat_live,
                    start_lon_live=st.session_state.start_lon_live,
                    end_lat_live=st.session_state.end_lat_live,
                    end_lon_live=st.session_state.end_lon_live,
                    start_geo_lat=st.session_state.start_geo_lat,
                    start_geo_lon=st.session_state.start_geo_lon,
                    end_geo_lat=st.session_state.end_geo_lat,
                    end_geo_lon=st.session_state.end_geo_lon
                )
            else:
                folium_map = create_folium_map(
                    st.session_state.graph,
                    start_lat_live=st.session_state.start_lat_live,
                    start_lon_live=st.session_state.start_lon_live,
                    end_lat_live=st.session_state.end_lat_live,
                    end_lon_live=st.session_state.end_lon_live,
                    start_geo_lat=st.session_state.start_geo_lat,
                    start_geo_lon=st.session_state.start_geo_lon,
                    end_geo_lat=st.session_state.end_geo_lat,
                    end_geo_lon=st.session_state.end_geo_lon
                )

            # ── Harita click modu seçici ──
            click_mode = st.radio(
                "Haritadan konum seç",
                ["— Devre Dışı", "📍 Başlangıç Seç", "🏁 Bitiş Seç"],
                horizontal=True,
                key="map_click_mode",
            )
            if click_mode != "— Devre Dışı":
                st.markdown(
                    f"<div class='click-hint'>🖱️ Haritada istediğiniz noktaya tıklayın — "
                    f"<b>{click_mode.split(' ', 1)[1]}</b> olarak ayarlanacak</div>",
                    unsafe_allow_html=True
                )

            # ── Ana harita — TEK st_folium çağrısı ──
            map_data = st_folium(
                folium_map,
                use_container_width=True,
                height=560,
                returned_objects=["last_clicked"],
                key="main_folium_map",
            )

            # ── Tıklama işle ──
            if map_data and map_data.get('last_clicked') and click_mode != "— Devre Dışı":
                lc = map_data['last_clicked']
                _ck = (round(lc['lat'], 5), round(lc['lng'], 5))
                if _ck != st.session_state._last_map_click:
                    st.session_state._last_map_click = _ck
                    if click_mode == "📍 Başlangıç Seç":
                        st.session_state.start_lat_live = lc['lat']
                        st.session_state.start_lon_live = lc['lng']
                        st.toast(f"📍 Başlangıç seçildi: {lc['lat']:.4f}, {lc['lng']:.4f}", icon="✅")
                    elif click_mode == "🏁 Bitiş Seç":
                        st.session_state.end_lat_live = lc['lat']
                        st.session_state.end_lon_live = lc['lng']
                        st.toast(f"🏁 Bitiş seçildi: {lc['lat']:.4f}, {lc['lng']:.4f}", icon="✅")
                    st.rerun()

            # ── Rota bilgisi (haritanın altında) ──
            if st.session_state.last_route:
                _r = st.session_state.last_route
                _surfaces = _r.get('surfaces', [])
                _mods = st.session_state.saved_profile.get('modifications', []) if st.session_state.saved_profile else []
                _vehicle = _r.get('vehicle_type', 'binek')
                _dist_km = _r['total_distance_m'] / 1000

                st.markdown(
                    f"<div class='route-banner'>"
                    f"✅ Rota Bulundu &nbsp;|&nbsp; "
                    f"📏 {_dist_km:.2f} km &nbsp;|&nbsp; "
                    f"⏱️ {int(_r['estimated_time_minutes'])} dk &nbsp;|&nbsp; "
                    f"{_VEMOJI.get(_vehicle, '🚗')} {_vehicle.capitalize()}"
                    f"</div>",
                    unsafe_allow_html=True
                )

                with st.expander("📊 Rota Detayları", expanded=False):
                    # Özet metrikler
                    _dc1, _dc2, _dc3 = st.columns(3)
                    with _dc1:
                        st.metric("📏 Mesafe", f"{_dist_km:.2f} km")
                    with _dc2:
                        st.metric("⏱️ Süre", f"{int(_r['estimated_time_minutes'])} dk")
                    with _dc3:
                        st.metric("🕐 Saat", f"{_r['hour']:02d}:00",
                                  delta=f"Trafik ×{_r['traffic_factor']:.2f}", delta_color="off")

                    st.divider()

                    # Yol kalitesi
                    _quality = vp.calculate_road_quality_score(_surfaces)
                    _qc1, _qc2 = st.columns([1, 3])
                    with _qc1:
                        st.markdown(f"### {_quality['emoji']}")
                    with _qc2:
                        st.write(f"**Yol Kalitesi:** {_quality['quality']} ({_quality['score']}/10)")
                        st.caption(_quality['description'])

                    # Hasar riski (sadece modifiye araçlarda)
                    if _mods:
                        st.divider()
                        _damage = vp.calculate_damage_risk(_surfaces, _mods)
                        _dd1, _dd2 = st.columns([1, 3])
                        with _dd1:
                            st.markdown(f"### {_damage['emoji']}")
                        with _dd2:
                            st.write(f"**Hasar Riski:** {_damage['description']}")
                            st.caption(
                                f"Risk: {_damage['risk_level']:.1f}% "
                                f"({_damage['count_bad_surfaces']}/{_damage['total_surfaces']} kötü yüzey)"
                            )

                    st.divider()

                    # Maliyet
                    _cost = vp.calculate_cost_estimate(_dist_km, _surfaces, _mods, _vehicle)
                    st.write("**💰 Maliyet Tahmini**")
                    _cc1, _cc2, _cc3 = st.columns(3)
                    with _cc1:
                        st.metric("Yakıt", f"{_cost['fuel_consumption_liters']} L",
                                  f"{_cost['fuel_cost_tl']} TL")
                    with _cc2:
                        st.metric("Bakım", f"{_cost['maintenance_cost_tl']} TL")
                    with _cc3:
                        st.metric("Toplam", f"{_cost['total_cost_tl']} TL",
                                  f"{_cost['cost_per_km']} TL/km", delta_color="off")

                # ── Alternatif Araç Karşılaştırması (tablo + haritada renkli rotalar) ──
                st.divider()

                _cmp_label = (
                    "❌ Karşılaştırmayı Kapat"
                    if st.session_state.comparison_mode
                    else "🔀 Araç Tiplerini Karşılaştır"
                )
                if st.button(_cmp_label, use_container_width=True, key="toggle_comparison"):
                    st.session_state.comparison_mode = not st.session_state.comparison_mode
                    if not st.session_state.comparison_mode:
                        st.session_state.comparison_routes = {}
                    st.rerun()

                if st.session_state.comparison_mode:
                    _route_vehicles = ['binek', 'kamyon', 'modifiye', 'motosiklet']
                    _CMP_COLORS_TBL = {
                        'binek': '#1565C0', 'kamyon': '#B71C1C',
                        'modifiye': '#2E7D32', 'motosiklet': '#E65100',
                    }
                    try:
                        _sp = _r['start_point']
                        _ep = _r['end_point']
                        _hv = _r['hour']

                        # Rotaları yalnızca henüz hesaplanmamışsa hesapla
                        if not st.session_state.comparison_routes:
                            _routes_cmp = {}
                            with st.spinner("Tüm araç rotaları hesaplanıyor..."):
                                for _vt in _route_vehicles:
                                    try:
                                        _ri = calculate_route(
                                            _sp[0], _sp[1], _ep[0], _ep[1], _vt, _hv
                                        )
                                        if _ri:
                                            _routes_cmp[_vt] = _ri
                                    except Exception:
                                        pass
                            st.session_state.comparison_routes = _routes_cmp
                            st.rerun()   # haritayı yenile

                        _routes_cmp = st.session_state.comparison_routes

                        if _routes_cmp:
                            # Renk göstergesi + tablo başlığı
                            _color_badges = " ".join(
                                f'<span style="display:inline-block;width:14px;height:14px;'
                                f'border-radius:50%;background:{_CMP_COLORS_TBL.get(_vt,"#888")};'
                                f'vertical-align:middle;margin-right:3px;"></span>'
                                f'<small>{_VEMOJI.get(_vt,"")}{_vt.capitalize()}</small>'
                                for _vt in _routes_cmp
                            )
                            st.markdown(
                                f"<div style='font-size:12px;margin-bottom:6px;'>"
                                f"Haritada renkli çizgiler: {_color_badges}</div>",
                                unsafe_allow_html=True
                            )

                            _cmp_data = []
                            _costs_cmp = {}
                            for _vt, _ri in _routes_cmp.items():
                                _s = _ri.get('surfaces', [])
                                _dk = _ri['total_distance_m'] / 1000
                                _q = vp.calculate_road_quality_score(_s)
                                _c = vp.calculate_cost_estimate(_dk, _s, [], _vt)
                                _costs_cmp[_vt] = _c['total_cost_tl']
                                _cmp_data.append({
                                    'Araç': f"{_VEMOJI.get(_vt,'🚗')} {_vt.capitalize()}",
                                    'Mesafe': f"{_dk:.1f} km",
                                    'Süre': f"{int(_ri['estimated_time_minutes'])} dk",
                                    'Yol Kal.': f"{_q['emoji']} {_q['score']}/10",
                                    'Yakıt (L)': f"{_c['fuel_consumption_liters']:.1f}",
                                    'Yakıt (TL)': f"{_c['fuel_cost_tl']:.0f}",
                                    'Bakım (TL)': f"{_c['maintenance_cost_tl']:.0f}",
                                    'Toplam (TL)': f"{_c['total_cost_tl']:.0f}",
                                })

                            _df_cmp = pd.DataFrame(_cmp_data)
                            st.dataframe(_df_cmp, use_container_width=True, hide_index=True)

                            _best = min(_costs_cmp, key=_costs_cmp.get)
                            _worst = max(_costs_cmp, key=_costs_cmp.get)
                            _saving = _costs_cmp[_worst] - _costs_cmp[_best]
                            st.success(
                                f"💚 En uygun: **{_VEMOJI.get(_best,'')} {_best.capitalize()}** "
                                f"— {_costs_cmp[_best]:.0f} TL  "
                                f"(diğerlerine göre {_saving:.0f} TL tasarruf)"
                            )
                    except Exception as _e:
                        st.error(f"❌ Karşılaştırma hatası: {_e}")
        else:
            st.warning("⏳ Sistem yükleniyor...")

    st.markdown(
        "<div style='text-align:center;padding:12px 0 4px;font-size:12px;color:#888;'>"
        "🗺️ <b>Sakarya Akıllı Navigasyon Sistemi</b> &nbsp;|&nbsp; "
        "Python 3.13 &nbsp;·&nbsp; OSMnx &nbsp;·&nbsp; NetworkX &nbsp;·&nbsp; Streamlit &nbsp;·&nbsp; Folium"
        "</div>",
        unsafe_allow_html=True
    )
