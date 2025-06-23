from vector_cache.config import settings
from vector_cache.pipeline import build_vector
from vector_cache.store.faiss_store import FaissStore
from optimized_route import optimize_delivery_routes

# Creamos el índice la primera vez (dim = embedding_dim + 2 coords)
# dim = embedding_dim + 3 valores numéricos (lat, lon, num_vehicles)
emb_dim = __import__("VectorCache.embeddings.model").embeddings.model._model.get_sentence_embedding_dimension()
_dim = emb_dim + 3
_store = FaissStore(dim=_dim)

def get_or_compute_route(context: dict) -> tuple[list, str]:
    """
    Devuelve (ruta, fuente) donde fuente es 'cache' o 'metaheuristic'.
    """
    vec = build_vector(context)          # 1) vector completo y normalizado
    results = _store.search(vec, k=1)    # 2) buscamos el vecino más cercano
    if results and results[0][0] >= settings.similarity_threshold:
        score, meta = results[0]
        return meta["route"], "cache"

    # 3) Si no hay coincidencia suficiente, calculamos nueva ruta
    route = optimize_delivery_routes(context)         # tu algoritmo actual
    # 4) Almacenamos vector + ruta
    _store.add(vec, {"route": route})
    
    return route, "metaheuristic"
