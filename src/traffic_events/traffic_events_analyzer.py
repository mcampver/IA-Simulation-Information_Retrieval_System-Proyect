# traffic_weight_modifier.py

from geopy.geocoders import Nominatim
from typing import List, Tuple, Dict, Any
from itertools import combinations
import networkx as nx
import math

def geocode_intersections(
    streets: List[str],
    city: str = "La Habana, Cuba",
    user_agent: str = "route_optimizer",
    importance_threshold: float = 0.5
) -> Dict[Tuple[str, str], Tuple[float, float]]:
    """
    Para cada par de calles (esquina), consulta Nominatim con 
    "calle1 y calle2, city" y devuelve un mapping de pares→(lat,lon),
    descartando localizaciones con importancia < threshold.
    """
    geo = Nominatim(user_agent=user_agent)
    intersection_coords: Dict[Tuple[str, str], Tuple[float, float]] = {}
    for c1, c2 in combinations(streets, 2):
        query = f"{c1} y {c2}, {city}"
        loc = geo.geocode(query)
        if loc is None:
            continue
        imp = float(loc.raw.get("importance", 0))
        if imp < importance_threshold:
            continue
        intersection_coords[(c1, c2)] = (loc.latitude, loc.longitude)
    return intersection_coords

def nearest_node(
    graph: nx.Graph,
    coord: Tuple[float, float],
    node_attrs: Tuple[str,str] = ("lat","lon")
) -> Any:
    """
    Busca el nodo de `graph` cuyas coordenadas (node_attrs) 
    estén más cerca de coord.
    """
    lat0, lon0 = coord
    best_node, best_dist = None, float("inf")
    for n, data in graph.nodes(data=True):
        lat, lon = data[node_attrs[0]], data[node_attrs[1]]
        d = math.hypot(lat - lat0, lon - lon0)
        if d < best_dist:
            best_node, best_dist = n, d
    return best_node

def apply_traffic_weights(
    graph: nx.Graph,
    eventos: List[Dict[str, Any]],
    penalty_factor: float = 2.0,
    penalty_offset: float = 100.0,
    city: str = "La Habana, Cuba",
    user_agent: str = "route_optimizer",
    importance_threshold: float = 0.5
) -> None:
    """
    1) Extrae la lista única de calles de todos los eventos.
    2) Geocodifica cada intersección (par de calles).
    3) Para cada coordenada válida, penaliza IN-PLACE
       todas las aristas incidentes al nodo más cercano.
    """
    # 1) Todas las calles afectadas
    all_streets = {
        calle
        for ev in eventos
        for calle in ev.get("streets", [])
    }
    # 2) Geocodificar intersecciones
    intersections = geocode_intersections(
        list(all_streets),
        city=city,
        user_agent=user_agent,
        importance_threshold=importance_threshold
    )
    # 3) Penalizar aristas
    for (c1, c2), coord in intersections.items():
        node = nearest_node(graph, coord)
        if node is None:
            continue
        for u, v, data in graph.edges(node, data=True):
            base = data.get("weight", 1.0)
            data["weight"] = base * penalty_factor + penalty_offset
