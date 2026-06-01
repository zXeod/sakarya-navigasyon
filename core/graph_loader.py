"""
OSMnx kullanarak Sakarya ili yol ağını indirme ve cache'leme
"""

import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import Optional

import osmnx as ox
import networkx as nx


# Klasör tanımları
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CACHE_FILE = DATA_DIR / "sakarya_graph.pkl"
METADATA_FILE = DATA_DIR / "graph_metadata.txt"

# Sakarya ili coğrafi sınırları
SAKARYA_PLACE = "Sakarya, Turkey"


def ensure_data_dir():
    """data/ klasörünün varlığını sağla"""
    DATA_DIR.mkdir(exist_ok=True)


def download_sakarya_graph(use_cache: bool = True) -> nx.MultiDiGraph:
    """
    OSMnx kullanarak Sakarya yol ağını indir
    
    Args:
        use_cache: Cache dosyası vardıysa kullan
    
    Returns:
        NetworkX MultiDiGraph nesnesi
    """
    ensure_data_dir()
    
    # Cache kontrolü
    if use_cache and CACHE_FILE.exists():
        print(f"[OK] Cache dosyası bulundu: {CACHE_FILE}")
        return load_graph_from_file()
    
    print("Sakarya il yol agi indiriliyor (bu islem 2-5 dakika alabilir)...")

    try:
        # Sakarya ili idari sınırları içindeki tüm sürüş yollarını indir
        graph = ox.graph_from_place(
            SAKARYA_PLACE,
            network_type='drive',
            simplify=True,
            retain_all=False,
            truncate_by_edge=True,
        )

        print(f"[OK] Graph indirildi: {len(graph.nodes)} düğüm, {len(graph.edges)} kenar")
        
        # Cache'e kaydet
        save_graph_to_file(graph)
        print(f"[OK] Cache kaydedildi: {CACHE_FILE}")
        
        return graph
        
    except Exception as e:
        print(f"[HATA] Graph indirme hatası: {e}")
        raise


def save_graph_to_file(graph: nx.MultiDiGraph) -> None:
    """
    Graf nesnesini pickle dosyasına kaydet
    
    Args:
        graph: Kaydedilecek NetworkX grafiği
    """
    ensure_data_dir()
    
    with open(CACHE_FILE, 'wb') as f:
        pickle.dump(graph, f, protocol=pickle.HIGHEST_PROTOCOL)
    
    # Metadata kaydı
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        f.write(f"Sakarya Yol Ağı Bilgisi\n")
        f.write(f"{'='*50}\n")
        f.write(f"Kapsam: {SAKARYA_PLACE} (il sınırları)\n")
        f.write(f"Düğüm Sayısı: {len(graph.nodes)}\n")
        f.write(f"Kenar Sayısı: {len(graph.edges)}\n")
        f.write(f"İndir Tarihi: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


def load_graph_from_file() -> nx.MultiDiGraph:
    """
    Kaydedilmiş graph nesnesini yükle
    
    Returns:
        NetworkX MultiDiGraph nesnesi
    
    Raises:
        FileNotFoundError: Cache dosyası yoksa
    """
    if not CACHE_FILE.exists():
        raise FileNotFoundError(
            f"Cache dosyası bulunamadı: {CACHE_FILE}\n"
            "Lütfen önce download_sakarya_graph() çağırın."
        )
    
    with open(CACHE_FILE, 'rb') as f:
        graph = pickle.load(f)
    
    return graph


def get_graph_cached() -> nx.MultiDiGraph:
    """
    Cache'lenmiş graph'ı al, yoksa indir ve cache'le
    
    Returns:
        NetworkX MultiDiGraph nesnesi
    """
    try:
        return load_graph_from_file()
    except FileNotFoundError:
        return download_sakarya_graph(use_cache=False)


def clear_cache() -> None:
    """Cache dosyalarını sil"""
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()
        print(f"[OK] Cache silindi: {CACHE_FILE}")
    
    if METADATA_FILE.exists():
        METADATA_FILE.unlink()
        print(f"[OK] Metadata silindi: {METADATA_FILE}")


def get_graph_info(graph: Optional[nx.MultiDiGraph] = None) -> dict:
    """
    Graf hakkında bilgi döndür

    Args:
        graph: Bilgi alınacak graf (None ise cache'ten yükle)

    Returns:
        Graf bilgileri içeren sözlük
    """
    if graph is None:
        graph = get_graph_cached()

    # Tek geçişte highway ve surface tiplerini say
    highway_types: dict = {}
    surface_types: dict = {}
    for _u, _v, data in graph.edges(data=True):
        hw = data.get('highway', 'unknown')
        if isinstance(hw, list):
            hw = hw[0]
        highway_types[hw] = highway_types.get(hw, 0) + 1

        sf = data.get('surface', 'unknown')
        surface_types[sf] = surface_types.get(sf, 0) + 1

    # Metadata dosyasından indirme/güncelleme tarihini oku
    cache_date: Optional[str] = None
    if METADATA_FILE.exists():
        try:
            for _line in METADATA_FILE.read_text(encoding='utf-8').splitlines():
                if _line.startswith('İndir Tarihi:'):
                    cache_date = _line.split(':', 1)[1].strip()
                    break
        except Exception:
            pass

    return {
        'nodes': len(graph.nodes),
        'edges': len(graph.edges),
        # nx.is_strongly_connected is O(V+E) and too slow for the UI expander;
        # use weakly-connected component count instead (much faster).
        'is_connected': nx.number_weakly_connected_components(graph) == 1,
        'top_highways': sorted(highway_types.items(), key=lambda x: x[1], reverse=True)[:5],
        'top_surfaces': sorted(surface_types.items(), key=lambda x: x[1], reverse=True)[:5],
        'cache_exists': CACHE_FILE.exists(),
        'cache_size_mb': CACHE_FILE.stat().st_size / (1024 * 1024) if CACHE_FILE.exists() else 0,
        'cache_date': cache_date,
    }


def export_graph_geojson(output_path: str = "sakarya_graph.geojson") -> None:
    """
    Graph'ı GeoJSON formatında dış veya et (Folium haritalar için)
    
    Args:
        output_path: Çıktı dosyası yolu
    """
    graph = get_graph_cached()
    
    print(f"[...] GeoJSON dosyası oluşturuluyor...")
    
    # GeoJSON formatına dönüştür (ox.graph_to_gdfs kullanarak)
    nodes_gdf, edges_gdf = ox.graph_to_gdfs(graph)
    
    # Kenarları dışa aktar
    edges_gdf.to_file(output_path, driver='GeoJSON')
    
    print(f"[OK] GeoJSON kaydedildi: {output_path}")


if __name__ == "__main__":
    # Test ve bilgi gösterimi
    print("🔍 Sakarya Yol Ağı Loader\n")
    
    graph = get_graph_cached()
    info = get_graph_info(graph)
    
    print(f"Düğüm Sayısı: {info['nodes']}")
    print(f"Kenar Sayısı: {info['edges']}")
    print(f"Bağlantılı Mı: {info['is_connected']}")
    print(f"\nEn Sık Kulllanılan Yol Tipleri:")
    for hw_type, count in info['top_highways']:
        print(f"  - {hw_type}: {count} kenar")
    print(f"\nEn Sık Kullanılan Yüzey Tipleri:")
    for surface, count in info['top_surfaces']:
        print(f"  - {surface}: {count} kenar")
    print(f"\nCache Bilgisi:")
    print(f"  - Dosya Var: {info['cache_exists']}")
    print(f"  - Dosya Boyutu: {info['cache_size_mb']:.2f} MB")
