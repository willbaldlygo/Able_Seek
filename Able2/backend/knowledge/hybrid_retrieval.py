"""
Hybrid retrieval system for Able2.
Combines vector search, BM25, and GraphRAG for optimal results.
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict

from backend.core import settings, retrieval_logger
from .vector_store import get_vector_store
from .bm25_search import get_bm25_search
from .graph_rag import get_graph_rag
from .reranker import get_reranker


class HybridRetriever:
    """
    Hybrid retrieval combining multiple search strategies.

    Strategies:
    1. Vector search (semantic similarity)
    2. BM25 search (keyword matching)
    3. GraphRAG (knowledge graph traversal)
    4. Cross-encoder reranking

    Results are combined using Reciprocal Rank Fusion.
    """

    def __init__(self):
        """Initialize hybrid retriever."""
        self.logger = retrieval_logger

        # Initialize components
        self.vector_store = get_vector_store()
        self.bm25_search = get_bm25_search()
        self.graph_rag = get_graph_rag()

        # Reranker (lazy loaded)
        self._reranker = None

        self.logger.info("Initialized hybrid retriever")

    @property
    def reranker(self):
        """Lazy load reranker."""
        if self._reranker is None and settings.retrieval_use_reranking:
            self._reranker = get_reranker()
        return self._reranker

    async def search(
        self,
        query: str,
        top_k: int = None,
        use_reranking: bool = None,
        include_graph: bool = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search across all sources.

        Args:
            query: Search query
            top_k: Number of results to return
            use_reranking: Whether to use cross-encoder reranking
            include_graph: Whether to include GraphRAG results
            filters: Optional metadata filters

        Returns:
            List of ranked search results
        """
        if top_k is None:
            top_k = settings.retrieval_top_k

        if use_reranking is None:
            use_reranking = settings.retrieval_use_reranking

        if include_graph is None:
            include_graph = settings.graphrag_enabled

        self.logger.info(f"Hybrid search: '{query[:50]}...' (top_k={top_k})")

        # Perform vector search
        vector_results = self.vector_store.search(
            query=query,
            top_k=top_k * 2,  # Get more for fusion
            filters=filters
        )

        # Perform BM25 search
        bm25_results = self.bm25_search.search(
            query=query,
            top_k=top_k * 2,
            filters=filters
        )

        self.logger.debug(
            f"Retrieved {len(vector_results)} vector results, "
            f"{len(bm25_results)} BM25 results"
        )

        # Combine results using Reciprocal Rank Fusion
        fused_results = self._reciprocal_rank_fusion(
            [vector_results, bm25_results],
            weights=[settings.retrieval_vector_weight, settings.retrieval_bm25_weight]
        )

        # Take top-k fused results
        fused_results = fused_results[:top_k * 2]

        # Apply reranking if enabled
        if use_reranking and self.reranker and len(fused_results) > 0:
            self.logger.debug("Applying cross-encoder reranking")
            fused_results = self.reranker.rerank(
                query=query,
                results=fused_results,
                top_k=top_k
            )
        else:
            fused_results = fused_results[:top_k]

        # Get parent chunks if available
        fused_results = self._expand_to_parent_chunks(fused_results)

        self.logger.info(f"Hybrid search returned {len(fused_results)} results")

        return fused_results

    def _reciprocal_rank_fusion(
        self,
        result_lists: List[List[Dict[str, Any]]],
        weights: Optional[List[float]] = None,
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Combine multiple result lists using Reciprocal Rank Fusion.

        RRF formula: score(d) = Σ weight_i / (k + rank_i(d))

        Args:
            result_lists: List of result lists to fuse
            weights: Optional weights for each list (default: equal weights)
            k: RRF parameter (default: 60)

        Returns:
            Fused and ranked results
        """
        if weights is None:
            weights = [1.0] * len(result_lists)

        # Collect all unique documents
        doc_scores = defaultdict(float)
        doc_data = {}  # Store full document data

        for result_list, weight in zip(result_lists, weights):
            for rank, result in enumerate(result_list, start=1):
                doc_id = result["id"]

                # Calculate RRF score
                rrf_score = weight / (k + rank)
                doc_scores[doc_id] += rrf_score

                # Store document data (from first occurrence)
                if doc_id not in doc_data:
                    doc_data[doc_id] = result

        # Create fused results
        fused_results = []
        for doc_id, score in sorted(doc_scores.items(), key=lambda x: x[1], reverse=True):
            result = doc_data[doc_id].copy()
            result["fusion_score"] = score
            result["score"] = score  # Use fusion score as primary score
            fused_results.append(result)

        return fused_results

    def _expand_to_parent_chunks(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Expand child chunks to include parent chunk context.

        Args:
            results: Search results (may contain child chunks)

        Returns:
            Results with parent context added
        """
        expanded_results = []

        for result in results:
            metadata = result.get("metadata", {})
            chunk_type = metadata.get("chunk_type")

            if chunk_type == "child":
                parent_id = metadata.get("parent_id")

                if parent_id:
                    # Try to get parent chunk
                    try:
                        parent_chunks = self.vector_store.get_by_ids([parent_id])

                        if parent_chunks:
                            parent_chunk = parent_chunks[0]
                            result["parent_text"] = parent_chunk["text"]
                            result["parent_metadata"] = parent_chunk["metadata"]
                    except Exception as e:
                        self.logger.debug(f"Could not retrieve parent chunk: {str(e)}")

            expanded_results.append(result)

        return expanded_results

    def add_document(
        self,
        text: str,
        document_id: str,
        metadata: Dict[str, Any],
        chunks: List[Dict[str, Any]]
    ):
        """
        Add document to all retrieval systems.

        Args:
            text: Full document text
            document_id: Document ID
            metadata: Document metadata
            chunks: Pre-chunked document
        """
        self.logger.info(f"Adding document to hybrid retrieval: {document_id}")

        # Add chunks to vector store
        chunk_texts = [chunk["text"] for chunk in chunks]
        chunk_ids = [chunk["id"] for chunk in chunks]
        chunk_metadatas = [chunk["metadata"] for chunk in chunks]

        self.vector_store.add_documents(
            texts=chunk_texts,
            metadatas=chunk_metadatas,
            ids=chunk_ids
        )

        # Add to BM25
        self.bm25_search.add_documents(
            texts=chunk_texts,
            ids=chunk_ids,
            metadatas=chunk_metadatas
        )

        # Add to graph
        if settings.graphrag_enabled:
            title = metadata.get("title", metadata.get("filename", "Unknown"))
            self.graph_rag.add_document(
                document_id=document_id,
                title=title,
                metadata=metadata
            )

        self.logger.info(f"Document added successfully: {document_id}")

    def delete_document(self, document_id: str):
        """
        Delete document from all retrieval systems.

        Args:
            document_id: Document ID to delete
        """
        self.logger.info(f"Deleting document from hybrid retrieval: {document_id}")

        self.vector_store.delete_document(document_id)
        self.bm25_search.delete_document(document_id)

        if settings.graphrag_enabled:
            self.graph_rag.delete_document(document_id)

        self.logger.info(f"Document deleted successfully: {document_id}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get retrieval system statistics.

        Returns:
            Dict with statistics
        """
        return {
            "vector_store": {
                "document_count": self.vector_store.get_document_count()
            },
            "bm25_search": {
                "document_count": self.bm25_search.get_document_count()
            },
            "graph_rag": self.graph_rag.get_statistics() if settings.graphrag_enabled else {}
        }


# Global instance
_hybrid_retriever = None


def get_hybrid_retriever() -> HybridRetriever:
    """Get or create global hybrid retriever instance."""
    global _hybrid_retriever
    if _hybrid_retriever is None:
        _hybrid_retriever = HybridRetriever()
    return _hybrid_retriever
