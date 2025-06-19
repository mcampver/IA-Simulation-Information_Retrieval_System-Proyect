import numpy as np
from sentence_transformers import SentenceTransformer
from vector_cache.config import settings

# Cargamos el modelo UNA SOLA vez al importar
_model: SentenceTransformer = SentenceTransformer(settings.model_name)

def encode(texts: list[str] | str) -> np.ndarray:
    """
    Convierte una o varias cadenas de texto en sus vectores de embeddings.
    - texts: cadena o lista de cadenas.
    - Devuelve un numpy array de shape (n_texts, dim_embedding).
    """
    # Aseguramos lista
    batch = texts if isinstance(texts, list) else [texts]
    embeddings = _model.encode(batch, convert_to_numpy=True, normalize_embeddings=True)
    return embeddings  # ya normalizados L2
