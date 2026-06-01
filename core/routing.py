"""
Akıllı navigasyon rotası planlama motoru
Ağırlıklı Dijkstra algoritması + araç profilleri
"""

from typing import List, Tuple, Dict, Optional
from collections import defaultdict
import heapq
import math  # bearing hesapları için

import networkx as nx
import osmnx as ox
from shapely.geometry import Point

from profiles.vehicle_profiles import (
    get_vehicle_profile,
    get_highway_cost,
    get_surface_cost,
    get_traffic_factor,
)

# (off_peak_kmh, rush_hour_kmh) — araç türü: binek için taban değerler
HIGHWAY_SPEEDS: Dict[str, tuple] = {
    'motorway':       (115, 85),
    'motorway_link':  (90,  65),
    'trunk':          (90,  70),
    'trunk_link':     (75,  55),
    'primary':        (70,  50),
    'primary_link':   (60,  45),
    'secondary':      (60,  45),
    'secondary_link': (50,  38),
    'tertiary':       (50,  35),
    'tertiary_link':  (45,  30),
    'residential':    (40,  30),
    'living_street':  (20,  15),
    'unclassified':   (45,  35),
    'service':        (25,  20),
    'track':          (25,  20),
}

# Araç tipi hız çarpanları (binek=1.0 baz)
VEHICLE_SPEED_FACTORS: Dict[str, float] = {
    'binek':      1.00,
    'kamyon':     0.72,   # Ağır araç, otobanda 90 sınırı
    'motosiklet': 1.08,   # Şehirde daha akıcı filtre yapabilir
    'bisiklet':   0.22,   # Sabit ~15-18 km/h
    'modifiye':   0.90,   # SUV/arazi daha ağır
}


class SmartRouter:
    """Akıllı navigasyon motoru"""
    
    def __init__(self, graph: nx.MultiDiGraph, vehicle_type: str = 'binek', hour: int = 12):
        """
        Router başlatma
        
        Args:
            graph: OSMnx ağı (MultiDiGraph)
            vehicle_type: Araç tipi ('binek', 'kamyon', 'motosiklet', 'bisiklet', 'modifiye')
            hour: Saat (0-23) - trafik hesaplamalarında kullanılır
        """
        self.graph = graph
        self.vehicle_type = vehicle_type
        self.hour = hour

        # Profil ve trafik çarpanını önceden yükle
        self.profile = get_vehicle_profile(vehicle_type)
        self.traffic_factor = get_traffic_factor(vehicle_type, hour)

        # Yoğun saatler: hafta içi 07:00-09:00 ve 17:00-19:30
        self.is_rush_hour = (7 <= hour <= 9) or (17 <= hour <= 19)
    
    def calculate_edge_weight(self, u: int, v: int, key: int = 0) -> float:
        """
        Kenar ağırlığını hesapla (maliyet = mesafe × yüzey cezası × trafik × highway cezası)
        
        Args:
            u, v: Düğüm ID'leri
            key: Kenar anahtarı (MultiDiGraph için)
        
        Returns:
            Kenar ağırlığı (metre)
        """
        try:
            edge_data = self.graph.edges[u, v, key]
            
            # Temel maliyet: mesafe (metre)
            distance = edge_data.get('length', 50)  # 50m varsayılan
            
            # Highway tipi cezası
            highway = edge_data.get('highway', 'unclassified')
            if isinstance(highway, list):
                highway = highway[0]
            highway_cost = get_highway_cost(self.vehicle_type, highway)
            
            # Surface tipi cezası (varsa)
            surface = edge_data.get('surface', None)
            if surface:
                surface_cost = get_surface_cost(self.vehicle_type, surface)
            else:
                surface_cost = 1.0
            
            # Toplam ağırlık = mesafe × highway cezası × surface cezası × trafik çarpanı
            weight = distance * highway_cost * surface_cost * self.traffic_factor
            
            return weight
            
        except (KeyError, TypeError):
            # Kenar yoksa veya veri eksik ise yüksek maliyet
            return float('inf')
    
    def find_nearest_node(self, lat: float, lon: float) -> int:
        """
        Belirtilen koordinata en yakın ağ düğümünü bul
        
        Args:
            lat: Enlem
            lon: Boylam
        
        Returns:
            Düğüm ID'si
        """
        # OSMnx'in nearest_nodes fonksiyonunu kullan
        nearest = ox.nearest_nodes(self.graph, lon, lat)
        return nearest
    
    def dijkstra_route(self, start_node: int, end_node: int) -> Tuple[List[int], float]:
        """
        Ağırlıklı Dijkstra algoritması ile optimal rota bul
        
        Args:
            start_node: Başlangıç düğümü ID
            end_node: Hedef düğümü ID
        
        Returns:
            (Rota düğüm listesi, Toplam maliyet) tuple'ı
        """
        if start_node not in self.graph or end_node not in self.graph:
            raise ValueError(f"Düğüm ağda bulunamadı")
        
        # Dijkstra algoritması
        distances = {node: float('inf') for node in self.graph.nodes()}
        distances[start_node] = 0
        
        previous = {node: None for node in self.graph.nodes()}
        
        # Priority queue: (distance, node)
        pq = [(0, start_node)]
        visited = set()
        
        while pq:
            current_dist, current = heapq.heappop(pq)
            
            if current in visited:
                continue
            
            visited.add(current)
            
            # Hedefe ulaştık
            if current == end_node:
                break
            
            # Komşu düğümleri kontrol et
            for neighbor in self.graph.successors(current):
                if neighbor in visited:
                    continue
                
                # En düşük ağırlıklı kenarı al (MultiDiGraph için)
                min_weight = float('inf')
                for key in self.graph[current][neighbor]:
                    weight = self.calculate_edge_weight(current, neighbor, key)
                    min_weight = min(min_weight, weight)
                
                new_dist = current_dist + min_weight
                
                if new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    previous[neighbor] = current
                    heapq.heappush(pq, (new_dist, neighbor))
        
        # Rota oluştur
        if previous[end_node] is None and start_node != end_node:
            raise ValueError("Başlangıç ve hedef arasında rota bulunamadı")
        
        route = []
        current = end_node
        while current is not None:
            route.append(current)
            current = previous[current]
        
        route.reverse()
        total_cost = distances[end_node]
        
        return route, total_cost
    
    def find_route(self, start_lat: float, start_lon: float, 
                   end_lat: float, end_lon: float) -> Dict:
        """
        Başlangıç ve bitiş koordinatlarından optimal rota bul
        
        Args:
            start_lat, start_lon: Başlangıç koordinatları
            end_lat, end_lon: Hedef koordinatları
        
        Returns:
            Rota bilgileri içeren sözlük
        """
        # En yakın ağ düğümlerini bul
        start_node = ox.nearest_nodes(self.graph, start_lon, start_lat)
        end_node = ox.nearest_nodes(self.graph, end_lon, end_lat)

        # OSMnx ile güvenilir yol-takipli rota bul
        route_nodes = ox.shortest_path(self.graph, start_node, end_node, weight='length')
        if route_nodes is None:
            raise ValueError("Başlangıç ve hedef arasında rota bulunamadı")

        # Araç profili ağırlıklı toplam maliyet hesapla
        total_cost = 0.0
        for u, v in zip(route_nodes[:-1], route_nodes[1:]):
            if v in self.graph[u]:
                min_w = min(
                    self.calculate_edge_weight(u, v, k)
                    for k in self.graph[u][v]
                )
                if min_w != float('inf'):
                    total_cost += min_w

        # Koordinatlar: her kenarın gerçek yol geometrisini kullan
        # OSMnx simplify=True ile sadeleştirilmiş grafta, kavşaklar arası
        # tüm ara noktalar edge'in 'geometry' (Shapely LineString) attribute'unda saklanır.
        # Sadece node koordinatlarını kullanırsak PolyLine yolun dışından geçer.
        route_coords = self._extract_route_geometry(route_nodes)
        
        # Yol yüzeyleri (surface) bilgisini çıkar
        route_surfaces = self._extract_route_surfaces(route_nodes)
        
        # Toplam mesafe (metre cinsinden maliyet hesaplamak için)
        total_distance = self._calculate_route_distance(route_nodes)
        
        # Tahmini seyahat süresi — yol tipine ve saate göre gerçekçi hesaplama
        estimated_time_minutes = self._calculate_route_time(route_nodes)
        
        return {
            'nodes': route_nodes,
            'coordinates': route_coords,
            'start_point': (start_lat, start_lon),
            'end_point': (end_lat, end_lon),
            'total_distance_m': total_distance,
            'total_cost': total_cost,
            'estimated_time_minutes': estimated_time_minutes,
            'vehicle_type': self.vehicle_type,
            'hour': self.hour,
            'traffic_factor': self.traffic_factor,
            'surfaces': route_surfaces,  # Yol yüzeyleri
        }
    
    def _calculate_route_distance(self, route_nodes: List[int]) -> float:
        """Rota üzerindeki gerçek mesafeyi hesapla (metre cinsinden)"""
        total_distance = 0.0
        
        for i in range(len(route_nodes) - 1):
            u, v = route_nodes[i], route_nodes[i + 1]
            
            # En kısa kenarı al (MultiDiGraph için)
            min_distance = float('inf')
            for key in self.graph[u][v]:
                distance = self.graph.edges[u, v, key].get('length', 50)
                min_distance = min(min_distance, distance)
            
            if min_distance != float('inf'):
                total_distance += min_distance
        
        return total_distance
    
    def _extract_route_surfaces(self, route_nodes: List[int]) -> List[str]:
        """
        Rota kenarlarından yol yüzey türlerini çıkar
        
        Args:
            route_nodes: Rota düğümleri listesi
        
        Returns:
            Yüzey türleri listesi
        """
        surfaces = []
        
        for i in range(len(route_nodes) - 1):
            u, v = route_nodes[i], route_nodes[i + 1]
            
            # En kısa kenarı al
            best_surface = 'asphalt'  # Varsayılan
            min_distance = float('inf')
            
            for key in self.graph[u][v]:
                edge_data = self.graph.edges[u, v, key]
                distance = edge_data.get('length', 50)
                
                if distance < min_distance:
                    min_distance = distance
                    best_surface = edge_data.get('surface', 'asphalt')
            
            surfaces.append(best_surface)
        
        return surfaces
    
    def _extract_route_geometry(self, route_nodes: List[int]) -> List[Tuple[float, float]]:
        """
        Rota kenarlarının gerçek yol geometrisini çıkar.

        OSMnx simplify=True ile sadeleştirilmiş grafta, iki kavşak arasındaki
        tüm ara noktalar kenarın 'geometry' (Shapely LineString) attribute'unda
        saklanır.  Sadece node koordinatı kullanmak PolyLine'ı yoldan çıkarır.

        Returns:
            (lat, lon) tuple listesi — tüm ara noktalar dahil
        """
        coords: List[Tuple[float, float]] = []

        for i in range(len(route_nodes) - 1):
            u, v = route_nodes[i], route_nodes[i + 1]

            # MultiDiGraph: en kısa kenarlı key'i bul
            best_key = min(
                self.graph[u][v],
                key=lambda k: self.graph[u][v][k].get('length', float('inf'))
            )
            edge_data = self.graph.edges[u, v, best_key]

            if 'geometry' in edge_data:
                # Shapely LineString — coords: [(lon, lat), ...]
                geom_coords = list(edge_data['geometry'].coords)
                # İlk nokta önceki segmentin son noktasıyla çakışır; atlıyoruz
                for lon, lat in geom_coords[:-1]:
                    coords.append((lat, lon))
            else:
                # Geometry yoksa düğüm koordinatını ekle
                node_data = self.graph.nodes[u]
                coords.append((node_data['y'], node_data['x']))

        # Son düğümü ekle
        last = self.graph.nodes[route_nodes[-1]]
        coords.append((last['y'], last['x']))

        return coords

    def _calculate_route_time(self, route_nodes: List[int]) -> float:
        """
        Rota seyahat süresini dakika cinsinden hesapla.
        Her kenar için yol tipine ve saate göre gerçekçi hız kullanır.
        """
        total_seconds = 0.0
        factor = VEHICLE_SPEED_FACTORS.get(self.vehicle_type, 1.0)

        for u, v in zip(route_nodes[:-1], route_nodes[1:]):
            if v not in self.graph[u]:
                continue
            best_key = min(self.graph[u][v],
                           key=lambda k: self.graph[u][v][k].get('length', float('inf')))
            edge_data = self.graph.edges[u, v, best_key]
            length_m = edge_data.get('length', 50)

            highway = edge_data.get('highway', 'unclassified')
            if isinstance(highway, list):
                highway = highway[0]

            speeds = HIGHWAY_SPEEDS.get(highway, (45, 35))
            speed_kmh = (speeds[1] if self.is_rush_hour else speeds[0]) * factor
            speed_kmh = max(speed_kmh, 5.0)  # minimum 5 km/h

            # Kamyon için otoban hız sınırı: 90 km/h
            if self.vehicle_type == 'kamyon' and highway in ('motorway', 'trunk'):
                speed_kmh = min(speed_kmh, 90.0)

            # Bisiklet için sabit hız
            if self.vehicle_type == 'bisiklet':
                speed_kmh = 16.0

            total_seconds += (length_m / 1000) / speed_kmh * 3600

        return total_seconds / 60  # dakika
    
    # Yol konfor faktörleri — "En Kolay" stratejisi için
    _ROAD_EASE: Dict[str, float] = {
        'motorway': 0.40,      'motorway_link': 0.50,
        'trunk':    0.50,      'trunk_link':    0.60,
        'primary':  0.70,      'primary_link':  0.75,
        'secondary':0.90,      'secondary_link':0.95,
        'tertiary': 1.20,      'tertiary_link': 1.30,
        'residential': 2.00,   'living_street': 3.00,
        'service':  2.50,      'track':         3.00,
        'unclassified': 1.40,
    }

    def _edge_weight_by_strategy(self, u: int, v: int, k: int,
                                  strategy: str) -> float:
        """Stratejiye göre tek kenar ağırlığı döndür."""
        try:
            data    = self.graph.edges[u, v, k]
            length  = data.get('length', 50)
            highway = data.get('highway', 'unclassified')
            if isinstance(highway, list):
                highway = highway[0]

            if strategy == 'ekonomik':
                return length                                      # salt mesafe

            if strategy == 'hizli':
                speeds     = HIGHWAY_SPEEDS.get(highway, (45, 35))
                speed_kmh  = (speeds[1] if self.is_rush_hour else speeds[0])
                speed_kmh *= VEHICLE_SPEED_FACTORS.get(self.vehicle_type, 1.0)
                speed_kmh  = max(speed_kmh, 5.0)
                return (length / 1000) / speed_kmh * 3600         # saniye

            # kolay: büyük yolları tercih et
            return length * self._ROAD_EASE.get(highway, 1.30)

        except (KeyError, TypeError):
            return float('inf')

    def _dijkstra_by_strategy(self, start_node: int, end_node: int,
                               strategy: str) -> Optional[List[int]]:
        """Strateji ağırlıklı özel Dijkstra — grafiği değiştirmez."""
        dist: Dict[int, float] = {}
        dist[start_node] = 0.0
        prev: Dict[int, Optional[int]] = {start_node: None}
        pq: list = [(0.0, start_node)]
        visited: set = set()

        while pq:
            cur_d, cur = heapq.heappop(pq)
            if cur in visited:
                continue
            visited.add(cur)
            if cur == end_node:
                break
            for nbr in self.graph.successors(cur):
                if nbr in visited:
                    continue
                w = min(
                    self._edge_weight_by_strategy(cur, nbr, k, strategy)
                    for k in self.graph[cur][nbr]
                )
                nd = cur_d + w
                if nd < dist.get(nbr, float('inf')):
                    dist[nbr] = nd
                    prev[nbr] = cur
                    heapq.heappush(pq, (nd, nbr))

        if end_node not in prev:
            return None
        path: List[int] = []
        node: Optional[int] = end_node
        while node is not None:
            path.append(node)
            node = prev.get(node)
        path.reverse()
        return path

    def find_alternative_routes(
        self,
        start_lat: float, start_lon: float,
        end_lat: float,   end_lon: float,
        n_routes: int = 3,          # parametre korunuyor (geriye dönük uyum)
    ) -> List[Dict]:
        """
        3 farklı optimizasyon stratejisi ile rota hesaplar:
          ⚡ En Hızlı  — seyahat süresi minimizasyonu (trafik dahil)
          🛣️ En Kolay  — büyük/rahat yolları tercih (konforlu sürüş)
          💰 En Ekonomik — salt mesafe minimizasyonu (yakıt tasarrufu)
        """
        STRATEGIES = [
            ('hizli',    '⚡ En Hızlı',    '#2E7D32'),
            ('kolay',    '🛣️ En Kolay',    '#1565C0'),
            ('ekonomik', '💰 En Ekonomik', '#E65100'),
        ]

        start_node = ox.nearest_nodes(self.graph, start_lon, start_lat)
        end_node   = ox.nearest_nodes(self.graph, end_lon,   end_lat)

        routes: List[Dict] = []

        for strategy, label, color in STRATEGIES:
            try:
                nodes = self._dijkstra_by_strategy(start_node, end_node, strategy)
                if not nodes:
                    continue

                coords   = self._extract_route_geometry(nodes)
                surfaces = self._extract_route_surfaces(nodes)
                distance = self._calculate_route_distance(nodes)
                time_min = self._calculate_route_time(nodes)
                cost     = sum(
                    min(self.calculate_edge_weight(u, v, k) for k in self.graph[u][v])
                    for u, v in zip(nodes[:-1], nodes[1:])
                    if v in self.graph[u]
                )

                routes.append({
                    'nodes':                nodes,
                    'coordinates':          coords,
                    'start_point':          (start_lat, start_lon),
                    'end_point':            (end_lat,   end_lon),
                    'total_distance_m':     distance,
                    'total_cost':           cost,
                    'estimated_time_minutes': time_min,
                    'vehicle_type':         self.vehicle_type,
                    'hour':                 self.hour,
                    'traffic_factor':       self.traffic_factor,
                    'surfaces':             surfaces,
                    'route_label':          label,
                    'route_color':          color,
                    'route_strategy':       strategy,
                    'route_idx':            len(routes),
                })
            except Exception:
                pass

        # Hiç rota bulunamadıysa tek rota döndür
        if not routes:
            r = self.find_route(start_lat, start_lon, end_lat, end_lon)
            r['route_label'] = '⚡ En Hızlı'
            r['route_color'] = '#2E7D32'
            r['route_idx']   = 0
            routes.append(r)

        return routes

    def _edge_bearing(self, u: int, v: int) -> float:
        """İki kavşak düğümü arasındaki coğrafi yönü hesapla (0–360°)."""
        n1 = self.graph.nodes[u]
        n2 = self.graph.nodes[v]
        lat1 = math.radians(n1['y']);  lon1 = math.radians(n1['x'])
        lat2 = math.radians(n2['y']);  lon2 = math.radians(n2['x'])
        dlon = lon2 - lon1
        x = math.sin(dlon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        return (math.degrees(math.atan2(x, y)) + 360) % 360

    def generate_turn_instructions(self, route_nodes: List[int]) -> List[Dict]:
        """
        Kavşak düğümleri arasındaki bearing farkından adım adım yön talimatları üretir.
        Ardışık talimatlar birleştirilir (ör. 3 × 'Düz devam et' → tek satır).
        """
        if len(route_nodes) < 3:
            return []

        _TURN = [
            (-180, -90,  '↰', 'Keskin sola dön'),
            ( -90, -25,  '↖', 'Sola dön'),
            ( -25,  25,  '↑', 'Düz devam et'),
            (  25,  90,  '↗', 'Sağa dön'),
            (  90, 180,  '↱', 'Keskin sağa dön'),
        ]

        raw: List[Dict] = []
        for i in range(1, len(route_nodes) - 1):
            u, v, w = route_nodes[i - 1], route_nodes[i], route_nodes[i + 1]

            in_b  = self._edge_bearing(u, v)
            out_b = self._edge_bearing(v, w)
            diff  = (out_b - in_b + 360) % 360
            if diff > 180:
                diff -= 360  # negatif = sol

            icon, text = '↑', 'Düz devam et'
            for lo, hi, ic, tx in _TURN:
                if lo <= diff < hi:
                    icon, text = ic, tx
                    break

            # Gelen kenarın uzunluğu
            best_k   = min(self.graph[u][v],
                           key=lambda k: self.graph[u][v][k].get('length', 9999))
            seg_m    = self.graph.edges[u, v, best_k].get('length', 0)

            # Sonraki yolun adı — boşsa OSM ref ile fallback (E-5, D-100 vb.)
            best_k2  = min(self.graph[v][w],
                           key=lambda k: self.graph[v][w][k].get('length', 9999))
            _edata   = self.graph.edges[v, w, best_k2]
            road     = _edata.get('name', '')
            if isinstance(road, list):
                road = road[0] if road else ''
            if not road:
                _ref = _edata.get('ref', '')
                if isinstance(_ref, list):
                    _ref = _ref[0] if _ref else ''
                road = _ref

            raw.append({'icon': icon, 'text': text,
                        'road': road, 'distance_m': seg_m})

        # Ardışık "Düz devam et" talimatlarını birleştir
        merged: List[Dict] = []
        for step in raw:
            if (merged and step['text'] == merged[-1]['text'] == 'Düz devam et'):
                merged[-1]['distance_m'] += step['distance_m']
                if step['road'] and not merged[-1]['road']:
                    merged[-1]['road'] = step['road']
            else:
                merged.append(dict(step))

        return merged

    def set_vehicle_type(self, vehicle_type: str) -> None:
        """Araç tipini değiştir"""
        self.vehicle_type = vehicle_type
        self.profile = get_vehicle_profile(vehicle_type)
    
    def set_hour(self, hour: int) -> None:
        """Saati değiştir (trafik çarpanı güncelleme için)"""
        if not 0 <= hour <= 23:
            raise ValueError("Saat 0-23 aralığında olmalı")
        self.hour = hour
        self.traffic_factor = get_traffic_factor(self.vehicle_type, hour)
        self.is_rush_hour = (7 <= hour <= 9) or (17 <= hour <= 19)


class AlternativeRoutes:
    """Alternatif rotalar bulma (Yen's algoritması)"""
    
    def __init__(self, router: SmartRouter):
        """
        AlternativeRoutes başlatma
        
        Args:
            router: SmartRouter örneği
        """
        self.router = router
        self.graph = router.graph
    
    def find_k_shortest_paths(self, start_node: int, end_node: int, 
                              k: int = 3) -> List[Dict]:
        """
        En kısa k rotayı bul (Yen's algoritması)
        
        Args:
            start_node: Başlangıç düğümü
            end_node: Hedef düğümü
            k: Kaç adet rota bulunacağı
        
        Returns:
            Rota listesi (her biri maliyet bilgisi ile)
        """
        routes = []
        
        # Ilk (en kısa) rotayı bul
        try:
            route, cost = self.router.dijkstra_route(start_node, end_node)
            routes.append({
                'route': route,
                'cost': cost,
                'distance': self.router._calculate_route_distance(route),
                'rank': 1,
            })
        except ValueError:
            return []
        
        # Ek rotalar bulmak için basit yaklaşım: 
        # Bulunan rotanın kenarlarını geçici olarak kaldır
        for i in range(1, k):
            if not routes:
                break
            
            # Son bulunan rotanın bir kenarını kaldır
            last_route = routes[-1]['route']
            try:
                idx = i - 1
                if idx < len(last_route) - 1:
                    u, v = last_route[idx], last_route[idx + 1]
                    
                    # Geçici olarak kenarı kaldır
                    removed_edges = []
                    for key in list(self.graph[u][v].keys()):
                        removed_edges.append((u, v, key, self.graph[u][v][key]))
                        self.graph.remove_edge(u, v, key)
                    
                    # Yeni rota bul
                    try:
                        route, cost = self.router.dijkstra_route(start_node, end_node)
                        routes.append({
                            'route': route,
                            'cost': cost,
                            'distance': self.router._calculate_route_distance(route),
                            'rank': i + 1,
                        })
                    except ValueError:
                        pass
                    finally:
                        # Kenarları geri ekle
                        for u, v, key, data in removed_edges:
                            self.graph.add_edge(u, v, key=key, **data)
            except Exception:
                break
        
        return routes[:k]

