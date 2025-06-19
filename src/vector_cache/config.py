from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    # Ruta en disco donde guardaremos el índice FAISS
    faiss_index_path: str = Field("data/faiss.index", env="FAISS_INDEX_PATH")
    # Umbral mínimo de similitud (coseno) para reutilizar rutas
    similarity_threshold: float = Field(0.90, env="VECTOR_THRESHOLD")
    # Nombre del modelo de embeddings
    model_name: str = Field("all-MiniLM-L6-v2", env="EMBEDDINGS_MODEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Instancia global de configuración
settings = Settings()
