"""
Vector store using ChromaDB for Able2.
Migrated from Able mk I with enhancements.
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid

from backend.core import settings, retrieval_logger


class VectorStore:
    """
    ChromaDB vector store for document embeddings.

    Features:
    - Persistent storage
    - Semantic search
    - Metadata filtering
    - Multiple collections
    """

    def __init__(self, collection_name: str = "documents"):
        """
        Initialize vector store.

        Args:
            collection_name: Name of the ChromaDB collection
        """
        self.logger = retrieval_logger
        self.collection_name = collection_name

        # Setup ChromaDB client
        persist_dir = Path(settings.path_vector_store)
        persist_dir.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.Client(ChromaSettings(
            persist_directory=str(persist_dir),
            anonymized_telemetry=False
        ))

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

        self.logger.info(f"Initialized vector store: {collection_name}")

    def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Add documents to vector store.

        Args:
            texts: List of text chunks
            metadatas: Optional metadata for each chunk
            ids: Optional custom IDs (auto-generated if not provided)

        Returns:
            List of document IDs
        """
        if not ids:
            ids = [str(uuid.uuid4()) for _ in texts]

        if not metadatas:
            metadatas = [{}] * len(texts)

        # Add to collection (ChromaDB handles embedding generation)
        self.collection.add(
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )

        self.logger.info(f"Added {len(texts)} documents to vector store")
        return ids

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic search in vector store.

        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional metadata filters

        Returns:
            List of search results with text, metadata, score
        """
        where_filter = self._build_where_filter(filters) if filters else None

        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_filter
        )

        # Format results
        formatted_results = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                formatted_results.append({
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "score": 1.0 - results["distances"][0][i],  # Convert distance to similarity
                    "source": "vector"
                })

        self.logger.debug(f"Vector search found {len(formatted_results)} results")
        return formatted_results

    def delete_document(self, document_id: str):
        """
        Delete a document from vector store.

        Args:
            document_id: Document ID to delete
        """
        # Delete all chunks belonging to this document
        self.collection.delete(
            where={"document_id": document_id}
        )
        self.logger.info(f"Deleted document {document_id} from vector store")

    def get_document_count(self) -> int:
        """Get total number of documents in store."""
        return self.collection.count()

    def clear(self):
        """Clear all documents from store."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        self.logger.warning(f"Cleared vector store: {self.collection_name}")

    def _build_where_filter(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build ChromaDB where filter from simple filter dict.

        Args:
            filters: Simple filter dict (e.g., {"document_id": "123"})

        Returns:
            ChromaDB where filter
        """
        # For simple equality filters
        if len(filters) == 1:
            key, value = list(filters.items())[0]
            return {key: {"$eq": value}}

        # For multiple filters (AND)
        return {
            "$and": [
                {key: {"$eq": value}}
                for key, value in filters.items()
            ]
        }

    def get_by_ids(self, ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get documents by IDs.

        Args:
            ids: List of document IDs

        Returns:
            List of documents
        """
        results = self.collection.get(ids=ids)

        formatted_results = []
        for i in range(len(results["ids"])):
            formatted_results.append({
                "id": results["ids"][i],
                "text": results["documents"][i],
                "metadata": results["metadatas"][i]
            })

        return formatted_results


# Global instance
_vector_store = None


def get_vector_store() -> VectorStore:
    """Get or create global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
