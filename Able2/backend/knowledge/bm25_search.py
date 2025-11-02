"""
BM25 lexical search for Able2.
Provides keyword-based search to complement vector search.
"""

from rank_bm25 import BM25Okapi
from typing import List, Dict, Any, Optional
import pickle
from pathlib import Path

from backend.core import settings, retrieval_logger


class BM25Search:
    """
    BM25 lexical search engine.

    Provides keyword-based search that complements semantic vector search.
    Particularly good for exact term matches and acronyms.
    """

    def __init__(self):
        """Initialize BM25 search."""
        self.logger = retrieval_logger
        self.bm25 = None
        self.documents = []
        self.doc_ids = []
        self.doc_metadatas = []

        self.index_path = Path(settings.path_vector_store) / "bm25_index.pkl"
        self._load_index()

        self.logger.info("Initialized BM25 search")

    def add_documents(
        self,
        texts: List[str],
        ids: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Add documents to BM25 index.

        Args:
            texts: List of document texts
            ids: List of document IDs
            metadatas: Optional metadata for each document
        """
        if not metadatas:
            metadatas = [{}] * len(texts)

        # Tokenize documents
        tokenized_docs = [self._tokenize(doc) for doc in texts]

        # Add to existing documents
        self.documents.extend(tokenized_docs)
        self.doc_ids.extend(ids)
        self.doc_metadatas.extend(metadatas)

        # Rebuild BM25 index
        self.bm25 = BM25Okapi(self.documents)

        self.logger.info(f"Added {len(texts)} documents to BM25 index")

        # Save index
        self._save_index()

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search documents using BM25.

        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional metadata filters

        Returns:
            List of search results
        """
        if not self.bm25 or len(self.documents) == 0:
            self.logger.warning("BM25 index is empty")
            return []

        # Tokenize query
        tokenized_query = self._tokenize(query)

        # Get BM25 scores
        scores = self.bm25.get_scores(tokenized_query)

        # Get top-k indices
        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:top_k * 2]  # Get more to account for filtering

        # Format results
        results = []
        for idx in top_indices:
            if scores[idx] <= 0:
                continue

            metadata = self.doc_metadatas[idx]

            # Apply filters
            if filters:
                if not self._matches_filters(metadata, filters):
                    continue

            # Reconstruct text from tokens
            text = " ".join(self.documents[idx])

            results.append({
                "id": self.doc_ids[idx],
                "text": text,
                "metadata": metadata,
                "score": float(scores[idx]),
                "source": "bm25"
            })

            if len(results) >= top_k:
                break

        self.logger.debug(f"BM25 search found {len(results)} results")
        return results

    def delete_document(self, document_id: str):
        """
        Delete a document from BM25 index.

        Args:
            document_id: Document ID to delete
        """
        # Find indices to delete
        indices_to_delete = [
            i for i, doc_id in enumerate(self.doc_ids)
            if doc_id == document_id or
            (self.doc_metadatas[i].get("document_id") == document_id)
        ]

        # Delete in reverse order to preserve indices
        for idx in sorted(indices_to_delete, reverse=True):
            del self.documents[idx]
            del self.doc_ids[idx]
            del self.doc_metadatas[idx]

        # Rebuild index
        if len(self.documents) > 0:
            self.bm25 = BM25Okapi(self.documents)
        else:
            self.bm25 = None

        self.logger.info(f"Deleted document {document_id} from BM25 index")
        self._save_index()

    def clear(self):
        """Clear all documents from index."""
        self.documents = []
        self.doc_ids = []
        self.doc_metadatas = []
        self.bm25 = None

        if self.index_path.exists():
            self.index_path.unlink()

        self.logger.warning("Cleared BM25 index")

    def get_document_count(self) -> int:
        """Get number of documents in index."""
        return len(self.documents)

    def _tokenize(self, text: str) -> List[str]:
        """
        Simple tokenization.

        Args:
            text: Text to tokenize

        Returns:
            List of tokens
        """
        # Simple whitespace tokenization with lowercasing
        # Could be enhanced with stemming, stopword removal, etc.
        return text.lower().split()

    def _matches_filters(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """
        Check if metadata matches filters.

        Args:
            metadata: Document metadata
            filters: Filter criteria

        Returns:
            True if matches, False otherwise
        """
        for key, value in filters.items():
            if metadata.get(key) != value:
                return False
        return True

    def _save_index(self):
        """Save BM25 index to disk."""
        if not self.bm25:
            return

        index_data = {
            "documents": self.documents,
            "doc_ids": self.doc_ids,
            "doc_metadatas": self.doc_metadatas
        }

        self.index_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.index_path, "wb") as f:
            pickle.dump(index_data, f)

        self.logger.debug("Saved BM25 index to disk")

    def _load_index(self):
        """Load BM25 index from disk."""
        if not self.index_path.exists():
            self.logger.debug("No existing BM25 index found")
            return

        try:
            with open(self.index_path, "rb") as f:
                index_data = pickle.load(f)

            self.documents = index_data["documents"]
            self.doc_ids = index_data["doc_ids"]
            self.doc_metadatas = index_data["doc_metadatas"]

            if len(self.documents) > 0:
                self.bm25 = BM25Okapi(self.documents)

            self.logger.info(f"Loaded BM25 index with {len(self.documents)} documents")
        except Exception as e:
            self.logger.error(f"Failed to load BM25 index: {str(e)}")


# Global instance
_bm25_search = None


def get_bm25_search() -> BM25Search:
    """Get or create global BM25 search instance."""
    global _bm25_search
    if _bm25_search is None:
        _bm25_search = BM25Search()
    return _bm25_search
