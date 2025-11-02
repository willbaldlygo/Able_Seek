"""
Memory Agent for Able2.

CRITICAL: This agent WRAPS the existing Able mk I retrieval system.
It does NOT reimplement retrieval - it delegates to the proven hybrid retrieval.

Responsibilities:
- Search documents (using Able1 hybrid retrieval)
- Search emails (Phase 2)
- Search calendar (Phase 2)
- Multi-source search
- Query knowledge graph
"""

from typing import Dict, Any, List
from backend.schemas import AgentType, AgentMessage, AgentResponse, ActionType, SearchQuery
from backend.core import retrieval_logger
from backend.knowledge import get_hybrid_retriever, get_graph_rag, get_document_processor, DocumentChunker
from .base_agent import BaseAgent


class MemoryAgent(BaseAgent):
    """
    Memory Agent - handles all knowledge retrieval.

    This agent wraps the Able mk I retrieval system and provides
    a standardized interface for the orchestrator.
    """

    def __init__(self):
        """Initialize Memory Agent."""
        super().__init__(
            agent_type=AgentType.MEMORY,
            model_provider="ollama"  # Use fast local model
        )

        # Import existing Able1 components
        self.hybrid_retriever = get_hybrid_retriever()
        self.graph_rag = get_graph_rag()
        self.document_processor = get_document_processor()
        self.chunker = DocumentChunker()

        self.logger.info("Memory Agent initialized with Able1 retrieval system")

    async def process(self, message: AgentMessage) -> AgentResponse:
        """
        Process a memory-related message.

        Args:
            message: Agent message

        Returns:
            Agent response
        """
        # Determine action type from metadata
        action_type = message.metadata.get("action_type", ActionType.SEARCH_DOCUMENTS)

        self.logger.info(f"Memory Agent processing: {action_type}")

        if action_type == ActionType.SEARCH_DOCUMENTS:
            return await self.search_documents(message)
        elif action_type == ActionType.SEARCH_MULTI_SOURCE:
            return await self.search_multi_source(message)
        elif action_type == ActionType.QUERY_GRAPH:
            return await self.query_graph(message)
        elif action_type == ActionType.BUILD_GRAPH:
            return await self.build_graph(message)
        else:
            return self.create_response(
                success=False,
                data={},
                error=f"Unsupported action type: {action_type}"
            )

    async def search_documents(self, message: AgentMessage) -> AgentResponse:
        """
        Search documents using Able1 hybrid retrieval.

        Args:
            message: Search message with query

        Returns:
            Search results
        """
        query = message.content
        metadata = message.metadata

        # Extract search parameters
        top_k = metadata.get("top_k", 10)
        use_reranking = metadata.get("use_reranking", True)
        include_graph = metadata.get("include_graph", True)
        filters = metadata.get("filters", None)

        self.logger.info(f"Searching documents: '{query[:50]}...'")

        try:
            # Delegate to Able1 hybrid retrieval (WRAPPING, not reimplementing!)
            results = await self.hybrid_retriever.search(
                query=query,
                top_k=top_k,
                use_reranking=use_reranking,
                include_graph=include_graph,
                filters=filters
            )

            self.log_action("search_documents", success=True, details=f"Found {len(results)} results")

            return self.create_response(
                success=True,
                data={
                    "results": results,
                    "query": query,
                    "total_found": len(results)
                },
                reasoning=f"Searched documents using hybrid retrieval (vector + BM25 + graph). Found {len(results)} relevant results.",
                next_action="synthesize_results" if results else "refine_query"
            )

        except Exception as e:
            self.logger.error(f"Document search failed: {str(e)}")
            self.log_action("search_documents", success=False, details=str(e))

            return self.create_response(
                success=False,
                data={},
                error=f"Search failed: {str(e)}"
            )

    async def search_multi_source(self, message: AgentMessage) -> AgentResponse:
        """
        Search across multiple sources (documents, emails, calendar).

        Phase 1: Only documents
        Phase 2: Add emails and calendar

        Args:
            message: Search message

        Returns:
            Multi-source search results
        """
        query = message.content
        sources = message.metadata.get("sources", ["documents"])

        self.logger.info(f"Multi-source search: {sources}")

        all_results = []

        # Search documents
        if "documents" in sources:
            doc_response = await self.search_documents(message)
            if doc_response.success:
                doc_results = doc_response.data.get("results", [])
                for result in doc_results:
                    result["source_type"] = "document"
                all_results.extend(doc_results)

        # Search emails (Phase 2)
        if "emails" in sources:
            self.logger.info("Email search not implemented yet (Phase 2)")
            # TODO: Implement email search

        # Search calendar (Phase 2)
        if "calendar" in sources:
            self.logger.info("Calendar search not implemented yet (Phase 2)")
            # TODO: Implement calendar search

        # Sort combined results by score
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)

        return self.create_response(
            success=True,
            data={
                "results": all_results,
                "sources_searched": sources,
                "total_found": len(all_results)
            },
            reasoning=f"Searched across {len(sources)} sources. Found {len(all_results)} total results."
        )

    async def query_graph(self, message: AgentMessage) -> AgentResponse:
        """
        Query knowledge graph.

        Args:
            message: Graph query message

        Returns:
            Graph query results
        """
        query = message.content
        max_tokens = message.metadata.get("max_tokens", 1000)

        self.logger.info(f"Querying knowledge graph: '{query[:50]}...'")

        try:
            result = self.graph_rag.query_graph(query=query, max_tokens=max_tokens)

            self.log_action("query_graph", success=True)

            return self.create_response(
                success=True,
                data=result,
                reasoning="Queried knowledge graph for entity relationships and community summaries."
            )

        except Exception as e:
            self.logger.error(f"Graph query failed: {str(e)}")
            self.log_action("query_graph", success=False, details=str(e))

            return self.create_response(
                success=False,
                data={},
                error=f"Graph query failed: {str(e)}"
            )

    async def build_graph(self, message: AgentMessage) -> AgentResponse:
        """
        Build or rebuild knowledge graph.

        Args:
            message: Build graph message

        Returns:
            Build statistics
        """
        force_rebuild = message.metadata.get("force_rebuild", False)

        self.logger.info(f"Building knowledge graph (force_rebuild={force_rebuild})")

        try:
            # Get all documents
            # For now, we'll build from existing vector store
            # In full implementation, would fetch all documents

            stats = self.graph_rag.build_graph(
                documents=[],  # Empty for Phase 1
                force_rebuild=force_rebuild
            )

            self.log_action("build_graph", success=True)

            return self.create_response(
                success=True,
                data=stats,
                reasoning=f"Built knowledge graph: {stats.get('num_entities', 0)} entities, {stats.get('num_relationships', 0)} relationships"
            )

        except Exception as e:
            self.logger.error(f"Graph build failed: {str(e)}")
            self.log_action("build_graph", success=False, details=str(e))

            return self.create_response(
                success=False,
                data={},
                error=f"Graph build failed: {str(e)}"
            )

    async def add_document(
        self,
        file_path: str,
        document_id: str = None
    ) -> AgentResponse:
        """
        Add a document to the memory system.

        Args:
            file_path: Path to document
            document_id: Optional document ID

        Returns:
            Add document response
        """
        self.logger.info(f"Adding document: {file_path}")

        try:
            # Process document
            doc_data = self.document_processor.process_file(file_path, document_id)

            document_id = doc_data["document_id"]
            text = doc_data["text"]
            metadata = doc_data["metadata"]

            # Chunk document
            child_chunks, parent_chunks = self.chunker.chunk_document(
                text=text,
                document_id=document_id,
                metadata=metadata
            )

            # Add to retrieval system (delegates to Able1 components!)
            self.hybrid_retriever.add_document(
                text=text,
                document_id=document_id,
                metadata=metadata,
                chunks=child_chunks
            )

            self.log_action("add_document", success=True, details=f"Added {len(child_chunks)} chunks")

            return self.create_response(
                success=True,
                data={
                    "document_id": document_id,
                    "num_chunks": len(child_chunks),
                    "filename": metadata.get("filename")
                },
                reasoning=f"Successfully added document with {len(child_chunks)} chunks to memory system."
            )

        except Exception as e:
            self.logger.error(f"Add document failed: {str(e)}")
            self.log_action("add_document", success=False, details=str(e))

            return self.create_response(
                success=False,
                data={},
                error=f"Failed to add document: {str(e)}"
            )

    async def delete_document(self, document_id: str) -> AgentResponse:
        """
        Delete a document from memory system.

        Args:
            document_id: Document ID to delete

        Returns:
            Delete response
        """
        self.logger.info(f"Deleting document: {document_id}")

        try:
            self.hybrid_retriever.delete_document(document_id)

            self.log_action("delete_document", success=True)

            return self.create_response(
                success=True,
                data={"document_id": document_id},
                reasoning=f"Successfully deleted document {document_id} from memory system."
            )

        except Exception as e:
            self.logger.error(f"Delete document failed: {str(e)}")
            self.log_action("delete_document", success=False, details=str(e))

            return self.create_response(
                success=False,
                data={},
                error=f"Failed to delete document: {str(e)}"
            )

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get memory system statistics.

        Returns:
            Statistics dict
        """
        return self.hybrid_retriever.get_statistics()
