"""
Document chunking strategies for Able2.
Supports parent/child chunking for better context retrieval.
"""

from typing import List, Dict, Any, Tuple
import uuid

from backend.core import settings, retrieval_logger


class DocumentChunker:
    """
    Chunk documents with parent/child hierarchy.

    Strategy:
    - Child chunks: Small chunks for precise retrieval
    - Parent chunks: Larger chunks containing multiple children for context
    """

    def __init__(
        self,
        child_chunk_size: int = None,
        child_chunk_overlap: int = None,
        parent_chunk_size: int = None,
        use_parent_chunks: bool = True
    ):
        """
        Initialize document chunker.

        Args:
            child_chunk_size: Size of child chunks in characters
            child_chunk_overlap: Overlap between child chunks
            parent_chunk_size: Size of parent chunks
            use_parent_chunks: Whether to create parent chunks
        """
        self.logger = retrieval_logger

        self.child_chunk_size = child_chunk_size or settings.retrieval_chunk_size
        self.child_chunk_overlap = child_chunk_overlap or settings.retrieval_chunk_overlap
        self.parent_chunk_size = parent_chunk_size or (self.child_chunk_size * 2)
        self.use_parent_chunks = use_parent_chunks

        self.logger.info(
            f"Initialized chunker: child={self.child_chunk_size}, "
            f"overlap={self.child_chunk_overlap}, parent={self.parent_chunk_size}"
        )

    def chunk_document(
        self,
        text: str,
        document_id: str,
        metadata: Dict[str, Any] = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Chunk a document into parent and child chunks.

        Args:
            text: Document text
            document_id: Document ID
            metadata: Document metadata

        Returns:
            Tuple of (child_chunks, parent_chunks)
            Each chunk is a dict with: id, text, metadata
        """
        if metadata is None:
            metadata = {}

        # Create parent chunks first
        parent_chunks = []
        if self.use_parent_chunks:
            parent_chunks = self._create_chunks(
                text,
                chunk_size=self.parent_chunk_size,
                overlap=self.child_chunk_overlap,
                chunk_type="parent",
                document_id=document_id,
                metadata=metadata
            )

        # Create child chunks
        child_chunks = []
        if self.use_parent_chunks and parent_chunks:
            # Create child chunks within each parent
            for parent_idx, parent_chunk in enumerate(parent_chunks):
                parent_id = parent_chunk["id"]
                parent_text = parent_chunk["text"]

                # Chunk the parent text into children
                children = self._create_chunks(
                    parent_text,
                    chunk_size=self.child_chunk_size,
                    overlap=self.child_chunk_overlap,
                    chunk_type="child",
                    document_id=document_id,
                    metadata=metadata,
                    parent_id=parent_id,
                    parent_index=parent_idx
                )

                child_chunks.extend(children)
        else:
            # Create child chunks directly from document
            child_chunks = self._create_chunks(
                text,
                chunk_size=self.child_chunk_size,
                overlap=self.child_chunk_overlap,
                chunk_type="child",
                document_id=document_id,
                metadata=metadata
            )

        self.logger.debug(
            f"Chunked document {document_id}: "
            f"{len(child_chunks)} children, {len(parent_chunks)} parents"
        )

        return child_chunks, parent_chunks

    def _create_chunks(
        self,
        text: str,
        chunk_size: int,
        overlap: int,
        chunk_type: str,
        document_id: str,
        metadata: Dict[str, Any],
        parent_id: str = None,
        parent_index: int = None
    ) -> List[Dict[str, Any]]:
        """
        Create chunks from text.

        Args:
            text: Text to chunk
            chunk_size: Target chunk size
            overlap: Overlap between chunks
            chunk_type: "parent" or "child"
            document_id: Document ID
            metadata: Base metadata
            parent_id: Parent chunk ID (for child chunks)
            parent_index: Parent chunk index (for child chunks)

        Returns:
            List of chunk dicts
        """
        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence ending within next 100 chars
                sentence_end = self._find_sentence_boundary(text, end, end + 100)
                if sentence_end > end:
                    end = sentence_end

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunk_id = str(uuid.uuid4())

                chunk_metadata = {
                    **metadata,
                    "document_id": document_id,
                    "chunk_type": chunk_type,
                    "chunk_index": chunk_index,
                    "char_start": start,
                    "char_end": end,
                }

                if parent_id:
                    chunk_metadata["parent_id"] = parent_id
                    chunk_metadata["parent_index"] = parent_index

                chunks.append({
                    "id": chunk_id,
                    "text": chunk_text,
                    "metadata": chunk_metadata
                })

                chunk_index += 1

            # Move start position
            start = end - overlap

            # Prevent infinite loop
            if start <= end - chunk_size:
                start = end

        return chunks

    def _find_sentence_boundary(self, text: str, start: int, end: int) -> int:
        """
        Find sentence boundary within range.

        Args:
            text: Text to search
            start: Start position
            end: End position

        Returns:
            Position of sentence boundary, or start if not found
        """
        # Look for sentence endings
        sentence_endings = [". ", ".\n", "! ", "!\n", "? ", "?\n"]

        search_text = text[start:min(end, len(text))]

        best_pos = start
        for ending in sentence_endings:
            pos = search_text.rfind(ending)
            if pos > 0:
                best_pos = max(best_pos, start + pos + len(ending))

        return best_pos


def chunk_text_simple(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200
) -> List[str]:
    """
    Simple text chunking utility function.

    Args:
        text: Text to chunk
        chunk_size: Target chunk size
        overlap: Overlap between chunks

    Returns:
        List of text chunks
    """
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start = end - overlap

        # Prevent infinite loop
        if start <= end - chunk_size:
            start = end

    return chunks
