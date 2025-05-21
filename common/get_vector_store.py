from typing import Literal
from common.vector_store import VectorStore
from common.chromadb_vector_store import ChromaDbVectorStore

VectorDbType = Literal["chromadb"]


def get_vector_store(db_type: VectorDbType, config: dict) -> VectorStore:
    if db_type == "chromadb":
        return ChromaDbVectorStore(**config)
    raise ValueError(f"Unknown db_type: {db_type}")
