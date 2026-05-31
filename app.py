"""
Sakarya Akıllı Navigasyon Sistemi - Streamlit Arayüzü
Sol kolon: araç tipi, saat, başlangıç/bitiş noktaları
Sağ kolon: Folium haritası + rota detayları
v2.1 - dark tema, markdown+button kartlar, Google/Yandex/WhatsApp paylaşım
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
from pathlib import Path
import requests
from datetime import datetime
from typing import Optional, List, Dict
import pandas as pd
import streamlit.components.v1 as components
from urllib.parse import quote as _urlencode

import sys
sys.path.insert(0, str(Path(__file__).parent))

from core.graph_loader import get_graph_cached, get_graph_info
from core.routing import SmartRouter
from profiles import vehicle_profiles as vp
from profiles.vehicle_profiles import list_vehicles, calculate_carbon_emission
from profiles.vehicle_data import (
    VEHICLE_TYPES, CATALOG, BRAND_EMOJI, BRAND_LOGO_URLS,
    get_brands, get_models, get_engines, get_routing_profile, get_display_label,
    get_brand_logo_html,
)



# ==================== GEO BUTTON (query_params tabanlı) ====================
def geo_button_html(field: str, color: str,
                    preserve_start: Optional[tuple] = None,
                    preserve_end: Optional[tuple] = None) -> None:
    """GPS konum butonu. Konum alındığında form submit ile query_params güncellenir."""
    preserve_html = ""
    if field == "start" and preserve_end:
        preserve_html = (f'<input type="hidden" name="end_geo" '
                         f'value="{preserve_end[0]},{preserve_end[1]}">')
    elif field == "end" and preserve_start:
        preserve_html = (f'<input type="hidden" name="start_geo" '
                         f'value="{preserve_start[0]},{preserve_start[1]}">')

    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;padding:2px;background:transparent}}
.btn{{display:block;width:100%;padding:8px 12px;font-size:13px;cursor:pointer;
      border:none;border-radius:6px;color:white;background:{color};
      font-weight:500;transition:opacity .15s}}
.btn:hover:not(:disabled){{opacity:.85}}
.btn:disabled{{opacity:.5;cursor:default}}
#msg{{font-size:11px;margin-top:5px;min-height:14px;color:#667}}
</style></head><body>
<form id="gf" method="GET" target="_top">
  <input type="hidden" name="{field}_geo" id="coords">
  {preserve_html}
</form>
<button class="btn" id="btn" onclick="getGeo()">📍 Mevcut Konumu Kullan</button>
<div id="msg"></div>
<script>
function getGeo(){{
  var btn=document.getElementById('btn'),msg=document.getElementById('msg');
  btn.disabled=true; msg.style.color='#888'; msg.textContent='⏳ Konum alınıyor...';
  if(!navigator.geolocation){{
    msg.style.color='#e53935'; msg.textContent='❌ Tarayıcınız konum desteklemiyor';
    btn.disabled=false; return;
  }}
  navigator.geolocation.getCurrentPosition(
    function(pos){{
      var lat=pos.coords.latitude.toFixed(6), lon=pos.coords.longitude.toFixed(6);
      msg.style.color='#4caf50'; msg.textContent='✅ '+lat+', '+lon;
      document.getElementById('coords').value=lat+','+lon;
      document.getElementById('gf').submit();
    }},
    function(err){{
      var m={{1:'❌ Konum izni reddedildi',2:'❌ Sinyal alınamadı',3:'❌ Zaman aşımı'}};
      msg.style.color='#e53935'; msg.textContent=m[err.code]||('❌ '+err.message);
      btn.disabled=false;
    }},
    {{enableHighAccuracy:true,timeout:12000,maximumAge:0}}
  );
}}
</script></body></html>"""
    components.html(html, height=62)


# ── Araç tipi seçim kartı ────────────────────────────────────────────────────
def vehicle_type_card(vtype: str, emoji: str, label: str, desc: str,
                      tags: list, color: str,
                      preserve: dict | None = None) -> None:
    """
    st.markdown (görsel kart) + st.button (aksiyon) kombinasyonu.
    CSS nth-child trickery yok — her ortamda güvenilir çalışır.
    """
    tags_html = "&nbsp;&nbsp;·&nbsp;&nbsp;".join(
        f"<span style='background:{color}28;color:{color};border-radius:4px;"
        f"padding:2px 8px;font-size:10px;font-weight:600'>{t}</span>"
        for t in tags
    )
    st.markdown(f"""
<div style="border:2px solid {color}44;border-radius:14px;
  background:linear-gradient(135deg,{color}18,{color}08);
  padding:24px 16px 18px;text-align:center;margin-bottom:6px">
  <div style="font-size:54px;line-height:1.1;margin-bottom:10px">{emoji}</div>
  <div style="font-weight:800;font-size:16px;color:{color};margin-bottom:6px">{label}</div>
  <div style="font-size:11px;color:#778;margin-bottom:12px">{desc}</div>
  <div style="line-height:2">{tags_html}</div>
</div>""", unsafe_allow_html=True)

    if st.button(f"Seç", key=f"vtype_{vtype}", use_container_width=True):
        st.session_state.sel_vehicle_type = vtype
        st.session_state.sel_brand        = None
        st.session_state.sel_model        = None
        st.session_state.sel_engine       = None
        st.session_state.app_page         = 'select_brand'
        st.rerun()


# ── Adres arama kutusu (Google Maps benzeri, query param iletişimi) ───────────
def search_box_html(field: str, color: str,
                    current_value: str = "",
                    preserve: dict | None = None) -> None:
    """
    Canlı Nominatim aramalı arama kutusu.
    Seçim yapıldığında `{field}_search=lat,lon,name` query param gönderir.
    """
    preserve = preserve or {}
    hidden_inputs = "".join(
        f'<input type="hidden" name="{k}" value="{v}">'
        for k, v in preserve.items()
    )
    esc_val = current_value.replace('"', '&quot;').replace("'", "&#39;") if current_value else ""
    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:transparent;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;padding:2px}}
.wrap{{position:relative}}
.bar{{display:flex;align-items:center;gap:7px;background:#1e2130;
      border:1.5px solid #3a3d52;border-radius:22px;padding:9px 13px;
      transition:border-color .15s,box-shadow .15s}}
.bar.focused{{border-color:{color};box-shadow:0 2px 12px {color}44}}
.icon{{color:#556;font-size:14px;flex-shrink:0}}
.inp{{flex:1;border:none;outline:none;font-size:13.5px;color:#dde;background:transparent}}
.inp::placeholder{{color:#4a4d62}}
.clr{{background:none;border:none;cursor:pointer;color:#556;font-size:14px;
      padding:2px 5px;border-radius:50%;display:none;flex-shrink:0;line-height:1}}
.clr:hover{{background:#2a2d42;color:#99a}}
.dd{{position:absolute;top:calc(100% + 4px);left:0;right:0;background:#1a1d2e;
     border-radius:12px;box-shadow:0 8px 28px rgba(0,0,0,.55);
     border:1px solid #3a3d52;z-index:9999;overflow:hidden;display:none;
     max-height:320px;overflow-y:auto}}
.dd.open{{display:block}}
.sec{{font-size:10px;font-weight:700;color:#556;letter-spacing:1.2px;
      padding:9px 13px 3px;text-transform:uppercase}}
.it{{display:flex;align-items:center;gap:9px;padding:9px 13px;cursor:pointer;
     transition:background .07s;user-select:none}}
.it:hover,.it.foc{{background:#252840}}
.ico{{font-size:16px;width:20px;text-align:center;flex-shrink:0}}
.tx{{flex:1;min-width:0}}
.p1{{font-size:13px;color:#ccd;font-weight:500;
     white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.p2{{font-size:11px;color:#667;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:1px}}
.tp{{font-size:10px;color:{color};background:{color}22;border-radius:4px;
     padding:1px 5px;flex-shrink:0;white-space:nowrap}}
.spin{{display:flex;align-items:center;gap:7px;padding:14px 13px;color:#667;font-size:12px}}
.dot{{display:inline-block;width:12px;height:12px;border:2px solid #3a3d52;
      border-top-color:{color};border-radius:50%;animation:sp .7s linear infinite}}
@keyframes sp{{to{{transform:rotate(360deg)}}}}
</style></head><body>
<form method="GET" target="_top" id="sf">
  <input type="hidden" name="{field}_search" id="res_input">
  {hidden_inputs}
</form>
<div class="wrap">
  <div class="bar" id="bar">
    <span class="icon">🔍</span>
    <input class="inp" id="inp" type="text" autocomplete="off" spellcheck="false"
           placeholder="Adres veya yer adı ara..." value="{esc_val}">
    <button class="clr" id="clr" type="button" onclick="doClear()">✕</button>
  </div>
  <div class="dd" id="dd"><div id="ddb"></div></div>
</div>
<script>
var NOM="https://nominatim.openstreetmap.org/search";
var ICONS={{university:"🎓",school:"🏫",college:"🎓",hospital:"🏥",clinic:"🏥",
  pharmacy:"💊",station:"🚂",halt:"🚉",bus_station:"🚌",fuel:"⛽",parking:"🅿️",
  restaurant:"🍽️",cafe:"☕",fast_food:"🍔",supermarket:"🛒",bank:"🏦",atm:"💳",
  mall:"🏬",police:"👮",fire_station:"🚒",post_office:"📮",townhall:"🏛️",
  mosque:"🕌",place_of_worship:"🕌",sports_centre:"🏋️",stadium:"🏟️",park:"🌳",
  hotel:"🏨",city:"🏙️",town:"🏘️",village:"🏡",suburb:"📍",neighbourhood:"📍"}};
var inp=document.getElementById("inp"),dd=document.getElementById("dd"),
    ddb=document.getElementById("ddb"),bar=document.getElementById("bar"),
    clr=document.getElementById("clr");
var results=[],focIdx=-1,timer=null;
clr.style.display=inp.value?"block":"none";
inp.addEventListener("focus",function(){{
  bar.classList.add("focused");
  if(!inp.value.trim())showRecents();
  else if(results.length)dd.classList.add("open");
  resize();
}});
inp.addEventListener("blur",function(){{
  bar.classList.remove("focused");
  setTimeout(function(){{if(!dd.matches(":hover"))dd.classList.remove("open");resize();}},180);
}});
inp.addEventListener("input",function(){{
  var q=inp.value.trim();
  clr.style.display=q?"block":"none";
  clearTimeout(timer);
  if(!q){{showRecents();return;}}
  if(q.length<2)return;
  showSpin();
  timer=setTimeout(function(){{doSearch(q);}},280);
}});
inp.addEventListener("keydown",function(e){{
  var items=dd.querySelectorAll(".it");
  if(e.key==="ArrowDown"){{e.preventDefault();focIdx=Math.min(focIdx+1,items.length-1);setFoc(items);}}
  else if(e.key==="ArrowUp"){{e.preventDefault();focIdx=Math.max(focIdx-1,0);setFoc(items);}}
  else if(e.key==="Enter"){{e.preventDefault();if(focIdx>=0&&items[focIdx])items[focIdx].click();}}
  else if(e.key==="Escape"){{dd.classList.remove("open");inp.blur();}}
}});
document.addEventListener("click",function(e){{if(!e.target.closest(".wrap"))dd.classList.remove("open");}});
function setFoc(items){{items.forEach(function(el,i){{el.classList.toggle("foc",i===focIdx);if(i===focIdx)el.scrollIntoView({{block:"nearest"}});}});}}
async function doSearch(q){{
  try{{
    var p=new URLSearchParams({{q:q+", Sakarya",format:"json",limit:10,bounded:1,viewbox:"29.5,41.2,31.5,40.3",countrycodes:"tr",addressdetails:1}});
    var r=await fetch(NOM+"?"+p,{{headers:{{"Accept-Language":"tr"}}}});
    var data=await r.json();
    results=[];
    var sn=new Set(),sc=new Set();
    for(var item of data){{
      var la=parseFloat(item.lat),lo=parseFloat(item.lon);
      if(la<40.3||la>41.2||lo<29.5||lo>31.5)continue;
      var ck=Math.round(la*1000)+","+Math.round(lo*1000);
      if(sc.has(ck))continue;sc.add(ck);
      var parts=(item.display_name||"").split(",").map(function(s){{return s.trim();}});
      var prim=parts[0]||"?";
      if(sn.has(prim.toLowerCase()))continue;sn.add(prim.toLowerCase());
      var addr=item.address||{{}};
      var dist=addr.suburb||addr.city_district||addr.quarter||"";
      var city=addr.city||addr.town||addr.county||"Sakarya";
      var sub=[dist,city].filter(function(x,i,a){{return x&&x.toLowerCase()!==prim.toLowerCase()&&a.indexOf(x)===i;}}).slice(0,2).join(", ");
      var ico=ICONS[item.type||""]||ICONS[item["class"]||""]||"📍";
      var tp=(item.type||"").replace(/_/g," ");
      results.push({{la:la,lo:lo,name:prim,dn:prim+(dist?", "+dist:"")+(city&&city!==dist?", "+city:""),ico:ico,sub:sub,tp:tp}});
      if(results.length>=7)break;
    }}
    renderResults();
  }}catch(e){{ddb.innerHTML='<div class="spin">❌ Arama hatası</div>';dd.classList.add("open");resize();}}
}}
function showSpin(){{ddb.innerHTML='<div class="spin"><span class="dot"></span>Aranıyor...</div>';dd.classList.add("open");resize();}}
function renderResults(){{
  if(!results.length){{ddb.innerHTML='<div class="spin">📭 Sonuç bulunamadı</div>';dd.classList.add("open");resize();return;}}
  var h="";
  results.forEach(function(r,i){{
    h+='<div class="it" data-i="'+i+'" onclick="pick('+i+')">'
      +'<span class="ico">'+r.ico+'</span>'
      +'<div class="tx"><div class="p1">'+esc(r.name)+'</div>'
      +(r.sub?'<div class="p2">'+esc(r.sub)+'</div>':"")
      +'</div>'+(r.tp?'<span class="tp">'+esc(r.tp)+'</span>':"")
      +'</div>';
  }});
  focIdx=-1;ddb.innerHTML=h;dd.classList.add("open");resize();
}}
function getRecents(){{try{{return JSON.parse(localStorage.getItem("snav_{field}")||"[]");}}catch(e){{return[];}}}}
function saveRecent(r){{try{{var l=getRecents().filter(function(x){{return!(x.la===r.la&&x.lo===r.lo);}});l.unshift(r);localStorage.setItem("snav_{field}",JSON.stringify(l.slice(0,5)));}}catch(e){{}}}}
function showRecents(){{
  var recs=getRecents();
  if(!recs.length){{dd.classList.remove("open");return;}}
  var h='<div class="sec">Son Aramalar</div>';
  recs.forEach(function(r,i){{h+='<div class="it" onclick="pickR('+i+')">'
    +'<span class="ico">🕐</span><div class="tx"><div class="p1">'+esc(r.name)+'</div>'
    +(r.sub?'<div class="p2">'+esc(r.sub)+'</div>':"")+'</div></div>';
  }});
  ddb.innerHTML=h;dd.classList.add("open");resize();
}}
function pick(i){{commit(results[i]);}}
function pickR(i){{var recs=getRecents();if(recs[i])commit(recs[i]);}}
function commit(r){{
  inp.value=r.name;clr.style.display="block";
  dd.classList.remove("open");
  saveRecent(r);
  document.getElementById("res_input").value=r.la+","+r.lo+","+encodeURIComponent(r.name)+","+encodeURIComponent(r.dn);
  document.getElementById("sf").submit();
}}
function doClear(){{inp.value="";clr.style.display="none";results=[];focIdx=-1;dd.classList.remove("open");inp.focus();resize();}}
function esc(s){{return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");}}
function resize(){{setTimeout(function(){{var h=document.body.scrollHeight+6;window.parent&&window.parent.postMessage&&window.parent.postMessage({{type:"streamlit:setFrameHeight",height:Math.max(52,h)}},"*");}},25);}}
resize();
</script></body></html>"""
    components.html(html, height=58, scrolling=False)


# ==================== STREAMLIT AYARLARI ====================
st.set_page_config(
    page_title="🗺️ Sakarya Akıllı Navigasyon Sistemi",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem !important; }

    .loc-card {
        background: linear-gradient(135deg, #1a237e11, #1565C011);
        border: 1px solid #1565C033;
        border-radius: 8px; padding: 8px 12px; margin: 6px 0; font-size: 13px;
    }
    .loc-card-end {
        background: linear-gradient(135deg, #b71c1c11, #C6282811);
        border: 1px solid #C6282833;
    }
    .loc-label  { font-weight: 600; color: #778; font-size: 11px; margin-bottom: 2px; }
    .loc-name   { font-size: 13px; color: #ccd; font-weight: 500; margin-bottom: 2px; }
    .loc-coords { font-family: monospace; font-size: 11px; color: #667; }

    .click-hint {
        background: #fff9c4; border: 1px solid #f9a825;
        border-radius: 6px; padding: 6px 10px;
        font-size: 12px; color: #555; margin: 4px 0 8px;
    }
    [data-testid="stMetric"] {
        border: 1px solid rgba(128,128,128,0.25);
        border-radius: 8px; padding: 10px 14px !important;
    }
    .route-banner {
        background: linear-gradient(90deg, #1b5e20, #2e7d32);
        border-radius: 8px; padding: 10px 16px;
        color: white; font-weight: 600; font-size: 15px; margin-bottom: 12px;
    }
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child
        > [data-testid="stVerticalBlock"] {
        position: sticky !important;
        top: 3.5rem;
        max-height: calc(100vh - 3.5rem);
        overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)

# ── Streamlit Cloud: iframe'lere geolocation izni yama ───────────────────────
components.html("""
<script>
(function(){
  try{
    // Bu iframe'e izin ekle
    var me=window.frameElement;
    if(me && me.allow && me.allow.indexOf('geolocation')===-1)
      me.allow=me.allow+'; geolocation *';
    else if(me && !me.allow) me.allow='geolocation *';

    // Yeni eklenen iframe'leri de yakala
    new MutationObserver(function(muts){
      muts.forEach(function(m){
        m.addedNodes.forEach(function(n){
          if(!n || n.nodeType!==1) return;
          var frames=(n.tagName==='IFRAME'?[n]:[]).concat(
            Array.from(n.querySelectorAll('iframe')));
          frames.forEach(function(f){
            if(f.allow && f.allow.indexOf('geolocation')===-1)
              f.allow=f.allow+'; geolocation *';
            else if(!f.allow) f.allow='geolocation *';
          });
        });
      });
    }).observe(window.parent.document.body,{childList:true,subtree:true});
  }catch(e){}
})();
</script>
""", height=0)


# ==================== SESSION STATE ====================
_SS_DEFAULTS: Dict = {
    'graph': None,
    'router': None,
    'last_route': None,
    'start_lat_live': None,
    'start_lon_live': None,
    'end_lat_live': None,
    'end_lon_live': None,
    'route_history': [],
    # Yer adları (loc-card'da gösterilir)
    'start_place_name': None,
    'end_place_name': None,
    # Searchbox infinite-fire koruması
    '_prev_start_sel': None,
    '_prev_end_sel': None,
    'start_place_name_short': None,
    'end_place_name_short':   None,
    '_last_map_click': None,
    # Karşılaştırma
    'comparison_routes': {},
    'comparison_mode': False,
    # Geolocation
    'start_geo_lat': None,
    'start_geo_lon': None,
    'end_geo_lat': None,
    'end_geo_lon': None,
    # Araç seçimi
    'vehicle_selection_step': 'category',
    'selected_category': None,
    'selected_model': None,
    'selected_modifications': [],
    'saved_profile': None,
    'app_page': 'welcome',
    'sel_vehicle_type': None,
    'sel_brand': None,
    'sel_model': None,
    'sel_engine': None,
    # Saat (persist)
    'hour': 12,
    # Alternatif rotalar
    'alt_routes': [],
    'sel_alt_idx': 0,
}
for _k, _v in _SS_DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ── GPS query params ──────────────────────────────────────────────────────────
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
    st.session_state.start_geo_lat    = _sgeo[0]
    st.session_state.start_geo_lon    = _sgeo[1]
    st.session_state.start_lat_live   = _sgeo[0]
    st.session_state.start_lon_live   = _sgeo[1]
    st.session_state.start_place_name = f"📍 GPS ({_sgeo[0]:.4f}, {_sgeo[1]:.4f})"

if _egeo:
    st.session_state.end_geo_lat    = _egeo[0]
    st.session_state.end_geo_lon    = _egeo[1]
    st.session_state.end_lat_live   = _egeo[0]
    st.session_state.end_lon_live   = _egeo[1]
    st.session_state.end_place_name = f"📍 GPS ({_egeo[0]:.4f}, {_egeo[1]:.4f})"

if _sgeo or _egeo:
    st.query_params.clear()




# ── Adres arama sonucu (query param) ─────────────────────────────────────────
def _read_search_param(param: str) -> Optional[dict]:
    """start_search / end_search query param'ını parse et: lat,lon,name,dn"""
    try:
        raw = st.query_params.get(param, '')
        if not raw:
            return None
        from urllib.parse import unquote
        parts = raw.split(',', 3)
        if len(parts) < 3:
            return None
        lat  = float(parts[0])
        lon  = float(parts[1])
        name = unquote(parts[2])
        dn   = unquote(parts[3]) if len(parts) > 3 else name
        if 40.3 <= lat <= 41.2 and 29.5 <= lon <= 31.5:
            return {'lat': lat, 'lon': lon, 'name': name, 'display_name': dn}
    except Exception:
        pass
    return None

_sres = _read_search_param('start_search')
_eres = _read_search_param('end_search')

if _sres:
    st.session_state.start_lat_live         = _sres['lat']
    st.session_state.start_lon_live         = _sres['lon']
    st.session_state.start_place_name       = _sres['display_name']
    st.session_state.start_place_name_short = _sres['name']
if _eres:
    st.session_state.end_lat_live         = _eres['lat']
    st.session_state.end_lon_live         = _eres['lon']
    st.session_state.end_place_name       = _eres['display_name']
    st.session_state.end_place_name_short = _eres['name']
if _sres or _eres:
    st.query_params.clear()
    st.rerun()


# ── Sakarya koordinat doğrulama ───────────────────────────────────────────────
def _is_sakarya(lat, lon) -> bool:
    return (lat is not None and lon is not None
            and 40.15 <= lat <= 41.05 and 29.8 <= lon <= 31.3)

for _k_lat, _k_lon in [
    ('start_lat_live',  'start_lon_live'),
    ('end_lat_live',    'end_lon_live'),
    ('start_geo_lat',   'start_geo_lon'),
    ('end_geo_lat',     'end_geo_lon'),
]:
    if not _is_sakarya(st.session_state.get(_k_lat), st.session_state.get(_k_lon)):
        st.session_state[_k_lat] = None
        st.session_state[_k_lon] = None


# ==================== YARDIMCI FONKSİYONLAR ====================

@st.cache_resource
def load_graph():
    """Graph'ı tek seferlik yükle ve cache'le."""
    with st.spinner("Sakarya yol ağı yükleniyor..."):
        return get_graph_cached()




def _clear_searchbox(field: str) -> None:
    """
    st_searchbox widget state'ini ve prev_sel koruma state'ini sıfırla.
    field: 'start' veya 'end'
    """
    prefix = f"{field}_searchbox"
    for _k in list(st.session_state.keys()):
        if prefix in str(_k):
            del st.session_state[_k]
    _prev_key = f"_prev_{field}_sel"
    st.session_state[_prev_key] = None


# ── Tile seçenekleri ──────────────────────────────────────────────────────────
_TILE_OPTIONS: Dict[str, str] = {
    "🗺️ Yol":     "OpenStreetMap",
    "🌑 Karanlık": "CartoDB dark_matter",
    "⬜ Açık":     "CartoDB positron",
}


# ── Folium harita oluşturucu ──────────────────────────────────────────────────
def create_folium_map(
    graph,
    route_info        = None,
    start_lat_live    = None, start_lon_live = None,
    end_lat_live      = None, end_lon_live   = None,
    start_geo_lat     = None, start_geo_lon  = None,
    end_geo_lat       = None, end_geo_lon    = None,
    center_lat        = 40.76, center_lon    = 30.39, zoom = 12,
    comparison_routes : Optional[Dict] = None,
    tile              : str = "OpenStreetMap",
    alt_routes        : Optional[List[Dict]] = None,
    sel_alt_idx       : int = 0,
):
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles=tile)

    # GPS marker'ları
    for _glat, _glon, _lbl in [
        (start_geo_lat, start_geo_lon, "Başlangıç GPS"),
        (end_geo_lat,   end_geo_lon,   "Bitiş GPS"),
    ]:
        if _glat is not None:
            folium.Marker(
                location=[_glat, _glon],
                popup=f"📍 GPS ({_lbl})",
                tooltip="GPS Konumunuz",
                icon=folium.Icon(color='blue', icon='map-marker'),
            ).add_to(m)

    # ── Karşılaştırma modu ──────────────────────────────────────────────────
    if comparison_routes:
        _CMP_COLORS = {
            'binek':      '#1565C0',
            'kamyon':     '#B71C1C',
            'modifiye':   '#2E7D32',
            'motosiklet': '#E65100',
            'bisiklet':   '#6A1B9A',
        }
        _CMP_LABELS = {
            'binek':      '🚗 Binek',
            'kamyon':     '🚛 Kamyon',
            'modifiye':   '🚙 Modifiye',
            'motosiklet': '🏍️ Motosiklet',
            'bisiklet':   '🚲 Bisiklet',
        }
        _CMP_DASH = {
            'binek': None, 'kamyon': '10 5', 'modifiye': '6 4',
            'motosiklet': '3 6', 'bisiklet': '12 4 3 4',
        }
        all_pts: list = []
        for _vt, _ri in comparison_routes.items():
            _coords = _ri.get('coordinates', [])
            if not _coords:
                continue
            folium.PolyLine(
                locations=_coords,
                color=_CMP_COLORS.get(_vt, '#555'),
                weight=5, opacity=0.85,
                dash_array=_CMP_DASH.get(_vt),
                tooltip=(f"{_CMP_LABELS.get(_vt, _vt)} | "
                         f"{_ri['total_distance_m']/1000:.1f} km | "
                         f"{int(_ri['estimated_time_minutes'])} dk"),
            ).add_to(m)
            all_pts.extend(_coords)

        _ref = next(iter(comparison_routes.values()))
        for _pt, _col, _lbl in [
            (_ref['start_point'], '#2E7D32', '🟢 Başlangıç'),
            (_ref['end_point'],   '#C62828', '🔴 Bitiş'),
        ]:
            folium.CircleMarker(
                location=list(_pt), radius=12,
                popup=_lbl, tooltip=_lbl,
                color='white', fill=True,
                fillColor=_col, fillOpacity=1.0, weight=3,
            ).add_to(m)

        legend = (
            "<div style='position:fixed;bottom:30px;right:10px;z-index:9999;"
            "background:rgba(255,255,255,.92);border:1px solid #ccc;"
            "border-radius:8px;padding:10px 14px;font-size:13px;"
            "box-shadow:0 2px 8px rgba(0,0,0,.15)'><b>Araç Rotaları</b><br>"
        )
        for _vt in comparison_routes:
            legend += (f'<span style="color:{_CMP_COLORS.get(_vt,"#555")};'
                       f'font-weight:700;">━━</span> {_CMP_LABELS.get(_vt,_vt)}<br>')
        legend += "</div>"
        m.get_root().html.add_child(folium.Element(legend))

        if all_pts:
            m.fit_bounds(
                [[min(c[0] for c in all_pts), min(c[1] for c in all_pts)],
                 [max(c[0] for c in all_pts), max(c[1] for c in all_pts)]],
                padding=[55, 55]
            )
        return m

    # ── Alternatif rotalar modu ────────────────────────────────────────────
    if alt_routes and len(alt_routes) > 1:
        all_coords: List = []
        # Önce seçili olmayanları çiz (altta kalır)
        for i, _ar in enumerate(alt_routes):
            if i == sel_alt_idx:
                continue
            _c = _ar.get('coordinates', [])
            if not _c:
                continue
            folium.PolyLine(
                locations=_c,
                color=_ar.get('route_color', '#888888'),
                weight=4, opacity=0.35,
                tooltip=(f"{_ar.get('route_label','')} | "
                         f"{_ar['total_distance_m']/1000:.1f} km | "
                         f"{int(_ar['estimated_time_minutes'])} dk"),
            ).add_to(m)
            all_coords.extend(_c)
        # Seçili rotayı üste çiz
        _sel = alt_routes[sel_alt_idx]
        _sc  = _sel.get('coordinates', [])
        if _sc:
            folium.PolyLine(
                locations=_sc,
                color=_sel.get('route_color', '#1565C0'),
                weight=6, opacity=0.94,
                tooltip=(f"{_sel.get('route_label','Rota')} | "
                         f"{_sel['total_distance_m']/1000:.1f} km | "
                         f"{int(_sel['estimated_time_minutes'])} dk"),
            ).add_to(m)
            all_coords.extend(_sc)

        # Başlangıç / bitiş marker'ları
        ref = alt_routes[0]
        for _pt, _col, _lbl in [
            (ref['start_point'], '#2E7D32', '🟢 Başlangıç'),
            (ref['end_point'],   '#C62828', '🔴 Bitiş'),
        ]:
            folium.CircleMarker(
                location=list(_pt), radius=12,
                popup=_lbl, tooltip=_lbl,
                color='white', fill=True,
                fillColor=_col, fillOpacity=1.0, weight=3,
            ).add_to(m)

        if all_coords:
            m.fit_bounds(
                [[min(c[0] for c in all_coords), min(c[1] for c in all_coords)],
                 [max(c[0] for c in all_coords), max(c[1] for c in all_coords)]],
                padding=[55, 55]
            )
        return m

    # ── Tekil rota modu ────────────────────────────────────────────────────
    if route_info is None:
        for _lat, _lon, _col, _tip in [
            (start_lat_live, start_lon_live, '#2E7D32', 'Başlangıç Noktası'),
            (end_lat_live,   end_lon_live,   '#C62828', 'Bitiş Noktası'),
        ]:
            if _lat is not None:
                folium.CircleMarker(
                    location=[_lat, _lon], radius=11,
                    tooltip=_tip, color='white', fill=True,
                    fillColor=_col, fillOpacity=1.0, weight=3,
                ).add_to(m)
    else:
        coords = route_info.get('coordinates', [])
        if coords:
            folium.PolyLine(
                locations=coords, color='#1565C0',
                weight=6, opacity=0.92,
                popup=f"📏 {route_info['total_distance_m']/1000:.2f} km",
            ).add_to(m)
            m.fit_bounds(
                [[min(c[0] for c in coords), min(c[1] for c in coords)],
                 [max(c[0] for c in coords), max(c[1] for c in coords)]],
                padding=[55, 55]
            )
        for _pt, _col, _lbl in [
            (route_info['start_point'], '#2E7D32', '🟢 Başlangıç'),
            (route_info['end_point'],   '#C62828', '🔴 Bitiş'),
        ]:
            folium.CircleMarker(
                location=list(_pt), radius=12,
                popup=_lbl, tooltip=_lbl,
                color='white', fill=True,
                fillColor=_col, fillOpacity=1.0, weight=3,
            ).add_to(m)
    return m


# ── Nominatim arama (cache 60s) ───────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def search_photon(query: str) -> List[Dict]:
    """
    Nominatim (OpenStreetMap) API ile Sakarya odaklı geocoding.
    - Sakarya ili viewbox + bounded ile sınırlı arama
    - (class, type) tuple ikon sistemi
    - Sonuçlar 60 saniye cache'lenir
    """
    if not query or len(query.strip()) < 2:
        return []

    ICONS: Dict[tuple, str] = {
        ("amenity", "university"):      "🎓",
        ("building", "university"):     "🎓",
        ("amenity", "school"):          "🏫",
        ("building", "school"):         "🏫",
        ("amenity", "college"):         "🎓",
        ("amenity", "tutoring"):        "📚",
        ("amenity", "language_school"): "📚",
        ("amenity", "driving_school"):  "🚗",
        ("amenity", "kindergarten"):    "🧒",
        ("amenity", "hospital"):        "🏥",
        ("amenity", "clinic"):          "🏥",
        ("amenity", "pharmacy"):        "💊",
        ("amenity", "dentist"):         "🦷",
        ("amenity", "doctors"):         "👨‍⚕️",
        ("railway", "station"):         "🚂",
        ("railway", "halt"):            "🚉",
        ("amenity", "bus_station"):     "🚌",
        ("highway", "bus_stop"):        "🚌",
        ("amenity", "fuel"):            "⛽",
        ("amenity", "parking"):         "🅿️",
        ("amenity", "restaurant"):      "🍽️",
        ("amenity", "cafe"):            "☕",
        ("amenity", "fast_food"):       "🍔",
        ("shop",    "supermarket"):     "🛒",
        ("amenity", "bank"):            "🏦",
        ("amenity", "atm"):             "💳",
        ("shop",    "mall"):            "🏬",
        ("amenity", "police"):          "👮",
        ("amenity", "fire_station"):    "🚒",
        ("amenity", "post_office"):     "📮",
        ("amenity", "townhall"):        "🏛️",
        ("amenity", "courthouse"):      "⚖️",
        ("amenity", "mosque"):          "🕌",
        ("amenity", "place_of_worship"):"🕌",
        ("leisure", "sports_centre"):   "🏋️",
        ("leisure", "stadium"):         "🏟️",
        ("leisure", "park"):            "🌳",
        ("tourism", "hotel"):           "🏨",
        ("tourism", "motel"):           "🏨",
        ("place",   "city"):            "🏙️",
        ("place",   "town"):            "🏘️",
        ("place",   "village"):         "🏡",
        ("place",   "suburb"):          "📍",
        ("place",   "neighbourhood"):   "📍",
    }

    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q":            f"{query.strip()}, Sakarya",
                "format":       "json",
                "limit":        10,
                "bounded":      1,
                "viewbox":      "29.5,41.2,31.5,40.3",   # west,north,east,south
                "countrycodes": "tr",
                "addressdetails": 1,
            },
            timeout=8,
            headers={
                "User-Agent": (
                    "SakaryaNavApp/1.0 "
                    "(github.com/zXeod/sakarya-navigasyon)"
                )
            },
        )
        resp.raise_for_status()
        items: list = resp.json()
    except Exception:
        return []

    results: List[Dict] = []
    seen_coords: set = set()
    seen_names:  set = set()

    for item in items:
        try:
            lat = float(item["lat"])
            lon = float(item["lon"])
        except (KeyError, ValueError):
            continue

        if not (40.3 <= lat <= 41.2 and 29.5 <= lon <= 31.5):
            continue

        coord_key = (round(lat, 3), round(lon, 3))
        if coord_key in seen_coords:
            continue
        seen_coords.add(coord_key)

        osm_class = item.get("class", "")
        osm_type  = item.get("type", "")
        address   = item.get("address", {})

        # İsim: display_name'in ilk parçası
        display_name = item.get("display_name", "")
        name_parts   = [p.strip() for p in display_name.split(",") if p.strip()]
        primary      = name_parts[0] if name_parts else "Bilinmeyen"

        district = (address.get("suburb") or address.get("city_district")
                    or address.get("quarter") or "")
        city     = (address.get("city") or address.get("town")
                    or address.get("county") or "Sakarya")

        nd_key = primary.lower()
        if nd_key in seen_names:
            continue
        seen_names.add(nd_key)

        icon = ICONS.get((osm_class, osm_type), "📍")

        addr_parts: list = []
        if district and district.lower() != primary.lower():
            addr_parts.append(district)
        if city and city.lower() != primary.lower():
            addr_parts.append(city)

        subtitle = ", ".join(addr_parts[:2])
        label = f"{icon} {primary}"
        if subtitle:
            label += f"  ·  {subtitle}"

        results.append({
            "label":        label,
            "lat":          lat,
            "lon":          lon,
            "name":         primary,
            "display_name": f"{primary}, {district or city}",
        })
        if len(results) >= 8:
            break

    return results


def _photon_wrapper_start(query: str, **_):
    """st_searchbox için (label, değer_dict) tuple listesi döndürür."""
    return [(r["label"], r) for r in search_photon(query)]


def _photon_wrapper_end(query: str, **_):
    return [(r["label"], r) for r in search_photon(query)]


# ── Rota hesapla ──────────────────────────────────────────────────────────────
def calculate_route(start_lat, start_lon, end_lat, end_lon, vehicle_type, hour,
                    with_alternatives: bool = True):
    """Rota hesapla (+ alternatifler), session_state'e kaydet."""
    SLAT, SLON = (40.15, 41.05), (29.8, 31.3)
    for lbl, la, lo in [("Başlangıç", start_lat, start_lon),
                         ("Bitiş",     end_lat,   end_lon)]:
        if not (SLAT[0] <= la <= SLAT[1] and SLON[0] <= lo <= SLON[1]):
            st.error(
                f"❌ {lbl} koordinatı Sakarya dışında: {la:.4f}, {lo:.4f}\n\n"
                "Lütfen arama yaparak veya haritaya tıklayarak yeniden seçin."
            )
            return None
    try:
        router = SmartRouter(st.session_state.graph, vehicle_type, hour)
        st.session_state.router = router

        if with_alternatives:
            alt_routes = router.find_alternative_routes(
                start_lat, start_lon, end_lat, end_lon, n_routes=5
            )
            st.session_state.alt_routes  = alt_routes
            st.session_state.sel_alt_idx = 0
            route_info = alt_routes[0]
        else:
            route_info = router.find_route(start_lat, start_lon, end_lat, end_lon)
            st.session_state.alt_routes  = [route_info]
            st.session_state.sel_alt_idx = 0

        st.session_state.last_route = route_info

        history_item = {
            'vehicle':    vehicle_type,
            'distance':   route_info['total_distance_m'] / 1000,
            'time':       f"{route_info['estimated_time_minutes']:.0f} dk",
            'hour':       hour,
            'route_info': route_info,
            'timestamp':  datetime.now().strftime('%H:%M'),
            'start_name': st.session_state.get('start_place_name', ''),
            'end_name':   st.session_state.get('end_place_name', ''),
        }
        st.session_state.route_history.insert(0, history_item)
        st.session_state.route_history = st.session_state.route_history[:5]
        return route_info
    except Exception as e:
        st.error(f"❌ Rota hesaplama hatası: {str(e)}")
        return None


# ── Popüler Sakarya lokasyonları ──────────────────────────────────────────────
_POPULAR: List[tuple] = [
    ("🎓 SUBÜ Kampüs",      40.7433, 30.3337),
    ("🏥 Sakarya EAH",      40.7712, 30.4053),
    ("🚂 Adapazarı Gar",    40.7855, 30.4082),
    ("🏛️ Sakarya Valiliği", 40.7742, 30.3961),
    ("🛒 Carrefour SAU",    40.7648, 30.4186),
    ("🌊 Karasu Sahili",    41.1114, 30.6895),
]


def _popular_picks(field: str) -> None:
    """Popüler yerler hızlı seçim expander'ı."""
    with st.expander("⭐ Popüler Yerler", expanded=False):
        for _i in range(0, len(_POPULAR), 2):
            _c1, _c2 = st.columns(2)
            for _col, _qi in zip([_c1, _c2], _POPULAR[_i:_i+2]):
                with _col:
                    if st.button(_qi[0], use_container_width=True,
                                 key=f"pop_{field}_{_qi[0]}"):
                        st.session_state[f"{field}_lat_live"]   = _qi[1]
                        st.session_state[f"{field}_lon_live"]   = _qi[2]
                        st.session_state[f"{field}_place_name"] = _qi[0]
                        _clear_searchbox(field)
                        st.rerun()


# ==================== ANA ARAYÜZ ====================

# ── Sayfa: Hoşgeldiniz ────────────────────────────────────────────────────────
if st.session_state.app_page == 'welcome':
    st.markdown("""
    <div style='text-align:center;padding:60px 20px 30px'>
        <div style='font-size:80px;margin-bottom:16px'>🗺️</div>
        <h1 style='font-size:2.8rem;font-weight:800;margin-bottom:8px'>
            Sakarya Akıllı Navigasyon Sistemi
        </h1>
        <p style='font-size:1.1rem;color:#888;margin-bottom:40px'>
            Araç tipinize göre optimize edilmiş rota planlama
        </p>
    </div>""", unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        if st.button("🚀  Başla — Aracını Seç", use_container_width=True, type="primary"):
            st.session_state.app_page = 'select_type'
            st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style='text-align:center;color:#999;font-size:13px'>
        OSMnx &nbsp;·&nbsp; NetworkX &nbsp;·&nbsp; Folium &nbsp;·&nbsp; Streamlit<br>
        Sakarya Uygulamalı Bilimler Üniversitesi &nbsp;·&nbsp; Kariyer Zirvesi 2026
        </div>""", unsafe_allow_html=True)


# ── Sayfa: Araç Tipi Seç ─────────────────────────────────────────────────────
elif st.session_state.app_page == 'select_type':
    st.markdown("## 🚘 Vasıta Türünü Seçin")
    st.caption("Hangi araç ile gitmek istiyorsunuz?")
    st.markdown("---")

    _COLORS = {'otomobil': '#1565C0', 'arazi_suv': '#2E7D32', 'motosiklet': '#E65100'}
    _types = [
        ('otomobil',   '🚗',  'Otomobil',
         'Sedan · Hatchback · Station Wagon', ['Şehir içi', 'Uzun yol', 'Yakıt dostu']),
        ('arazi_suv',  '🚙',  'Arazi / SUV / Pickup',
         'SUV · Crossover · Pickup',          ['Yüksek çekiş', 'Bozuk yol', 'Off-road']),
        ('motosiklet', '🏍️', 'Motosiklet',
         'Naked · Sport · Scooter',           ['Dar sokak', 'Hızlı geçiş', 'Ekonomik']),
    ]
    _tc1, _tc2, _tc3 = st.columns(3)
    for _col, (_vtype, _emoji, _label, _desc, _tags) in zip([_tc1, _tc2, _tc3], _types):
        with _col:
            vehicle_type_card(
                vtype=_vtype, emoji=_emoji, label=_label,
                desc=_desc, tags=_tags,
                color=_COLORS.get(_vtype, '#555'),
            )


# ── Sayfa: Marka Seç ──────────────────────────────────────────────────────────
elif st.session_state.app_page == 'select_brand':
    _vtype = st.session_state.sel_vehicle_type
    _bc, _tc = st.columns([1, 8])
    with _bc:
        if st.button("← Geri"):
            st.session_state.app_page = 'select_type'; st.rerun()
    with _tc:
        st.markdown(f"## {get_display_label(_vtype)} — Marka Seçin")
    st.caption("Sakarya'da popüler markalar"); st.markdown("---")
    _brands = get_brands(_vtype)
    for _row in [_brands[i:i+4] for i in range(0, len(_brands), 4)]:
        _cols = st.columns(4)
        for _ci, _brand in enumerate(_row):
            with _cols[_ci]:
                st.markdown(
                    f"<div style='text-align:center;height:58px;"
                    f"display:flex;align-items:center;justify-content:center;"
                    f"margin-bottom:4px;background:rgba(128,128,128,0.07);"
                    f"border-radius:8px;border:1px solid rgba(128,128,128,0.15)'>"
                    f"{get_brand_logo_html(_brand)}</div>",
                    unsafe_allow_html=True
                )
                if st.button(_brand, use_container_width=True, key=f"brand_{_brand}"):
                    st.session_state.sel_brand  = _brand
                    st.session_state.sel_model  = None
                    st.session_state.sel_engine = None
                    st.session_state.app_page   = 'select_model'
                    st.rerun()


# ── Sayfa: Model Seç ──────────────────────────────────────────────────────────
elif st.session_state.app_page == 'select_model':
    _vtype = st.session_state.sel_vehicle_type
    _brand = st.session_state.sel_brand
    _bc, _tc = st.columns([1, 8])
    with _bc:
        if st.button("← Geri"):
            st.session_state.app_page = 'select_brand'; st.rerun()
    with _tc:
        st.markdown(f"## {BRAND_EMOJI.get(_brand,'🚘')} {_brand} — Model Seçin")
    st.caption(f"Sakarya'da popüler {_brand} modelleri"); st.markdown("---")
    _models = get_models(_vtype, _brand)
    for _row in [_models[i:i+3] for i in range(0, len(_models), 3)]:
        _cols = st.columns(3)
        for _ci, _model in enumerate(_row):
            with _cols[_ci]:
                if st.button(_model, use_container_width=True, key=f"model_{_model}"):
                    st.session_state.sel_model  = _model
                    st.session_state.sel_engine = None
                    st.session_state.app_page   = 'select_engine'
                    st.rerun()


# ── Sayfa: Motor Seç ──────────────────────────────────────────────────────────
elif st.session_state.app_page == 'select_engine':
    _vtype  = st.session_state.sel_vehicle_type
    _brand  = st.session_state.sel_brand
    _model  = st.session_state.sel_model
    _bc, _tc = st.columns([1, 8])
    with _bc:
        if st.button("← Geri"):
            st.session_state.app_page = 'select_model'; st.rerun()
    with _tc:
        st.markdown(f"## {_brand} {_model} — Motor Seçin")
    st.caption("Motor hacmi ve güç"); st.markdown("---")
    _engines = get_engines(_vtype, _brand, _model)
    for _row in [_engines[i:i+2] for i in range(0, len(_engines), 2)]:
        _cols = st.columns(2)
        for _ci, _eng in enumerate(_row):
            with _cols[_ci]:
                if st.button(f"⚙️ {_eng}", use_container_width=True, key=f"eng_{_eng}"):
                    st.session_state.sel_engine = _eng
                    st.session_state.app_page   = 'select_mods'
                    st.rerun()


# ── Sayfa: Modifikasyon Seç ───────────────────────────────────────────────────
elif st.session_state.app_page == 'select_mods':
    _vtype  = st.session_state.sel_vehicle_type
    _brand  = st.session_state.sel_brand
    _model  = st.session_state.sel_model
    _engine = st.session_state.sel_engine

    st.markdown(f"## ⚙️ {_brand} {_model} {_engine}")
    st.markdown("### Ek Tercihler (İsteğe Bağlı)")
    st.caption("Aracınızda modifikasyon var mı?"); st.markdown("---")

    _available_mods = vp.get_modifications()
    _selected = list(st.session_state.selected_modifications)
    _mod_cols = st.columns(2)
    for _mi, (_mkey, _mdata) in enumerate(_available_mods.items()):
        with _mod_cols[_mi % 2]:
            _checked = st.checkbox(
                f"{_mdata.get('emoji','🔧')} {_mdata['name']}",
                value=_mkey in _selected,
                key=f"mod_{_mkey}",
                help=_mdata.get('effect', '')
            )
            if _checked and _mkey not in _selected:   _selected.append(_mkey)
            elif not _checked and _mkey in _selected: _selected.remove(_mkey)
    st.session_state.selected_modifications = _selected
    st.markdown("---")

    def _commit_profile(mods: list) -> None:
        _profile = get_routing_profile(_vtype)
        st.session_state.saved_profile = {
            'name':            f"{_brand} {_model} {_engine}",
            'routing_profile': _profile,
            'modifications':   mods,
            'vehicle_display': f"{VEHICLE_TYPES[_vtype]['emoji']} {_brand} {_model}",
            'engine':          _engine,
            'brand':           _brand,
            'model_name':      _model,
            'vtype':           _vtype,
        }
        st.session_state.selected_category     = _vtype
        st.session_state.selected_model        = f"{_brand} {_model}"
        st.session_state.vehicle_selection_step = 'confirm'
        st.session_state.app_page               = 'map'

    _bc2, _cc2 = st.columns(2)
    with _bc2:
        if st.button("⏭️ Modifikasyon Yok, Devam Et", use_container_width=True):
            _commit_profile([]); st.rerun()
    with _cc2:
        if st.button("✅ Onayla ve Haritaya Git",
                     use_container_width=True, type="primary"):
            _commit_profile(_selected); st.rerun()


# ── Sayfa: Harita ─────────────────────────────────────────────────────────────
elif st.session_state.app_page == 'map':

    # ── Araç kartı ────────────────────────────────────────────────────────────
    if st.session_state.saved_profile:
        _sp     = st.session_state.saved_profile
        _vemoji = VEHICLE_TYPES.get(_sp.get('vtype', ''), {}).get('emoji', '🚗')
        _cc1, _cc2, _cc3 = st.columns([3, 6, 1])
        with _cc1:
            st.markdown(
                f"<div style='background:linear-gradient(135deg,#1a237e18,#1565C018);"
                f"border:1px solid #1565C033;border-radius:10px;padding:10px 14px;"
                f"display:flex;align-items:center;gap:10px'>"
                f"<span style='font-size:36px'>{_vemoji}</span>"
                f"<div>"
                f"<div style='font-weight:700;font-size:14px'>"
                f"{_sp.get('brand','')} {_sp.get('model_name','')}</div>"
                f"<div style='font-size:11px;color:#888'>⚙️ {_sp.get('engine','')}</div>"
                f"</div></div>",
                unsafe_allow_html=True
            )
        with _cc3:
            if st.button("↩️", help="Araç değiştir", key="change_vehicle_btn"):
                st.session_state.app_page    = 'select_type'
                st.session_state.saved_profile = None
                st.session_state.last_route    = None
                st.rerun()

    # ── Başlık + Yeni Rota ────────────────────────────────────────────────────
    col_title, col_btn = st.columns([4, 1])
    with col_title:
        st.title("🗺️ Sakarya Akıllı Navigasyon Sistemi")
        st.caption("Araç tipi ve yol yüzeyi temelli optimal rota planlama")
    with col_btn:
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        if st.button("🔄 Yeni Rota", use_container_width=True, key="new_route_btn"):
            st.session_state.last_route = None
            for _k in ['start_lat_live', 'start_lon_live',
                       'end_lat_live',   'end_lon_live',
                       'start_place_name', 'end_place_name',
                       '_prev_start_sel', '_prev_end_sel',
                       '_last_map_click']:
                st.session_state[_k] = None
            for _k in list(st.session_state.keys()):
                if 'searchbox' in str(_k):
                    del st.session_state[_k]
            st.rerun()

    # ── Ana layout ────────────────────────────────────────────────────────────
    col1, col2 = st.columns([1, 2.5], gap="large")

    # ==================== SOL KOLON ====================
    with col1:
        st.subheader("📋 Rota Planlama")

        if st.session_state.graph is None:
            st.session_state.graph = load_graph()

        with st.expander("ℹ️ Sistem Bilgisi"):
            graph_info = get_graph_info(st.session_state.graph)
            st.metric("Düğüm", f"{graph_info['nodes']:,}")
            st.metric("Kenar", f"{graph_info['edges']:,}")
            st.metric("Cache", f"{graph_info['cache_size_mb']:.1f} MB")

        st.divider()

        # Aktif araç profili
        if st.session_state.saved_profile:
            with st.container(border=True):
                st.caption("✅ Aktif Araç Profili")
                _ap = st.session_state.saved_profile
                st.write(f"**{_ap.get('name', 'Bilinmiyor')}**")
                st.caption(f"Profil: `{_ap.get('routing_profile', 'binek')}`")
                vehicle_type = _ap['routing_profile']
        else:
            vehicle_type = 'binek'

        st.divider()

        # ── Saat seçimi ───────────────────────────────────────────────────────
        st.subheader("🕐 Seyahat Saati")
        # key="hour" → Streamlit otomatik session_state.hour'a bağlar (persist)
        hour = st.slider("Saat (Trafik Tahmini)", 0, 23, key="hour", format="%d:00")

        _TRAFFIC: List[tuple] = [
            ((0,  4), "🌙 Gece — Yollar boş"),
            ((5,  5), "🌅 Sabah erken — Az trafik"),
            ((6,  6), "🚨 Sabah trafiği başlıyor"),
            ((7,  9), "🚨 Yoğun sabah trafiği"),
            ((10, 11),"✅ Normal akış"),
            ((12, 13),"🍽️ Öğle saatleri"),
            ((14, 16),"✅ Normal akış"),
            ((17, 19),"🚨 Yoğun akşam trafiği"),
            ((20, 21),"🌆 Akşam — Trafik azalıyor"),
            ((22, 23),"🌙 Gece — Az trafik"),
        ]
        for (_h0, _h1), _lbl in _TRAFFIC:
            if _h0 <= hour <= _h1:
                st.info(_lbl)
                break

        st.divider()

        # ==================== BAŞLANGIÇ NOKTASI ====================
        st.subheader("📍 Başlangıç Noktası")

        _preserve_end = (
            (st.session_state.end_lat_live, st.session_state.end_lon_live)
            if st.session_state.end_lat_live else None
        )
        geo_button_html("start", "#1565C0", preserve_end=_preserve_end)

        # Seçili konum kartı
        if st.session_state.start_lat_live:
            _sc1, _sc2 = st.columns([4, 1])
            with _sc1:
                _sname = st.session_state.get('start_place_name') or ""
                st.markdown(
                    f"<div class='loc-card'>"
                    f"<div class='loc-label'>SEÇİLİ BAŞLANGIÇ</div>"
                    + (f"<div class='loc-name'>{_sname}</div>" if _sname else "")
                    + f"<div class='loc-coords'>"
                    f"📍 {st.session_state.start_lat_live:.5f}, "
                    f"{st.session_state.start_lon_live:.5f}</div></div>",
                    unsafe_allow_html=True
                )
            with _sc2:
                st.markdown("<div style='margin-top:14px'></div>", unsafe_allow_html=True)
                if st.button("✕", key="clear_start",
                             help="Başlangıç noktasını temizle",
                             use_container_width=True):
                    for _k in ['start_lat_live', 'start_lon_live',
                               'start_geo_lat',  'start_geo_lon',
                               'start_place_name']:
                        st.session_state[_k] = None
                    _clear_searchbox('start')
                    st.rerun()

        # ── Arama Kutusu (Google Maps benzeri) ───────────────────────────────
        _preserve_end_s = {}
        if st.session_state.end_lat_live:
            _preserve_end_s['end_geo'] = (
                f"{st.session_state.end_lat_live},{st.session_state.end_lon_live}"
            )
        search_box_html(
            field="start",
            color="#1565C0",
            current_value=st.session_state.get('start_place_name_short') or '',
            preserve=_preserve_end_s,
        )

        _popular_picks("start")

        start_lat = st.session_state.start_lat_live or 40.76
        start_lon = st.session_state.start_lon_live or 30.39

        # ==================== BİTİŞ NOKTASI ====================
        st.subheader("🏁 Bitiş Noktası")

        _preserve_start = (
            (st.session_state.start_lat_live, st.session_state.start_lon_live)
            if st.session_state.start_lat_live else None
        )
        geo_button_html("end", "#C62828", preserve_start=_preserve_start)

        # Seçili konum kartı
        if st.session_state.end_lat_live:
            _ec1, _ec2 = st.columns([4, 1])
            with _ec1:
                _ename = st.session_state.get('end_place_name') or ""
                st.markdown(
                    f"<div class='loc-card loc-card-end'>"
                    f"<div class='loc-label'>SEÇİLİ BİTİŞ</div>"
                    + (f"<div class='loc-name'>{_ename}</div>" if _ename else "")
                    + f"<div class='loc-coords'>"
                    f"🏁 {st.session_state.end_lat_live:.5f}, "
                    f"{st.session_state.end_lon_live:.5f}</div></div>",
                    unsafe_allow_html=True
                )
            with _ec2:
                st.markdown("<div style='margin-top:14px'></div>", unsafe_allow_html=True)
                if st.button("✕", key="clear_end",
                             help="Bitiş noktasını temizle",
                             use_container_width=True):
                    for _k in ['end_lat_live', 'end_lon_live',
                               'end_geo_lat',  'end_geo_lon',
                               'end_place_name']:
                        st.session_state[_k] = None
                    _clear_searchbox('end')
                    st.rerun()

        # ── Arama Kutusu (Google Maps benzeri) ───────────────────────────────
        _preserve_start_e = {}
        if st.session_state.start_lat_live:
            _preserve_start_e['start_geo'] = (
                f"{st.session_state.start_lat_live},{st.session_state.start_lon_live}"
            )
        search_box_html(
            field="end",
            color="#C62828",
            current_value=st.session_state.get('end_place_name_short') or '',
            preserve=_preserve_start_e,
        )

        _popular_picks("end")

        end_lat = st.session_state.end_lat_live or 40.75
        end_lon = st.session_state.end_lon_live or 30.40

        st.divider()

        # ── Rota hesapla butonu ───────────────────────────────────────────────
        if st.button("🔍 Rota Hesapla", use_container_width=True, type="primary"):
            if st.session_state.start_lat_live is None:
                st.warning("⚠️ Lütfen önce bir **başlangıç noktası** seçin.")
            elif st.session_state.end_lat_live is None:
                st.warning("⚠️ Lütfen önce bir **bitiş noktası** seçin.")
            else:
                with st.spinner("Optimal rota hesaplanıyor..."):
                    _result = calculate_route(start_lat, start_lon,
                                              end_lat,   end_lon,
                                              vehicle_type, hour)
                if _result:
                    st.rerun()

        if st.session_state.last_route:
            if st.button("🗑️ Rotayı Temizle", use_container_width=True):
                st.session_state.last_route = None
                st.rerun()

    # ==================== SAĞ KOLON ====================
    with col2:
        st.subheader("🗺️ Harita")

        _VEMOJI: Dict[str, str] = {
            'binek':      '🚗',
            'kamyon':     '🚚',
            'motosiklet': '🏍️',
            'bisiklet':   '🚴',
            'modifiye':   '🚙',
        }

        # Geçmiş rotalar
        if st.session_state.route_history:
            with st.expander(
                f"📜 Geçmiş Rotalar ({len(st.session_state.route_history)})",
                expanded=False
            ):
                for _idx, _hist in enumerate(st.session_state.route_history):
                    _he = _VEMOJI.get(_hist['vehicle'], '🚗')
                    _hc1, _hc2 = st.columns([1, 3])
                    with _hc1:
                        if st.button(_he, key=f"history_{_idx}",
                                     use_container_width=True,
                                     help=f"{_hist['distance']:.1f} km | {_hist['time']}"):
                            st.session_state.last_route = _hist['route_info']
                            st.rerun()
                    with _hc2:
                        _sn = _hist.get('start_name', '')
                        _en = _hist.get('end_name', '')
                        _route_lbl = f"{_sn} → {_en}" if _sn and _en else ""
                        st.caption(
                            f"**{_hist['vehicle'].capitalize()}** · "
                            f"{_hist['distance']:.1f} km · "
                            f"{_hist['time']} · {_hist['timestamp']}"
                            + (f"  \n{_route_lbl}" if _route_lbl else "")
                        )

        if st.session_state.graph:
            # ── Tile seçimi ───────────────────────────────────────────────────
            _tile_choice = st.radio(
                "Harita görünümü",
                list(_TILE_OPTIONS.keys()),
                horizontal=True,
                key="map_tile_radio",
                label_visibility="collapsed",
            )
            _tile_url = _TILE_OPTIONS[_tile_choice]

            # ── Haritayı oluştur ──────────────────────────────────────────────
            _cmp_routes = (
                st.session_state.comparison_routes
                if st.session_state.comparison_mode
                   and st.session_state.comparison_routes
                else None
            )
            _has_alts = (
                not _cmp_routes
                and len(st.session_state.alt_routes) > 1
            )
            folium_map = create_folium_map(
                st.session_state.graph,
                route_info        = st.session_state.last_route if not (_cmp_routes or _has_alts) else None,
                start_lat_live    = st.session_state.start_lat_live,
                start_lon_live    = st.session_state.start_lon_live,
                end_lat_live      = st.session_state.end_lat_live,
                end_lon_live      = st.session_state.end_lon_live,
                start_geo_lat     = st.session_state.start_geo_lat,
                start_geo_lon     = st.session_state.start_geo_lon,
                end_geo_lat       = st.session_state.end_geo_lat,
                end_geo_lon       = st.session_state.end_geo_lon,
                comparison_routes = _cmp_routes,
                tile              = _tile_url,
                alt_routes        = st.session_state.alt_routes if _has_alts else None,
                sel_alt_idx       = st.session_state.sel_alt_idx,
            )

            # ── Harita click modu ─────────────────────────────────────────────
            click_mode = st.radio(
                "Haritadan konum seç",
                ["— Devre Dışı", "📍 Başlangıç Seç", "🏁 Bitiş Seç"],
                horizontal=True,
                key="map_click_mode",
            )
            if click_mode != "— Devre Dışı":
                st.markdown(
                    f"<div class='click-hint'>🖱️ Haritada noktaya tıkla — "
                    f"<b>{click_mode.split(' ', 1)[1]}</b> olarak ayarlanacak</div>",
                    unsafe_allow_html=True
                )

            # ── Harita ───────────────────────────────────────────────────────
            map_data = st_folium(
                folium_map,
                use_container_width=True,
                height=560,
                returned_objects=["last_clicked"],
                key="main_folium_map",
            )

            # ── Tıklama işle ──────────────────────────────────────────────────
            if (map_data and map_data.get('last_clicked')
                    and click_mode != "— Devre Dışı"):
                lc  = map_data['last_clicked']
                _ck = (round(lc['lat'], 5), round(lc['lng'], 5))
                if _ck != st.session_state._last_map_click:
                    st.session_state._last_map_click = _ck
                    if click_mode == "📍 Başlangıç Seç":
                        st.session_state.start_lat_live   = lc['lat']
                        st.session_state.start_lon_live   = lc['lng']
                        st.session_state.start_place_name = (
                            f"Harita ({lc['lat']:.4f}, {lc['lng']:.4f})")
                        _clear_searchbox('start')
                        st.toast(f"📍 Başlangıç: {lc['lat']:.4f}, {lc['lng']:.4f}",
                                 icon="✅")
                    elif click_mode == "🏁 Bitiş Seç":
                        st.session_state.end_lat_live   = lc['lat']
                        st.session_state.end_lon_live   = lc['lng']
                        st.session_state.end_place_name = (
                            f"Harita ({lc['lat']:.4f}, {lc['lng']:.4f})")
                        _clear_searchbox('end')
                        st.toast(f"🏁 Bitiş: {lc['lat']:.4f}, {lc['lng']:.4f}",
                                 icon="✅")
                    st.rerun()

            # ── Alternatif rota seçici ────────────────────────────────────────
            if st.session_state.alt_routes and len(st.session_state.alt_routes) > 1:
                st.markdown("### 🗺️ Rota Seçenekleri")
                _alts = st.session_state.alt_routes
                _N_COL = 3
                for _row_start in range(0, len(_alts), _N_COL):
                    _row = _alts[_row_start:_row_start + _N_COL]
                    _rcols = st.columns(len(_row))
                    for _ci, (_rcol, _ar) in enumerate(zip(_rcols, _row)):
                        _ai = _row_start + _ci
                        _is_sel  = (_ai == st.session_state.sel_alt_idx)
                        _ar_dist = _ar['total_distance_m'] / 1000
                        _ar_time = int(_ar['estimated_time_minutes'])
                        _ar_clr  = _ar.get('route_color', '#1565C0')
                        _border  = _ar_clr if _is_sel else '#3a3d52'
                        _bg      = f"{_ar_clr}22" if _is_sel else "transparent"
                        with _rcol:
                            st.markdown(
                                f"<div style='border:2px solid {_border};"
                                f"border-radius:10px;padding:10px 8px;text-align:center;"
                                f"background:{_bg};margin-bottom:4px'>"
                                f"<div style='font-size:11px;font-weight:700;"
                                f"color:{_ar_clr};margin-bottom:4px'>"
                                f"{_ar.get('route_label','Rota')}</div>"
                                f"<div style='font-size:13px;font-weight:600;color:#dde'>"
                                f"{_ar_dist:.1f} km · {_ar_time} dk</div>"
                                f"</div>",
                                unsafe_allow_html=True
                            )
                            if _is_sel:
                                st.markdown(
                                    "<div style='text-align:center;font-size:11px;"
                                    "color:#4caf50;padding:2px 0 6px'>✓ Seçili</div>",
                                    unsafe_allow_html=True
                                )
                            else:
                                if st.button("Seç", key=f"sel_alt_{_ai}",
                                             use_container_width=True):
                                    st.session_state.sel_alt_idx = _ai
                                    st.session_state.last_route  = _ar
                                    st.rerun()
                st.divider()

            # ── Rota bilgisi ──────────────────────────────────────────────────
            if st.session_state.last_route:
                _r        = st.session_state.last_route
                _surfaces = _r.get('surfaces', [])
                _mods     = (st.session_state.saved_profile.get('modifications', [])
                             if st.session_state.saved_profile else [])
                _vehicle  = _r.get('vehicle_type', 'binek')
                _dist_km  = _r['total_distance_m'] / 1000

                _rlabel = _r.get('route_label', '✅ Rota Bulundu')
                _rcolor = _r.get('route_color', '#1b5e20')
                st.markdown(
                    f"<div class='route-banner' style='background:linear-gradient(90deg,{_rcolor}cc,{_rcolor})'>"
                    f"{_rlabel} &nbsp;|&nbsp; "
                    f"📏 {_dist_km:.2f} km &nbsp;|&nbsp; "
                    f"⏱️ {int(_r['estimated_time_minutes'])} dk &nbsp;|&nbsp; "
                    f"{_VEMOJI.get(_vehicle,'🚗')} {_vehicle.capitalize()}"
                    f"</div>",
                    unsafe_allow_html=True
                )

                # ── Rota Paylaş ───────────────────────────────────────────────
                with st.expander("🔗 Rotayı Paylaş", expanded=False):
                    _sp2 = _r['start_point']
                    _ep2 = _r['end_point']

                    _google_url = (
                        f"https://www.google.com/maps/dir/"
                        f"{_sp2[0]:.6f},{_sp2[1]:.6f}/"
                        f"{_ep2[0]:.6f},{_ep2[1]:.6f}"
                    )
                    _yandex_url = (
                        f"https://yandex.com.tr/harita/?rtext="
                        f"{_sp2[0]:.6f}%2C{_sp2[1]:.6f}"
                        f"~{_ep2[0]:.6f}%2C{_ep2[1]:.6f}&rtt=auto"
                    )
                    _wa_text = (
                        f"🗺️ Sakarya Navigasyon Rotası\n"
                        f"📏 {_dist_km:.1f} km · "
                        f"⏱️ {int(_r['estimated_time_minutes'])} dk\n"
                        f"Google Maps: {_google_url}"
                    )
                    _wa_url = f"https://wa.me/?text={_urlencode(_wa_text)}"

                    _sh1, _sh2, _sh3 = st.columns(3)
                    with _sh1:
                        st.link_button(
                            "🗺️ Google Maps", _google_url,
                            use_container_width=True
                        )
                    with _sh2:
                        st.link_button(
                            "🧭 Yandex Maps", _yandex_url,
                            use_container_width=True
                        )
                    with _sh3:
                        st.link_button(
                            "💬 WhatsApp", _wa_url,
                            use_container_width=True
                        )

                with st.expander("📊 Rota Detayları", expanded=False):
                    _dc1, _dc2, _dc3 = st.columns(3)
                    with _dc1:
                        st.metric("📏 Mesafe", f"{_dist_km:.2f} km")
                    with _dc2:
                        st.metric("⏱️ Süre",   f"{int(_r['estimated_time_minutes'])} dk")
                    with _dc3:
                        st.metric("🕐 Saat", f"{_r['hour']:02d}:00",
                                  delta=f"Trafik ×{_r['traffic_factor']:.2f}",
                                  delta_color="off")
                    st.divider()

                    _quality = vp.calculate_road_quality_score(_surfaces)
                    _qc1, _qc2 = st.columns([1, 3])
                    with _qc1:
                        st.markdown(f"### {_quality['emoji']}")
                    with _qc2:
                        st.write(f"**Yol Kalitesi:** {_quality['quality']} "
                                 f"({_quality['score']}/10)")
                        st.caption(_quality['description'])

                    if _mods:
                        st.divider()
                        _damage = vp.calculate_damage_risk(_surfaces, _mods)
                        _dd1, _dd2 = st.columns([1, 3])
                        with _dd1:
                            st.markdown(f"### {_damage['emoji']}")
                        with _dd2:
                            st.write(f"**Hasar Riski:** {_damage['description']}")
                            st.caption(
                                f"Risk: {_damage['risk_level']:.1f}%  "
                                f"({_damage['count_bad_surfaces']}/"
                                f"{_damage['total_surfaces']} kötü yüzey)"
                            )

                    st.divider()
                    # Karbon emisyonu
                    _co2 = calculate_carbon_emission(_dist_km, _vehicle)
                    _ec1, _ec2, _ec3 = st.columns(3)
                    with _ec1:
                        st.markdown(
                            f"<div style='text-align:center;padding:8px'>"
                            f"<div style='font-size:28px;font-weight:900;"
                            f"color:{_co2['grade_color']}'>{_co2['grade']}</div>"
                            f"<div style='font-size:10px;color:#888'>Emisyon Notu</div>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    with _ec2:
                        st.metric("🌿 CO₂", f"{_co2['total_co2_kg']} kg",
                                  f"{_co2['co2_per_km_g']} g/km",
                                  delta_color="off")
                    with _ec3:
                        st.markdown(
                            f"<div style='font-size:11px;color:#666;padding-top:12px'>"
                            f"{_co2['context']}</div>",
                            unsafe_allow_html=True
                        )

                    st.divider()
                    _cost = vp.calculate_cost_estimate(_dist_km, _surfaces, _mods, _vehicle)
                    st.write("**💰 Maliyet Tahmini**")
                    _cc1, _cc2, _cc3 = st.columns(3)
                    with _cc1:
                        st.metric("Yakıt",
                                  f"{_cost['fuel_consumption_liters']} L",
                                  f"{_cost['fuel_cost_tl']} TL")
                    with _cc2:
                        st.metric("Bakım", f"{_cost['maintenance_cost_tl']} TL")
                    with _cc3:
                        st.metric("Toplam", f"{_cost['total_cost_tl']} TL",
                                  f"{_cost['cost_per_km']} TL/km",
                                  delta_color="off")

                # ── Karşılaştırma ─────────────────────────────────────────────
                st.divider()
                _cmp_lbl = ("❌ Karşılaştırmayı Kapat"
                            if st.session_state.comparison_mode
                            else "🔀 Araç Tiplerini Karşılaştır")
                if st.button(_cmp_lbl, use_container_width=True,
                             key="toggle_comparison"):
                    st.session_state.comparison_mode = not st.session_state.comparison_mode
                    if not st.session_state.comparison_mode:
                        st.session_state.comparison_routes = {}
                    st.rerun()

                if st.session_state.comparison_mode:
                    _CMP_COLORS_TBL = {
                        'binek':      '#1565C0',
                        'kamyon':     '#B71C1C',
                        'modifiye':   '#2E7D32',
                        'motosiklet': '#E65100',
                    }
                    try:
                        _sp2 = _r['start_point']
                        _ep2 = _r['end_point']
                        _hv  = _r['hour']

                        if not st.session_state.comparison_routes:
                            _routes_cmp: Dict = {}
                            with st.spinner("Tüm araç rotaları hesaplanıyor..."):
                                for _vt in ['binek', 'kamyon', 'modifiye', 'motosiklet']:
                                    try:
                                        _ri = calculate_route(
                                            _sp2[0], _sp2[1],
                                            _ep2[0], _ep2[1], _vt, _hv
                                        )
                                        if _ri:
                                            _routes_cmp[_vt] = _ri
                                    except Exception:
                                        pass
                            st.session_state.comparison_routes = _routes_cmp
                            st.rerun()

                        _routes_cmp = st.session_state.comparison_routes
                        if _routes_cmp:
                            _color_badges = " ".join(
                                f'<span style="display:inline-block;width:14px;height:14px;'
                                f'border-radius:50%;background:{_CMP_COLORS_TBL.get(_vt,"#888")};'
                                f'vertical-align:middle;margin-right:3px;"></span>'
                                f'<small>{_VEMOJI.get(_vt,"")}{_vt.capitalize()}</small>'
                                for _vt in _routes_cmp
                            )
                            st.markdown(
                                f"<div style='font-size:12px;margin-bottom:6px'>"
                                f"Haritada renkli çizgiler: {_color_badges}</div>",
                                unsafe_allow_html=True
                            )

                            _cmp_data = []
                            _costs_cmp: Dict[str, float] = {}
                            for _vt, _ri in _routes_cmp.items():
                                _s   = _ri.get('surfaces', [])
                                _dk  = _ri['total_distance_m'] / 1000
                                _q   = vp.calculate_road_quality_score(_s)
                                _c   = vp.calculate_cost_estimate(_dk, _s, [], _vt)
                                _costs_cmp[_vt] = _c['total_cost_tl']
                                _cmp_data.append({
                                    'Araç':        f"{_VEMOJI.get(_vt,'🚗')} {_vt.capitalize()}",
                                    'Mesafe':      f"{_dk:.1f} km",
                                    'Süre':        f"{int(_ri['estimated_time_minutes'])} dk",
                                    'Yol Kal.':    f"{_q['emoji']} {_q['score']}/10",
                                    'Yakıt (L)':   f"{_c['fuel_consumption_liters']:.1f}",
                                    'Yakıt (TL)':  f"{_c['fuel_cost_tl']:.0f}",
                                    'Bakım (TL)':  f"{_c['maintenance_cost_tl']:.0f}",
                                    'Toplam (TL)': f"{_c['total_cost_tl']:.0f}",
                                })

                            _df_cmp = pd.DataFrame(_cmp_data)
                            st.dataframe(_df_cmp, use_container_width=True,
                                         hide_index=True)

                            _best  = min(_costs_cmp, key=_costs_cmp.get)
                            _worst = max(_costs_cmp, key=_costs_cmp.get)
                            _saving = _costs_cmp[_worst] - _costs_cmp[_best]
                            st.success(
                                f"💚 En uygun: **{_VEMOJI.get(_best,'')} "
                                f"{_best.capitalize()}** — "
                                f"{_costs_cmp[_best]:.0f} TL  "
                                f"(diğerlerine göre {_saving:.0f} TL tasarruf)"
                            )
                    except Exception as _e:
                        st.error(f"❌ Karşılaştırma hatası: {_e}")
        else:
            st.warning("⏳ Sistem yükleniyor...")

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(
        "<div style='text-align:center;padding:12px 0 4px;font-size:12px;color:#888'>"
        "🗺️ <b>Sakarya Akıllı Navigasyon Sistemi</b> &nbsp;|&nbsp; "
        "Python &nbsp;·&nbsp; OSMnx &nbsp;·&nbsp; NetworkX &nbsp;·&nbsp; "
        "Streamlit &nbsp;·&nbsp; Folium"
        "</div>",
        unsafe_allow_html=True
    )
