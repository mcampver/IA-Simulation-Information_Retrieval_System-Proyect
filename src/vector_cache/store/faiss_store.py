import faiss
import numpy as np
import os
import pickle

from vector_cache.config import settings

class FaissStore:
    def __init__(self, dim: int):
        self.dim = dim
        # Si existe un índice en disco, lo cargamos; sino creamos uno nuevo
        if os.path.isfile(settings.faiss_index_path):
            self.index = faiss.read_index(settings.faiss_index_path)
            with open(settings.faiss_index_path + ".meta", "rb") as f:
                self.metadata = pickle.load(f)
        else:
            # IndexFlatIP para similitud de coseno (requiere vectores L2-normalizados)
            self.index = faiss.IndexFlatIP(dim)
            self.metadata = []  # lista paralela a los vectores

    def add(self, vector: np.ndarray, meta: dict):
        """
        Añade un vector (shape=(dim,)) y su metadato asociado.
        """
        vec = vector.reshape(1, -1).astype("float32")
        self.index.add(vec)
        self.metadata.append(meta)
        self._save()

    def search(self, query: np.ndarray, k: int = 5):
        """
        Busca los k vecinos más cercanos al query (shape=(dim,)).
        Devuelve lista de tuplas (score, meta).
        """
        q = query.reshape(1, -1).astype("float32")
        distances, indices = self.index.search(q, k)
        results = []
        for score, idx in zip(distances[0], indices[0]):
            if idx < len(self.metadata):
                results.append((float(score), self.metadata[idx]))
        return results

    def _save(self):
        """Serializa el índice y los metadatos en disco."""
        faiss.write_index(self.index, settings.faiss_index_path)
        with open(settings.faiss_index_path + ".meta", "wb") as f:
            pickle.dump(self.metadata, f)
