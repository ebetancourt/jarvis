import os
from typing import Literal, Dict, Tuple
from common.vector_store import VectorStore
from common.chromadb_vector_store import ChromaDbVectorStore
from common.weaviate_vector_store import WeaviateVectorStore
from common.load_settings import load_settings
from common.data import DATA_DIR

VectorDbType = Literal["chromadb", "weaviate"]

vector_db_config_defaults: Dict[VectorDbType, dict] = {
    "chromadb": {
        "persist_directory": os.path.join(DATA_DIR, "chroma_db"),
        "embedding_model": "sentence-transformers/all-mpnet-base-v2",
    },
    "weaviate": {
        "host": "localhost",
        "port": 8080,
        "grpc_host": "localhost",
        "grpc_port": 50051,
        "secure": False,
        "grpc_secure": False,
        "embedding_model": "sentence-transformers/all-mpnet-base-v2",
    },
}


def get_vector_store(db_type: VectorDbType, config: dict, **kwargs) -> VectorStore:
    if db_type == "chromadb":
        return ChromaDbVectorStore(**config, **kwargs)
    if db_type == "weaviate":
        return WeaviateVectorStore(**config, **kwargs)
    raise ValueError(f"Unknown db_type: {db_type}")


def get_vector_store_config(**kwargs) -> Tuple[VectorDbType, dict]:
    settings = load_settings()
    db_type = settings.get("vector_db_type", "chromadb")
    # Validate db_type
    if db_type not in vector_db_config_defaults:
        raise ValueError(f"Unknown db_type: {db_type}")
    config = vector_db_config_defaults[db_type]
    db_settings = settings.get(db_type, {})
    config.update(db_settings)
    return db_type, config


def get_vector_store_from_config(**kwargs) -> VectorStore:
    db_type, config = get_vector_store_config(**kwargs)
    return get_vector_store(db_type, config, **kwargs)
