"""
GraphRAG integration for Able2.
Provides knowledge graph-based retrieval.

This is a simplified implementation for Phase 1.
Full GraphRAG with community detection in later phases.
"""

from typing import List, Dict, Any, Optional
import networkx as nx
import json
from pathlib import Path
from networkx.readwrite import json_graph

from backend.core import settings, retrieval_logger


class GraphRAG:
    """
    Knowledge graph for document relationships.

    Phase 1: Simple entity-relationship graph
    Future: Full GraphRAG with hierarchical communities
    """

    def __init__(self):
        """Initialize GraphRAG."""
        self.logger = retrieval_logger
        self.graph = nx.Graph()

        self.graph_path = Path(settings.path_graph_store) / "knowledge_graph.json"
        # Legacy pickle path for migration
        self._legacy_pickle_path = Path(settings.path_graph_store) / "knowledge_graph.pkl"
        self._load_graph()

        self.logger.info("Initialized GraphRAG")

    def build_graph(
        self,
        documents: List[Dict[str, Any]],
        force_rebuild: bool = False
    ) -> Dict[str, Any]:
        """
        Build knowledge graph from documents.

        Args:
            documents: List of documents with text and metadata
            force_rebuild: Rebuild even if graph exists

        Returns:
            Dict with build statistics
        """
        if force_rebuild:
            self.graph.clear()

        self.logger.info(f"Building graph from {len(documents)} documents")

        # For Phase 1, create simple document nodes
        # Future: Extract entities and relationships using NER/LLM

        for doc in documents:
            doc_id = doc.get("document_id") or doc.get("id")
            title = doc.get("metadata", {}).get("title", doc.get("filename", "Unknown"))

            # Add document node
            self.graph.add_node(
                doc_id,
                type="document",
                title=title,
                metadata=doc.get("metadata", {})
            )

        stats = {
            "num_entities": self.graph.number_of_nodes(),
            "num_relationships": self.graph.number_of_edges(),
            "num_communities": 0  # Not implemented in Phase 1
        }

        self._save_graph()
        self.logger.info(f"Built graph: {stats}")

        return stats

    def query_graph(
        self,
        query: str,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        Query knowledge graph.

        Args:
            query: Natural language query
            max_tokens: Max tokens for response

        Returns:
            Dict with graph query results
        """
        self.logger.debug(f"Querying graph: {query}")

        # Phase 1: Return basic graph statistics
        # Future: Semantic graph traversal and community summaries

        nodes = list(self.graph.nodes(data=True))

        # Extract relevant information
        documents = [
            {
                "id": node_id,
                "title": data.get("title", "Unknown"),
                "type": data.get("type", "unknown")
            }
            for node_id, data in nodes[:10]  # Limit to 10 for now
        ]

        return {
            "answer": f"Found {len(nodes)} documents in knowledge graph.",
            "documents": documents,
            "entities_found": [node_id for node_id, _ in nodes[:10]],
            "relationships_found": [],
            "community_summaries": []
        }

    def get_related_documents(
        self,
        document_id: str,
        max_results: int = 5
    ) -> List[str]:
        """
        Get documents related to a given document.

        Args:
            document_id: Source document ID
            max_results: Max number of related documents

        Returns:
            List of related document IDs
        """
        if document_id not in self.graph:
            return []

        # Get neighbors
        neighbors = list(self.graph.neighbors(document_id))

        return neighbors[:max_results]

    def add_document(
        self,
        document_id: str,
        title: str,
        metadata: Dict[str, Any]
    ):
        """
        Add a document to the graph.

        Args:
            document_id: Document ID
            title: Document title
            metadata: Document metadata
        """
        self.graph.add_node(
            document_id,
            type="document",
            title=title,
            metadata=metadata
        )

        self._save_graph()
        self.logger.debug(f"Added document to graph: {document_id}")

    def delete_document(self, document_id: str):
        """
        Delete a document from the graph.

        Args:
            document_id: Document ID to delete
        """
        if document_id in self.graph:
            self.graph.remove_node(document_id)
            self._save_graph()
            self.logger.debug(f"Deleted document from graph: {document_id}")

    def clear(self):
        """Clear the entire graph."""
        self.graph.clear()

        if self.graph_path.exists():
            self.graph_path.unlink()

        self.logger.warning("Cleared knowledge graph")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get graph statistics.

        Returns:
            Dict with graph stats
        """
        return {
            "num_nodes": self.graph.number_of_nodes(),
            "num_edges": self.graph.number_of_edges(),
            "is_connected": nx.is_connected(self.graph) if self.graph.number_of_nodes() > 0 else False
        }

    def _save_graph(self):
        """Save graph to disk using JSON (secure serialization)."""
        self.graph_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert graph to JSON-serializable format
        graph_data = json_graph.node_link_data(self.graph)

        with open(self.graph_path, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, indent=2, default=str)

        self.logger.debug("Saved knowledge graph to disk (JSON format)")

    def _load_graph(self):
        """Load graph from disk using JSON (secure deserialization)."""
        # Try loading from JSON first
        if self.graph_path.exists():
            try:
                with open(self.graph_path, "r", encoding="utf-8") as f:
                    graph_data = json.load(f)

                self.graph = json_graph.node_link_graph(graph_data)

                self.logger.info(
                    f"Loaded knowledge graph: "
                    f"{self.graph.number_of_nodes()} nodes, "
                    f"{self.graph.number_of_edges()} edges"
                )
                return
            except Exception as e:
                self.logger.error(f"Failed to load knowledge graph from JSON: {str(e)}")

        # Check for legacy pickle file and migrate if found
        if self._legacy_pickle_path.exists():
            self.logger.warning(
                "Found legacy pickle graph file. "
                "Please manually verify and migrate to JSON format for security. "
                "Legacy pickle files will not be loaded automatically."
            )
            # Note: We intentionally do NOT load pickle files automatically
            # as they pose a security risk (arbitrary code execution)

        self.logger.debug("No existing knowledge graph found")


# Global instance
_graph_rag = None


def get_graph_rag() -> GraphRAG:
    """Get or create global GraphRAG instance."""
    global _graph_rag
    if _graph_rag is None:
        _graph_rag = GraphRAG()
    return _graph_rag
