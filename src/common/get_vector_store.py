import os
from typing import Literal

from common.chromadb_vector_store import ChromaDbVectorStore
from common.data import DATA_DIR
from common.load_settings import load_settings
from common.vector_store import VectorStore

VectorDbType = Literal["chromadb"]

vector_db_config_defaults: dict[VectorDbType, dict] = {
    "chromadb": {
        "persist_directory": os.path.join(DATA_DIR, "chroma_db"),
        "embedding_model": "sentence-transformers/all-mpnet-base-v2",
    },
}


def get_vector_store(db_type: VectorDbType, config: dict) -> VectorStore:
    if db_type == "chromadb":
        return ChromaDbVectorStore(**config)
    raise ValueError(f"Unknown db_type: {db_type}")


def get_vector_store_config() -> tuple[VectorDbType, dict]:
    settings = load_settings()
    db_type = settings.get("vector_db_type", "chromadb")
    # Validate db_type
    if db_type not in vector_db_config_defaults:
        raise ValueError(f"Unknown db_type: {db_type}")
    config = vector_db_config_defaults[db_type]
    config.update(settings.get(db_type, {}))
    return db_type, config


def get_vector_store_from_config() -> VectorStore:
    db_type, config = get_vector_store_config()
    return get_vector_store(db_type, config)
