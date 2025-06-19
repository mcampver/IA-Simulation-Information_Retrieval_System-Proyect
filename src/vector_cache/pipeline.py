import json
import numpy as np

from vector_cache.embeddings.model import encode
from vector_cache.geocoding import get_latlon

def build_vector(context: dict) -> np.ndarray:
    """
    A partir del dict de contexto:
      1) Geocodifica cada dirección de entrega.
      2) Crea un JSON canónico ordenado.
      3) Genera embedding del JSON.
      4) Concatena coords (media de latitudes/longitudes).
    Devuelve un vector 1D numpy normalizado.
    """
    # 1) Extraer y geocodificar direcciones
    coords = []
    for entrega in context["pedido"]["entregas"]:
        addr = entrega["direccion"]
        coords.append(get_latlon(addr))
    # Media de coords (simplificación)
    lats, lons = zip(*coords)
    avg_lat, avg_lon = float(sum(lats)/len(lats)), float(sum(lons)/len(lons))

    # 2) Serializar contexto en string ordenado
    canon = json.dumps(context, sort_keys=True, ensure_ascii=False)

    # 3) Embedding textual
    vec_text = encode(canon)[0]  # (dim,)

    # 4) Concatena lat/lon normalizados (rango aproximado [-90,90]/[-180,180])
    vec = np.concatenate([vec_text, np.array([avg_lat/90, avg_lon/180])])
    # Quedará L2-normalizarlo nuevamente: aunque vec_text ya lo esté, 
    # la parte numérica puede romper la norma. 
    norm = np.linalg.norm(vec)
    return vec / norm
