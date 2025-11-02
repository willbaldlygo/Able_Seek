"""
Document processing for Able2.
Handles PDF extraction using PyMuPDF and text processing.
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, Any, Optional
import hashlib
from datetime import datetime

from backend.core import settings, retrieval_logger


class DocumentProcessor:
    """
    Process documents (primarily PDFs) for ingestion.

    Features:
    - PDF text extraction with PyMuPDF
    - Metadata extraction
    - Text cleaning
    """

    def __init__(self):
        """Initialize document processor."""
        self.logger = retrieval_logger
        self.logger.info("Initialized document processor")

    def process_pdf(
        self,
        file_path: str,
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a PDF file.

        Args:
            file_path: Path to PDF file
            document_id: Optional document ID (generated if not provided)

        Returns:
            Dict with:
                - document_id: Unique document ID
                - text: Extracted text
                - metadata: Document metadata
                - num_pages: Number of pages
                - file_path: Original file path
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not document_id:
            document_id = self._generate_document_id(file_path)

        self.logger.info(f"Processing PDF: {file_path.name}")

        # Open PDF
        doc = fitz.open(file_path)

        # Extract text from all pages
        text_pages = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text_pages.append(page.get_text())

        full_text = "\n\n".join(text_pages)

        # Extract metadata
        metadata = self._extract_pdf_metadata(doc, file_path)

        doc.close()

        self.logger.info(
            f"Processed PDF: {file_path.name} - "
            f"{len(doc)} pages, {len(full_text)} characters"
        )

        return {
            "document_id": document_id,
            "text": full_text,
            "metadata": metadata,
            "num_pages": len(doc),
            "file_path": str(file_path)
        }

    def process_text_file(
        self,
        file_path: str,
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a plain text file.

        Args:
            file_path: Path to text file
            document_id: Optional document ID

        Returns:
            Dict with document data
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not document_id:
            document_id = self._generate_document_id(file_path)

        self.logger.info(f"Processing text file: {file_path.name}")

        # Read text
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        # Extract metadata
        metadata = {
            "filename": file_path.name,
            "file_type": "text",
            "file_extension": file_path.suffix,
            "file_size": file_path.stat().st_size,
            "upload_date": datetime.now().isoformat(),
        }

        return {
            "document_id": document_id,
            "text": text,
            "metadata": metadata,
            "num_pages": 1,
            "file_path": str(file_path)
        }

    def process_file(
        self,
        file_path: str,
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a file (auto-detect type).

        Args:
            file_path: Path to file
            document_id: Optional document ID

        Returns:
            Dict with document data
        """
        file_path = Path(file_path)
        extension = file_path.suffix.lower()

        if extension == ".pdf":
            return self.process_pdf(str(file_path), document_id)
        elif extension in [".txt", ".md", ".markdown"]:
            return self.process_text_file(str(file_path), document_id)
        else:
            raise ValueError(f"Unsupported file type: {extension}")

    def clean_text(self, text: str) -> str:
        """
        Clean extracted text.

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        lines = text.split("\n")
        cleaned_lines = [line.strip() for line in lines if line.strip()]

        # Join with single newlines
        cleaned_text = "\n".join(cleaned_lines)

        # Remove excessive blank lines
        while "\n\n\n" in cleaned_text:
            cleaned_text = cleaned_text.replace("\n\n\n", "\n\n")

        return cleaned_text

    def _extract_pdf_metadata(
        self,
        doc: fitz.Document,
        file_path: Path
    ) -> Dict[str, Any]:
        """
        Extract metadata from PDF.

        Args:
            doc: PyMuPDF document
            file_path: File path

        Returns:
            Metadata dict
        """
        metadata = doc.metadata or {}

        return {
            "filename": file_path.name,
            "file_type": "pdf",
            "file_size": file_path.stat().st_size,
            "num_pages": len(doc),
            "title": metadata.get("title", file_path.stem),
            "author": metadata.get("author", "Unknown"),
            "subject": metadata.get("subject", ""),
            "keywords": metadata.get("keywords", ""),
            "creator": metadata.get("creator", ""),
            "producer": metadata.get("producer", ""),
            "creation_date": metadata.get("creationDate", ""),
            "modification_date": metadata.get("modDate", ""),
            "upload_date": datetime.now().isoformat(),
        }

    def _generate_document_id(self, file_path: Path) -> str:
        """
        Generate unique document ID from file path and content.

        Args:
            file_path: File path

        Returns:
            Document ID (hash)
        """
        # Use file path and modification time for uniqueness
        unique_string = f"{file_path.name}_{file_path.stat().st_mtime}"
        document_id = hashlib.sha256(unique_string.encode()).hexdigest()[:16]
        return document_id


# Global instance
_document_processor = None


def get_document_processor() -> DocumentProcessor:
    """Get or create global document processor instance."""
    global _document_processor
    if _document_processor is None:
        _document_processor = DocumentProcessor()
    return _document_processor
