"""
Araç tipi profilleri ve yol tercihlerine göre maliyet katsayıları
Sakarya ili akıllı navigasyon sistemi için
"""

# ==================== ARAÇ VERİTABANI ====================

VEHICLE_CATEGORIES = {
    'sedan': {
        'name': 'Sedan',
        'emoji': '🚗',
        'vehicles': [
            'Renault Megane',
            'Toyota Corolla',
            'Fiat Egea',
            'Honda Civic',
            'Hyundai Elantra'
        ]
    },
    'hatchback': {
        'name': 'Hatchback',
        'emoji': '🚙',
        'vehicles': [
            'Volkswagen Golf',
            'Renault Clio',
            'Opel Astra',
            'Ford Focus'
        ]
    },
    'suv': {
        'name': 'SUV/Crossover',
        'emoji': '🚕',
        'vehicles': [
            'Toyota RAV4',
            'Renault Kadjar',
            'Hyundai Tucson',
            'Dacia Duster'
        ]
    },
    'ticari': {
        'name': 'Ticari',
        'emoji': '🚐',
        'vehicles': [
            'Ford Transit',
            'Volkswagen Transporter',
            'Fiat Ducato',
            'Renault Master'
        ]
    },
    'kamyon': {
        'name': 'Kamyon',
        'emoji': '🚚',
        'vehicles': [
            'Ford Cargo',
            'MAN TGS',
            'Mercedes Actros'
        ]
    },
    'motorsiklet': {
        'name': 'Motorsiklet',
        'emoji': '🏍️',
        'vehicles': [
            'Honda CB500',
            'Yamaha MT-07'
        ]
    },
    'arazi': {
        'name': 'Arazi',
        'emoji': '🚙',
        'vehicles': [
            'Toyota Land Cruiser',
            'Mitsubishi L200',
            'Ford Ranger'
        ]
    },
    'diger': {
        'name': 'Diğer',
        'emoji': '❓',
        'vehicles': [
            'Demo — Zamanla güncellenecektir'
        ]
    }
}

MODIFICATIONS = {
    'lowering': {
        'name': 'Alçaltma / Lowering',
        'emoji': '⬇️',
        'effect': 'Yüksek kaliteli yollarda hız artışı, kötü yollarda risk ↑'
    },
    'lift': {
        'name': 'Yükseltme / Lift Kit',
        'emoji': '⬆️',
        'effect': 'Arazi yollarında başarı ↑, stabilite ↓'
    },
    'offset': {
        'name': 'Geniş Lastik / Offset',
        'emoji': '🔄',
        'effect': 'Grip ↑, yakıt tüketimi ↑'
    },
    'bodykit': {
        'name': 'Body Kit',
        'emoji': '✨',
        'effect': 'Estetik, havalı görünüm (teknik etki yok)'
    },
    'cargo': {
        'name': 'Yük Eklentisi',
        'emoji': '📦',
        'effect': 'Yükleme kapasitesi ↑, hız & verim ↓'
    }
}

# ==================== PROFIL SİSTEMİ ====================

VEHICLE_PROFILES = {
    'binek': {
        'description': 'Standart otomobil - yüksek hızlı ana yolları tercih eder',
        'highways': {
            'motorway': 0.5,        # Otoyolları tercih et
            'trunk': 0.6,           # Ana yollar
            'primary': 0.7,
            'secondary': 0.85,
            'tertiary': 1.0,
            'residential': 1.2,
            'unclassified': 1.3,
            'living_street': 1.5,
            'track': 2.0,           # Geçmedik yollar
            'path': 2.5,
            'footway': 2.5,
            'bridleway': 2.5,
            'cycleway': 1.8,
        },
        'surfaces': {
            'asphalt': 1.0,
            'concrete': 1.0,
            'paved_smooth': 1.05,
            'paved': 1.05,
            'cobblestone': 1.15,
            'unpaved': 1.4,
            'gravel': 1.5,
            'dirt': 1.8,
            'sand': 2.0,
            'grass': 2.5,
            'mud': 2.5,
        },
        'traffic_factor': {
            # Saat bazlı trafik çarpanları (0-23)
            0: 0.8,   # Gece 00:00
            1: 0.75,
            2: 0.7,
            3: 0.7,
            4: 0.8,
            5: 1.0,
            6: 1.3,   # Sabah trafik
            7: 1.6,
            8: 1.8,
            9: 1.4,
            10: 1.1,
            11: 1.0,
            12: 1.2,  # Öğle
            13: 1.0,
            14: 0.95,
            15: 1.0,
            16: 1.1,
            17: 1.6,  # Akşam trafik
            18: 1.8,
            19: 1.5,
            20: 1.2,
            21: 1.0,
            22: 0.9,
            23: 0.85,
        }
    },
    'kamyon': {
        'description': 'Ağır vasıta - geniş yolları tercih eder, keskin virajları seviyor',
        'highways': {
            'motorway': 0.6,
            'trunk': 0.55,          # Kamyon yolları tercih eder
            'primary': 0.65,
            'secondary': 0.8,
            'tertiary': 0.95,
            'residential': 1.3,
            'unclassified': 1.4,
            'living_street': 2.0,
            'track': 1.8,
            'path': 2.5,
            'footway': 2.5,
            'bridleway': 2.5,
            'cycleway': 2.2,
        },
        'surfaces': {
            'asphalt': 1.0,
            'concrete': 0.95,       # Kamyonlar beton yollarda daha verimli
            'paved_smooth': 1.05,
            'paved': 1.05,
            'cobblestone': 1.3,
            'unpaved': 1.6,
            'gravel': 1.7,
            'dirt': 2.0,
            'sand': 2.3,
            'grass': 2.8,
            'mud': 2.8,
        },
        'traffic_factor': {
            0: 0.7,
            1: 0.65,
            2: 0.6,
            3: 0.6,
            4: 0.7,
            5: 1.0,
            6: 1.2,
            7: 1.4,   # Kamyonlar sabah trafiğinde daha az etkilenir
            8: 1.3,
            9: 1.0,
            10: 0.95,
            11: 0.9,
            12: 1.0,
            13: 0.95,
            14: 0.9,
            15: 0.95,
            16: 1.1,
            17: 1.3,
            18: 1.2,
            19: 1.0,
            20: 0.95,
            21: 0.9,
            22: 0.8,
            23: 0.75,
        }
    },
    'motosiklet': {
        'description': 'Motosiklet - dar sokakları ve manevra yollarını tercih eder',
        'highways': {
            'motorway': 1.0,
            'trunk': 0.9,
            'primary': 0.8,
            'secondary': 0.7,
            'tertiary': 0.6,
            'residential': 0.5,     # Şehir içi tercih
            'unclassified': 0.6,
            'living_street': 0.7,
            'track': 0.8,
            'path': 1.2,
            'footway': 1.5,
            'bridleway': 1.5,
            'cycleway': 0.6,        # Bisiklet yollarında rahat
        },
        'surfaces': {
            'asphalt': 1.0,
            'concrete': 1.0,
            'paved_smooth': 1.0,
            'paved': 1.05,
            'cobblestone': 1.2,
            'unpaved': 1.3,
            'gravel': 1.4,
            'dirt': 1.5,
            'sand': 1.8,
            'grass': 2.0,
            'mud': 2.2,
        },
        'traffic_factor': {
            0: 0.85,
            1: 0.8,
            2: 0.75,
            3: 0.75,
            4: 0.85,
            5: 1.1,
            6: 1.2,
            7: 1.1,    # Motosikletler trafikten daha az etkilenir
            8: 1.0,
            9: 0.95,
            10: 0.9,
            11: 0.85,
            12: 0.9,
            13: 0.85,
            14: 0.8,
            15: 0.85,
            16: 1.0,
            17: 1.2,
            18: 1.1,
            19: 0.95,
            20: 0.9,
            21: 0.85,
            22: 0.8,
            23: 0.8,
        }
    },
    'bisiklet': {
        'description': 'Bisiklet - bisiklet yolları ve düşük hızlı sakinlik alanlarını tercih eder',
        'highways': {
            'motorway': 2.5,        # Motor kargo yasak
            'trunk': 2.5,
            'primary': 1.8,
            'secondary': 1.2,
            'tertiary': 0.8,
            'residential': 0.5,     # Sakin sokaklar
            'unclassified': 0.7,
            'living_street': 0.4,   # Yaşayan sokaklar en iyi
            'track': 0.9,
            'path': 0.6,            # Yaya yolları tercih
            'footway': 0.7,
            'bridleway': 0.8,
            'cycleway': 0.3,        # Bisiklet yolları mükemmel
        },
        'surfaces': {
            'asphalt': 1.0,
            'concrete': 1.0,
            'paved_smooth': 1.0,
            'paved': 1.05,
            'cobblestone': 1.2,
            'unpaved': 1.4,
            'gravel': 1.5,
            'dirt': 1.6,
            'sand': 2.0,
            'grass': 1.8,
            'mud': 2.2,
        },
        'traffic_factor': {
            0: 1.0,    # Gece az tercih
            1: 1.0,
            2: 1.0,
            3: 1.0,
            4: 1.0,
            5: 0.9,
            6: 0.8,    # Sabah sporuna tercih
            7: 0.7,
            8: 0.85,
            9: 1.0,
            10: 0.9,
            11: 0.85,
            12: 1.0,
            13: 1.0,
            14: 0.9,
            15: 0.9,
            16: 1.0,
            17: 1.1,
            18: 0.9,   # Akşam sporuna tercih
            19: 0.85,
            20: 0.95,
            21: 1.0,
            22: 1.0,
            23: 1.0,
        }
    },
    'modifiye': {
        'description': 'Modifiye araç (basık) - daha dar geçişler ve yan yolları tercih eder',
        'highways': {
            'motorway': 0.9,
            'trunk': 0.8,
            'primary': 0.85,
            'secondary': 0.9,
            'tertiary': 0.8,
            'residential': 0.6,     # Şehir içinde daha rahat
            'unclassified': 0.7,
            'living_street': 0.8,
            'track': 1.0,           # Off-road yeteneklidir
            'path': 1.3,
            'footway': 1.5,
            'bridleway': 1.2,
            'cycleway': 1.0,
        },
        'surfaces': {
            'asphalt': 1.0,
            'concrete': 0.98,
            'paved_smooth': 1.02,
            'paved': 1.05,
            'cobblestone': 1.1,     # Düşük yer öne daha kolay geçer
            'unpaved': 0.95,        # Off-road yetenekli
            'gravel': 0.9,
            'dirt': 0.85,
            'sand': 1.0,
            'grass': 1.1,
            'mud': 1.2,
        },
        'traffic_factor': {
            0: 0.9,
            1: 0.85,
            2: 0.8,
            3: 0.8,
            4: 0.9,
            5: 1.2,
            6: 1.4,
            7: 1.5,    # Sabah trafiğinde geç kalır
            8: 1.3,
            9: 1.0,
            10: 1.0,
            11: 0.95,
            12: 1.0,
            13: 0.95,
            14: 0.9,
            15: 1.0,
            16: 1.1,
            17: 1.3,
            18: 1.4,
            19: 1.2,
            20: 1.0,
            21: 0.95,
            22: 0.9,
            23: 0.9,
        }
    }
}


def get_vehicle_profile(vehicle_type: str) -> dict:
    """
    Belirtilen araç tipi için profil döndür
    
    Args:
        vehicle_type: Araç tipi ('binek', 'kamyon', 'motosiklet', 'bisiklet', 'modifiye')
    
    Returns:
        Araç profili sözlüğü
    
    Raises:
        ValueError: Geçersiz araç tipi
    """
    if vehicle_type not in VEHICLE_PROFILES:
        raise ValueError(
            f"Geçersiz araç tipi: {vehicle_type}. "
            f"Seçenekler: {', '.join(VEHICLE_PROFILES.keys())}"
        )
    return VEHICLE_PROFILES[vehicle_type]


def get_highway_cost(vehicle_type: str, highway_type: str) -> float:
    """
    Belirtilen araç ve yol tipi kombinas iyonu için maliyet katsayısını döndür
    
    Args:
        vehicle_type: Araç tipi
        highway_type: Yol tipi (highway tag'i)
    
    Returns:
        Maliyet katsayısı (1.0 = temel maliyet)
    """
    profile = get_vehicle_profile(vehicle_type)
    return profile['highways'].get(highway_type, 1.5)  # Bilinmeyen yol tipi için yüksek maliyet


def get_surface_cost(vehicle_type: str, surface_type: str) -> float:
    """
    Belirtilen araç ve yüzey tipi kombinasyonu için maliyet katsayısını döndür
    
    Args:
        vehicle_type: Araç tipi
        surface_type: Yüzey tipi (surface tag'i)
    
    Returns:
        Maliyet katsayısı (1.0 = temel maliyet)
    """
    profile = get_vehicle_profile(vehicle_type)
    return profile['surfaces'].get(surface_type, 1.5)  # Bilinmeyen yüzey tipi için yüksek maliyet


def get_traffic_factor(vehicle_type: str, hour: int) -> float:
    """
    Belirtilen araç tipi ve saat için trafik çarpanını döndür
    
    Args:
        vehicle_type: Araç tipi
        hour: Saat (0-23)
    
    Returns:
        Trafik çarpanı (1.0 = normal trafik yoğunluğu)
    """
    if not 0 <= hour <= 23:
        raise ValueError(f"Geçersiz saat: {hour}. 0-23 aralığında olmalı.")
    
    profile = get_vehicle_profile(vehicle_type)
    return profile['traffic_factor'][hour]


def list_vehicles() -> list:
    """Mevcut araç tiplerine döndür"""
    return list(VEHICLE_PROFILES.keys())


def get_vehicle_category_emoji(category: str) -> str:
    """Kategori emoji döndür"""
    return VEHICLE_CATEGORIES.get(category, {}).get('emoji', '❓')


def get_vehicles_by_category(category: str) -> list:
    """Kategoriye göre araçları döndür"""
    return VEHICLE_CATEGORIES.get(category, {}).get('vehicles', [])


def get_modifications() -> dict:
    """Tüm modifiye seçeneklerini döndür"""
    return MODIFICATIONS


def map_model_to_profile(model_name: str, category: str, modifications: list = None) -> str:
    """Model adından en uygun profili seç"""
    modifications = modifications or []
    
    # Basit mapping
    if any(keyword in model_name.lower() for keyword in ['megane', 'clio', 'golf', 'focus', 'civic']):
        return 'binek'
    elif any(keyword in model_name.lower() for keyword in ['transit', 'transporter', 'ducato', 'master']):
        return 'kamyon'
    elif category in ['motorsiklet']:
        return 'motosiklet'
    elif category in ['arazi', 'suv']:
        return 'modifiye' if 'lowering' in modifications or 'lift' in modifications else 'binek'
    elif category in ['ticari']:
        return 'kamyon'
    else:
        return 'binek'


def calculate_profile_penalty(modifications: list) -> dict:
    """Modifiye seçeneklerine göre profil cezaları hesapla"""
    penalty = {
        'speed_multiplier': 1.0,  # Hız çarpanı
        'fuel_efficiency': 1.0,   # Yakıt verimliliği
        'comfort': 1.0,           # Konfor
        'surface_penalty': {},    # Yüzey cezaları
    }
    
    if 'lowering' in modifications:
        penalty['speed_multiplier'] *= 1.1
        penalty['comfort'] *= 0.8
        penalty['surface_penalty']['cobblestone'] = 1.5
        penalty['surface_penalty']['unpaved'] = 2.0
    
    if 'lift' in modifications:
        penalty['surface_penalty']['asphalt'] = 1.15
        penalty['surface_penalty']['gravel'] = 0.6
        penalty['comfort'] *= 0.9
    
    if 'offset' in modifications:
        penalty['fuel_efficiency'] *= 0.9
        penalty['speed_multiplier'] *= 1.05
    
    if 'cargo' in modifications:
        penalty['fuel_efficiency'] *= 0.85
        penalty['speed_multiplier'] *= 0.9
    
    return penalty


# ==================== METRİK HESAPLAMA FONKSİYONLARI ====================

def calculate_road_quality_score(route_surfaces: list) -> dict:
    """
    Rota yüzey kalitelerinden 1-10 skoru hesapla
    
    Args:
        route_surfaces: Rota kenarlarındaki surface değerleri listesi
    
    Returns:
        {'score': 1-10, 'color': 'green'|'yellow'|'red', 'quality': 'İyi'|'Orta'|'Kötü'}
    """
    
    # Surface kalite puanları
    quality_map = {
        'asphalt': 9,
        'concrete': 10,
        'paved': 8,
        'paved_smooth': 9,
        'cobblestone': 5,
        'cobblestone:flattened': 6,
        'gravel': 3,
        'unpaved': 3,
        'dirt': 2,
        'mud': 2,
        'sand': 3,
        'stabilized': 5,
    }
    
    if not route_surfaces:
        return {'score': 5.0, 'color': 'yellow', 'emoji': '🟡', 'quality': 'Orta', 'description': 'Yol verisi bulunamadı'}
    
    # Her surface'ın puanını al
    scores = []
    for surface in route_surfaces:
        surface_str = str(surface).lower() if surface else 'unknown'
        score = quality_map.get(surface_str, 7)  # Bilinmeyen = 5
        scores.append(score)
    
    # Ağırlıklı ortalama (ilk kenarlar daha önemli)
    weights = [1.0 / (i + 1) for i in range(len(scores))]
    total_weight = sum(weights)
    weighted_score = sum(s * w for s, w in zip(scores, weights)) / total_weight
    
    # 1-10 arasında normal et
    final_score = max(1, min(10, weighted_score))
    
    # Renk ve açıklama
    if final_score >= 8:
        return {
            'score': round(final_score, 1),
            'color': 'green',
            'emoji': '🟢',
            'quality': 'İyi',
            'description': 'Yüksek kaliteli yol'
        }
    elif final_score >= 5:
        return {
            'score': round(final_score, 1),
            'color': 'yellow',
            'emoji': '🟡',
            'quality': 'Orta',
            'description': 'Karışık yol koşulları'
        }
    else:
        return {
            'score': round(final_score, 1),
            'color': 'red',
            'emoji': '🔴',
            'quality': 'Kötü',
            'description': 'Düşük kaliteli yol'
        }


def calculate_damage_risk(route_surfaces: list, modifications: list) -> dict:
    """
    Modifiye araçlar için yol hasarı riski hesapla
    
    Args:
        route_surfaces: Rota yüzeyleri
        modifications: Araç modifikasyonları
    
    Returns:
        {'risk_level': 0-100, 'count_bad_surfaces': int, 'is_risky': bool}
    """
    
    # Hasara açık yüzeyler
    risky_surfaces = ['cobblestone', 'unpaved', 'gravel', 'mud', 'dirt']
    
    if not route_surfaces:
        return {
            'risk_level': 0,
            'count_bad_surfaces': 0,
            'is_risky': False,
            'emoji': '🟢',
            'description': 'Güvenli'
        }
    
    bad_count = sum(1 for s in route_surfaces if str(s).lower() in risky_surfaces)
    
    # Modifikasyon etkisi
    risk_multiplier = 1.0
    if 'lowering' in modifications:
        risk_multiplier *= 2.0  # Lowering çok riskli
    if 'lift' in modifications:
        risk_multiplier *= 0.6  # Lift iyileştirir
    if 'offset' in modifications:
        risk_multiplier *= 1.3  # Geniş lastik daha hassas
    
    # Risk seviyesi (0-100)
    total_surfaces = len(route_surfaces)
    base_risk = (bad_count / total_surfaces * 100) if total_surfaces > 0 else 0
    final_risk = min(100, base_risk * risk_multiplier)
    
    return {
        'risk_level': round(final_risk, 1),
        'count_bad_surfaces': bad_count,
        'total_surfaces': total_surfaces,
        'is_risky': final_risk > 30,
        'emoji': '🟢' if final_risk <= 20 else ('🟡' if final_risk <= 50 else '🔴'),
        'description': 'Güvenli' if final_risk <= 20 else ('Uyarı' if final_risk <= 50 else 'Riskli Rota')
    }


def calculate_cost_estimate(distance_km: float, route_surfaces: list, modifications: list, vehicle_type: str) -> dict:
    """
    Yakıt ve bakım maliyeti tahmini
    
    Args:
        distance_km: Rota uzunluğu (km)
        route_surfaces: Rota yüzeyleri
        modifications: Araç modifikasyonları
        vehicle_type: Araç tipi (binek, kamyon, vb.)
    
    Returns:
        {'fuel_cost': float, 'maintenance_cost': float, 'total_cost': float}
    """
    
    # Temel yakıt tüketimi (L/100km) — gerçek araçlara göre (şehir içi ortalama)
    # Binek: Corolla/Megane/Egea şehir içi ~8-9 L
    # Kamyon: MAN TGS / Mercedes Actros ortalama ~32 L
    # Motosiklet: CB500/MT-07 ~5 L
    # Modifiye (SUV/Arazi): RAV4/Land Cruiser/Duster şehir içi ~11 L
    base_consumption = {
        'binek': 8.5,
        'kamyon': 32.0,
        'motosiklet': 5.0,
        'bisiklet': 0.0,
        'modifiye': 11.0,
    }

    consumption = base_consumption.get(vehicle_type, 8.5)

    # Yüzey kalitesi cezası
    quality_score = calculate_road_quality_score(route_surfaces)['score']
    quality_penalty = (11 - quality_score) / 10  # 1.0 - 2.0

    # Modifikasyon cezası
    penalties = calculate_profile_penalty(modifications)
    fuel_multiplier = penalties['fuel_efficiency']

    # Toplam yakıt tüketimi
    total_consumption = (distance_km / 100) * consumption * quality_penalty * fuel_multiplier

    # Yakıt maliyeti (Türkiye Nisan 2026 fiyatları, TL/L)
    # Benzin 95: ~53 TL/L · Dizel: ~49 TL/L
    fuel_prices = {
        'binek':      53.0,   # Benzin 95
        'kamyon':     49.0,   # Dizel
        'motosiklet': 53.0,   # Benzin 95
        'bisiklet':    0.0,
        'modifiye':   53.0,   # Benzin 95 (SUV/Arazi)
    }

    fuel_price = fuel_prices.get(vehicle_type, 53.0)
    fuel_cost = total_consumption * fuel_price
    
    # Bakım maliyeti (kötü yollarda daha fazla)
    bad_surface_ratio = (
        sum(1 for s in route_surfaces if str(s).lower() in ['cobblestone', 'unpaved', 'gravel', 'mud', 'dirt'])
        / len(route_surfaces)
        if route_surfaces
        else 0
    )
    
    # Km başına temel bakım (TL) — Nisan 2026 Türkiye fiyatları
    # Binek lastik+yağ+fren ortalama ~3.5 TL/km, kamyon ~12 TL/km
    base_maintenance = {
        'binek':      3.5,
        'kamyon':    12.0,
        'motosiklet': 2.0,
        'bisiklet':   0.15,
        'modifiye':   5.0,
    }
    
    maintenance_base = base_maintenance.get(vehicle_type, 0.15)
    maintenance_penalty = 1.0 + (bad_surface_ratio * 2.0)  # Kötü yol = 3x bakım
    
    maintenance_cost = distance_km * maintenance_base * maintenance_penalty
    
    # Modifikasyon bakımı ek maliyeti
    if 'lowering' in modifications:
        maintenance_cost *= 1.3  # Lowering çok bakım istiyor
    if 'lift' in modifications:
        maintenance_cost *= 1.2
    
    total_cost = fuel_cost + maintenance_cost
    
    return {
        'fuel_consumption_liters': round(total_consumption, 2),
        'fuel_cost_tl': round(fuel_cost, 2),
        'maintenance_cost_tl': round(maintenance_cost, 2),
        'total_cost_tl': round(total_cost, 2),
        'cost_per_km': round(total_cost / distance_km, 4) if distance_km > 0 else 0,
        'description': f"{round(total_consumption, 1)}L yakıt, {round(total_cost, 0)} TL tahmini maliyet"
    }


# ── Karbon Emisyonu ──────────────────────────────────────────────────────────

# g CO₂ / km — WLTP kombine değerleri (Türkiye ortalama parkı, 2024)
_CO2_G_KM = {
    'binek':      130,   # Ortalama benzinli binek
    'modifiye':   185,   # SUV / arazi / pickup
    'kamyon':     620,   # Ağır vasıta (yüklü)
    'motosiklet':  95,   # Motosiklet (400–750 cc)
    'bisiklet':     0,   # İnsan/elektrik gücü
}

_CO2_GRADES = [
    (0,   'A+', '#1b5e20'),
    (100, 'A',  '#2e7d32'),
    (140, 'B',  '#558b2f'),
    (180, 'C',  '#f57f17'),
    (250, 'D',  '#e65100'),
    (999, 'E',  '#b71c1c'),
]


def calculate_carbon_emission(distance_km: float, vehicle_type: str) -> dict:
    """
    CO₂ emisyonu ve emisyon notu hesapla.

    Returns:
        co2_per_km_g, total_co2_kg, grade, grade_color, context
    """
    base = _CO2_G_KM.get(vehicle_type, 130)
    total_g  = base * distance_km
    total_kg = total_g / 1000

    grade, grade_color = 'D', '#e65100'
    for threshold, g, c in _CO2_GRADES:
        if base <= threshold:
            grade, grade_color = g, c
            break

    if total_kg < 0.05:
        context = "🌱 Neredeyse sıfır emisyon"
    elif total_kg < 0.3:
        context = f"🌿 {total_kg*1000:.0f} g — çok düşük"
    elif total_kg < 1:
        context = f"☕ {total_kg/0.21:.0f} bardak kahve üretimine eşdeğer"
    elif total_kg < 5:
        context = f"🌳 {total_kg / 0.060:.0f} ağacın 1 günlük CO₂ emilimi"
    else:
        context = f"✈️ {total_kg / 255:.2f} km uçuşa eşdeğer (kişi başı)"

    return {
        'co2_per_km_g': base,
        'total_co2_g':  round(total_g),
        'total_co2_kg': round(total_kg, 3),
        'grade':        grade,
        'grade_color':  grade_color,
        'context':      context,
    }
