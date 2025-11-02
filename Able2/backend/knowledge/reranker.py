"""
Cross-encoder reranking for Able2.
Reranks search results for better relevance.
"""

from typing import List, Dict, Any
from sentence_transformers import CrossEncoder

from backend.core import settings, retrieval_logger


class Reranker:
    """
    Cross-encoder reranker for search results.

    Uses a cross-encoder model to rerank results based on
    query-document relevance scores.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize reranker.

        Args:
            model_name: HuggingFace model name for cross-encoder
        """
        self.logger = retrieval_logger
        self.model_name = model_name

        self.logger.info(f"Loading reranker model: {model_name}")
        self.model = CrossEncoder(model_name)
        self.logger.info("Reranker model loaded")

    def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank search results using cross-encoder.

        Args:
            query: Search query
            results: List of search results
            top_k: Number of top results to return (None = return all)

        Returns:
            Reranked results with updated scores
        """
        if not results:
            return []

        # Extract texts from results
        texts = [result["text"] for result in results]

        # Create query-document pairs
        pairs = [[query, text] for text in texts]

        # Get cross-encoder scores
        self.logger.debug(f"Reranking {len(pairs)} results")
        scores = self.model.predict(pairs)

        # Update results with new scores
        for i, result in enumerate(results):
            result["rerank_score"] = float(scores[i])
            result["original_score"] = result.get("score", 0.0)

        # Sort by rerank score
        reranked = sorted(results, key=lambda x: x["rerank_score"], reverse=True)

        # Take top-k if specified
        if top_k:
            reranked = reranked[:top_k]

        self.logger.debug(f"Reranked {len(reranked)} results")
        return reranked


# Global instance
_reranker = None


def get_reranker() -> Reranker:
    """Get or create global reranker instance."""
    global _reranker
    if _reranker is None:
        _reranker = Reranker()
    return _reranker
