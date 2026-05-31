"""
Sakarya'da popüler araç katalogu — marka/model/motor seçimi
"""
import base64


def _svg_uri(svg: str) -> str:
    """SVG string'i base64 data URI'ye çevir."""
    return "data:image/svg+xml;base64," + base64.b64encode(svg.strip().encode()).decode()


# SVG logolar: SimpleIcons'ta olmayan markalar için
_BRAND_SVGS: dict = {
    'Mercedes-Benz': (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<circle cx="50" cy="50" r="49" fill="#1c1c1c"/>'
        '<circle cx="50" cy="50" r="47" fill="none" stroke="#aaa" stroke-width="1.5"/>'
        '<line x1="50" y1="50" x2="50" y2="6" stroke="#ddd" stroke-width="3.5" stroke-linecap="round"/>'
        '<line x1="50" y1="50" x2="89" y2="71" stroke="#ddd" stroke-width="3.5" stroke-linecap="round"/>'
        '<line x1="50" y1="50" x2="11" y2="71" stroke="#ddd" stroke-width="3.5" stroke-linecap="round"/>'
        '<circle cx="50" cy="6" r="3.5" fill="#ddd"/>'
        '<circle cx="89" cy="71" r="3.5" fill="#ddd"/>'
        '<circle cx="11" cy="71" r="3.5" fill="#ddd"/>'
        '<circle cx="50" cy="50" r="4" fill="#ddd"/>'
        '</svg>'
    ),
    'Kawasaki': (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 64">'
        '<rect width="220" height="64" fill="#111"/>'
        '<text x="110" y="44" font-family="Arial Black,sans-serif" font-weight="900"'
        ' font-size="26" text-anchor="middle" fill="#00a651" letter-spacing="1">KAWASAKI</text>'
        '</svg>'
    ),
    'Yamaha': (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 180 60">'
        '<rect width="180" height="60" fill="#fff"/>'
        '<text x="90" y="42" font-family="Arial Black,sans-serif" font-weight="900"'
        ' font-size="28" text-anchor="middle" fill="#1a2faa" letter-spacing="2">YAMAHA</text>'
        '</svg>'
    ),
    'Land Rover': (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 64">'
        '<rect width="200" height="64" fill="#f5f5f5"/>'
        '<ellipse cx="100" cy="32" rx="96" ry="27" fill="none" stroke="#005a1f" stroke-width="2.5"/>'
        '<text x="100" y="37" font-family="Arial,sans-serif" font-weight="bold"'
        ' font-size="14" text-anchor="middle" fill="#005a1f" letter-spacing="2">LAND ROVER</text>'
        '</svg>'
    ),
    'Tofas': (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 180 60">'
        '<rect width="180" height="60" fill="#fff"/>'
        '<text x="90" y="43" font-family="Arial Black,sans-serif" font-weight="900"'
        ' font-size="30" text-anchor="middle" fill="#cc0000">TOFAŞ</text>'
        '</svg>'
    ),
    'Isuzu': (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 180 60">'
        '<rect width="180" height="60" fill="#fff"/>'
        '<text x="90" y="43" font-family="Arial Black,sans-serif" font-weight="900"'
        ' font-size="30" text-anchor="middle" fill="#cc0022" letter-spacing="2">ISUZU</text>'
        '</svg>'
    ),
    'BMW Motorrad': None,   # BMW logosunu kullan
}

# Önbelleğe alınmış data URI'ler
_BRAND_SVG_URIS: dict = {
    brand: _svg_uri(svg) if svg else None
    for brand, svg in _BRAND_SVGS.items()
}


def get_brand_logo_html(brand: str, size: int = 44) -> str:
    """Marka için logo HTML döndür: SimpleIcons URL → SVG data URI → emoji."""
    url = BRAND_LOGO_URLS.get(brand, '')
    if url:
        return (
            f"<img src='{url}' "
            f"style='max-height:{size}px;max-width:{size * 2}px;object-fit:contain'"
            f" onerror=\"this.style.display='none'\">"
        )
    if brand == 'BMW Motorrad':
        return (
            f"<img src='https://cdn.simpleicons.org/bmw' "
            f"style='max-height:{size}px;max-width:{size * 2}px;object-fit:contain'>"
        )
    uri = _BRAND_SVG_URIS.get(brand)
    if uri:
        return (
            f"<img src='{uri}' "
            f"style='max-height:{size}px;max-width:{size * 2}px;object-fit:contain'>"
        )
    return f"<span style='font-size:{size - 8}px'>{BRAND_EMOJI.get(brand, '🚘')}</span>"

VEHICLE_TYPES = {
    'otomobil': {'label': '🚗 Otomobil', 'routing_profile': 'binek', 'emoji': '🚗'},
    'arazi_suv': {'label': '🚙 Arazi / SUV / Pickup', 'routing_profile': 'modifiye', 'emoji': '🚙'},
    'motosiklet': {'label': '🏍️ Motosiklet', 'routing_profile': 'motosiklet', 'emoji': '🏍️'},
}

BRAND_EMOJI = {
    # Otomobil markaları
    'Audi': '🔵',
    'BMW': '🔷',
    'Fiat': '🇮🇹',
    'Ford': '🔵',
    'Honda': '⭕',
    'Hyundai': '🔵',
    'Kia': '🔴',
    'Mercedes-Benz': '⭐',
    'Nissan': '⚙️',
    'Renault': '💎',
    'Tofas': '🇹🇷',
    'Toyota': '🔴',
    'Volkswagen': '🔵',
    'Volvo': '🔵',
    # Arazi/SUV markaları
    'Dacia': '🟡',
    'Isuzu': '🔩',
    'Jeep': '🟢',
    'Land Rover': '🦁',
    'Mitsubishi': '♦️',
    # Motosiklet markaları
    'Kawasaki': '🟢',
    'Suzuki': '🔵',
    'Yamaha': '🔵',
    'BMW Motorrad': '🔷',
}

BRAND_LOGO_URLS = {
    # cdn.simpleicons.org — doğrulanan markalar
    'Audi':       'https://cdn.simpleicons.org/audi',
    'BMW':        'https://cdn.simpleicons.org/bmw',
    'Fiat':       'https://cdn.simpleicons.org/fiat',
    'Ford':       'https://cdn.simpleicons.org/ford',
    'Honda':      'https://cdn.simpleicons.org/honda',
    'Hyundai':    'https://cdn.simpleicons.org/hyundai',
    'Kia':        'https://cdn.simpleicons.org/kia',
    'Nissan':     'https://cdn.simpleicons.org/nissan',
    'Renault':    'https://cdn.simpleicons.org/renault',
    'Toyota':     'https://cdn.simpleicons.org/toyota',
    'Volkswagen': 'https://cdn.simpleicons.org/volkswagen',
    'Volvo':      'https://cdn.simpleicons.org/volvo',
    'Dacia':      'https://cdn.simpleicons.org/dacia',
    'Jeep':       'https://cdn.simpleicons.org/jeep',
    'Mitsubishi': 'https://cdn.simpleicons.org/mitsubishi',
    'Suzuki':     'https://cdn.simpleicons.org/suzuki',
    # Aşağıdakiler SimpleIcons'ta yok → emoji fallback (URL boş)
    'Mercedes-Benz': '',
    'Tofas':         '',
    'Isuzu':         '',
    'Land Rover':    '',
    'Kawasaki':      '',
    'Yamaha':        '',
    'BMW Motorrad':  '',
}

CATALOG = {
    'otomobil': {
        'Audi': {
            'A3': ['1.0 TFSI 110bg', '1.4 TFSI 150bg', '1.5 TFSI 150bg', '2.0 TDI 150bg'],
            'A4': ['1.4 TFSI 150bg', '2.0 TFSI 190bg', '2.0 TDI 150bg'],
            'Q3': ['1.5 TFSI 150bg', '2.0 TDI 150bg'],
            'Q5': ['2.0 TDI 190bg', '2.0 TFSI 252bg'],
        },
        'BMW': {
            '1 Serisi': ['116d', '118i', '118d', '120d'],
            '3 Serisi': ['316i', '318i', '320i', '320d', '330i'],
            '5 Serisi': ['520i', '520d', '530i'],
            'X1': ['sDrive18i', 'sDrive20d'],
            'X3': ['xDrive20d', 'xDrive20i'],
        },
        'Fiat': {
            'Egea': ['1.4 Fire 95bg', '1.6 Multijet 120bg', '1.3 Multijet 95bg'],
            'Tipo': ['1.4 100bg', '1.6 D Multijet 120bg'],
            'Punto': ['1.4 8V 77bg', '1.3 Multijet 75bg'],
        },
        'Ford': {
            'Focus': ['1.0 EcoBoost 100bg', '1.0 EcoBoost 125bg', '1.5 EcoBoost 150bg', '1.5 TDCi 95bg'],
            'Fiesta': ['1.0 EcoBoost 100bg', '1.1 Ti-VCT 75bg', '1.5 TDCi 85bg'],
            'Mondeo': ['1.5 EcoBoost 160bg', '2.0 TDCi 150bg'],
        },
        'Honda': {
            'Civic': ['1.5 VTEC Turbo 182bg', '1.6 i-DTEC 120bg', '1.8 i-VTEC 142bg'],
            'CR-V': ['1.5 VTEC Turbo 193bg', '1.6 i-DTEC 120bg'],
            'HR-V': ['1.5 i-VTEC 130bg'],
        },
        'Hyundai': {
            'i20': ['1.0 T-GDI 100bg', '1.2 MPI 75bg', '1.4 MPI 100bg'],
            'i30': ['1.0 T-GDI 120bg', '1.4 T-GDI 140bg', '1.6 CRDi 110bg'],
            'Elantra': ['1.6 MPI 132bg'],
            'Tucson': ['1.6 T-GDI 150bg', '2.0 MPi 155bg', '1.7 CRDi 115bg'],
        },
        'Kia': {
            "Cee'd": ['1.0 T-GDI 120bg', '1.4 T-GDI 140bg', '1.6 CRDi 115bg'],
            'Picanto': ['1.0 MPI 67bg', '1.2 MPI 84bg'],
            'Stonic': ['1.0 T-GDI 100bg'],
            'Sportage': ['1.6 T-GDI 177bg', '2.0 MPi 163bg'],
        },
        'Mercedes-Benz': {
            'A Serisi': ['A 180d', 'A 200', 'A 180', 'A 250'],
            'C Serisi': ['C 180', 'C 200', 'C 220d', 'C 250d'],
            'E Serisi': ['E 200', 'E 220d', 'E 250'],
            'GLA': ['GLA 180', 'GLA 200', 'GLA 220d'],
        },
        'Nissan': {
            'Qashqai': ['1.3 DIG-T 140bg', '1.5 dCi 115bg', '1.6 dCi 130bg'],
            'Juke': ['1.0 DIG-T 117bg', '1.5 dCi 110bg'],
            'Micra': ['1.0 IG-T 100bg', '0.9 DIG-T 90bg'],
        },
        'Renault': {
            'Clio': ['1.0 SCe 75bg', '1.0 TCe 100bg', '1.5 dCi 90bg', '0.9 TCe 90bg'],
            'Symbol': ['1.5 dCi 90bg', '1.2 16V 75bg'],
            'Megane': ['1.3 TCe 115bg', '1.3 TCe 160bg', '1.5 dCi 90bg'],
            'Kadjar': ['1.3 TCe 140bg', '1.5 dCi 115bg'],
            'Captur': ['1.0 TCe 100bg', '1.5 dCi 90bg'],
        },
        'Tofas': {
            'Egea': ['1.4 Fire 95bg', '1.6 Multijet 120bg'],
            'Dogan': ['1.6 8V 82bg'],
            'Sahin': ['1.6 8V 82bg'],
        },
        'Toyota': {
            'Corolla': ['1.6 Valvematic 132bg', '1.8 Hibrit 122bg', '2.0 D-4D 143bg'],
            'Yaris': ['1.0 VVT-i 72bg', '1.5 Hibrit 100bg'],
            'C-HR': ['1.8 Hibrit 122bg', '2.0 Hibrit 184bg'],
            'Auris': ['1.6 Valvematic 132bg', '1.8 Hibrit 136bg'],
        },
        'Volkswagen': {
            'Golf': ['1.0 TSI 115bg', '1.5 TSI 130bg', '2.0 TDI 115bg', '2.0 TDI 150bg'],
            'Polo': ['1.0 MPI 65bg', '1.0 TSI 95bg', '1.0 TSI 115bg', '1.6 TDI 95bg'],
            'Passat': ['1.5 TSI 150bg', '2.0 TDI 150bg', '2.0 TDI 190bg'],
            'Jetta': ['1.4 TSI 125bg', '1.6 TDI 105bg'],
        },
        'Volvo': {
            'S60': ['T4 190bg', 'T5 245bg', 'D3 150bg', 'D4 190bg'],
            'V40': ['T2 122bg', 'D2 120bg'],
            'XC60': ['T5 245bg', 'D4 190bg', 'D5 AWD 235bg'],
        },
    },

    'arazi_suv': {
        'Dacia': {
            'Duster': ['1.0 TCe 100bg', '1.3 TCe 150bg', '1.5 dCi 95bg', 'Blue dCi 115bg'],
        },
        'Ford': {
            'Kuga': ['1.5 EcoBoost 150bg', '1.5 EcoBlue 120bg', '2.0 EcoBlue 150bg'],
            'Ranger': ['2.0 EcoBlue 170bg', '2.0 EcoBlue 213bg', '3.2 TDCi 200bg'],
        },
        'Hyundai': {
            'Tucson': ['1.6 T-GDI 150bg', '2.0 MPi 155bg', '1.6 CRDi 136bg'],
            'Santa Fe': ['2.2 CRDi 200bg', '2.0 T-GDI 240bg'],
            'Kona': ['1.0 T-GDI 120bg', '1.6 T-GDI 177bg'],
        },
        'Isuzu': {
            'D-Max': ['1.9 DTH 164bg', '3.0 DTH 190bg'],
        },
        'Jeep': {
            'Renegade': ['1.0 T3 120bg', '1.3 T4 150bg'],
            'Compass': ['1.3 T4 150bg', '2.0 Multijet 140bg'],
        },
        'Kia': {
            'Sportage': ['1.6 T-GDI 177bg', '2.0 MPi 163bg', '1.6 CRDi 136bg'],
            'Sorento': ['2.2 CRDi 200bg', '2.0 T-GDI 235bg'],
        },
        'Land Rover': {
            'Discovery Sport': ['2.0 Si4 290bg', '2.0 SD4 240bg'],
            'Defender': ['2.0 Si4 300bg', '3.0 Si6 400bg'],
        },
        'Mitsubishi': {
            'L200': ['2.2 MIVEC 150bg', '2.4 MIVEC 181bg'],
            'Outlander': ['2.0 MIVEC 150bg', '2.4 MIVEC 167bg'],
            'ASX': ['1.6 MIVEC 117bg'],
        },
        'Nissan': {
            'Qashqai': ['1.3 DIG-T 140bg', '1.5 dCi 115bg'],
            'X-Trail': ['2.0 dCi 177bg', '1.6 dCi 130bg'],
            'Navara': ['2.3 dCi 163bg', '2.3 dCi 190bg'],
        },
        'Renault': {
            'Duster': ['1.0 TCe 100bg', '1.3 TCe 150bg', '1.5 dCi 95bg'],
            'Kadjar': ['1.3 TCe 140bg', '1.5 dCi 115bg'],
        },
        'Toyota': {
            'RAV4': ['2.0 Valvematic 173bg', '2.5 Hibrit 218bg', '2.0 D-4D 143bg'],
            'Land Cruiser': ['2.8 D-4D 204bg', '4.5 D-4D 272bg'],
            'Hilux': ['2.4 D-4D 150bg', '2.8 D-4D 204bg'],
        },
        'Volkswagen': {
            'Tiguan': ['1.5 TSI 150bg', '2.0 TDI 150bg', '2.0 TSI 190bg'],
            'T-Roc': ['1.0 TSI 115bg', '1.5 TSI 150bg', '2.0 TDI 150bg'],
        },
    },

    'motosiklet': {
        'Honda': {
            'CB500F': ['471cc 47bg'],
            'CB650R': ['649cc 95bg'],
            'CBR600RR': ['599cc 121bg'],
            'PCX 125': ['125cc 12bg'],
            'Forza 300': ['279cc 26bg'],
        },
        'Kawasaki': {
            'Z400': ['399cc 45bg'],
            'Z650': ['649cc 68bg'],
            'Z900': ['948cc 125bg'],
            'Ninja 400': ['399cc 45bg'],
            'Ninja 650': ['649cc 68bg'],
        },
        'Suzuki': {
            'GSX-S750': ['749cc 105bg'],
            'Burgman 400': ['399cc 34bg'],
            'V-Strom 650': ['645cc 70bg'],
            'SV650': ['645cc 76bg'],
        },
        'Yamaha': {
            'MT-07': ['689cc 74bg'],
            'MT-09': ['889cc 119bg'],
            'YZF-R6': ['599cc 118bg'],
            'XMAX 300': ['292cc 28bg'],
            'NMAX 125': ['125cc 12bg'],
        },
        'BMW Motorrad': {
            'R 1250 GS': ['1254cc 136bg'],
            'S 1000 RR': ['999cc 210bg'],
            'F 900 R': ['895cc 105bg'],
            'G 310 R': ['313cc 34bg'],
        },
    },
}

# Tofas display label override
BRAND_DISPLAY_LABELS = {
    'Tofas': 'Tofaş',
}


def get_brands(vehicle_type: str) -> list:
    """Seçili araç tipindeki markaları döndür"""
    return sorted(CATALOG.get(vehicle_type, {}).keys())


def get_models(vehicle_type: str, brand: str) -> list:
    """Seçili marka için modelleri döndür"""
    return sorted(CATALOG.get(vehicle_type, {}).get(brand, {}).keys())


def get_engines(vehicle_type: str, brand: str, model: str) -> list:
    """Seçili model için motor seçeneklerini döndür"""
    return CATALOG.get(vehicle_type, {}).get(brand, {}).get(model, [])


def get_routing_profile(vehicle_type: str) -> str:
    """Araç tipine göre routing profili döndür"""
    return VEHICLE_TYPES.get(vehicle_type, {}).get('routing_profile', 'binek')


def get_display_label(vehicle_type: str) -> str:
    """Araç tipi için gösterim etiketi"""
    return VEHICLE_TYPES.get(vehicle_type, {}).get('label', vehicle_type)
