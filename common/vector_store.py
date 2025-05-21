from abc import ABC, abstractmethod
from typing import List


class VectorStore(ABC):
    @abstractmethod
    def from_documents(self, documents: List, **kwargs):
        pass

    @abstractmethod
    def add_documents(self, documents: List, **kwargs):
        pass

    @abstractmethod
    def load(self):
        pass

    @abstractmethod
    def as_retriever(self, **kwargs):
        pass

    @abstractmethod
    def get_notes_retriever(self, **kwargs):
        pass

    @abstractmethod
    def get_gmail_retriever(self, **kwargs):
        pass

    @abstractmethod
    def similarity_search_with_distance(
        self, query: str, k: int = 5, source: str = "", score_threshold: float = 0.2
    ):
        pass
