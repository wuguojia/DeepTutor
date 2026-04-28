"""Document loading for the LlamaIndex RAG pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from llama_index.core import Document

from deeptutor.logging import get_logger
from deeptutor.services.rag.file_routing import FileTypeRouter


class LlamaIndexDocumentLoader:
    """Convert source files into LlamaIndex ``Document`` objects."""

    def __init__(self, logger=None) -> None:
        self.logger = logger or get_logger("LlamaIndexDocumentLoader")

    async def load(self, file_paths: Iterable[str]) -> list[Document]:
        documents: list[Document] = []
        classification = FileTypeRouter.classify_files(list(file_paths))

        for file_path_str in classification.parser_files:
            file_path = Path(file_path_str)
            ext = file_path.suffix.lower()
            if ext == ".pdf":
                self.logger.info(f"Parsing PDF: {file_path.name}")
                text = self._extract_pdf_text(file_path)
            elif ext == ".epub":
                self.logger.info(f"Parsing EPUB: {file_path.name}")
                text = self._extract_epub_text(file_path)
            else:
                self.logger.warning(f"Unsupported parser file type: {file_path.name}")
                continue
            self._append_if_nonempty(documents, file_path, text)

        for file_path_str in classification.text_files:
            file_path = Path(file_path_str)
            self.logger.info(f"Parsing text: {file_path.name}")
            text = await FileTypeRouter.read_text_file(str(file_path))
            self._append_if_nonempty(documents, file_path, text)

        for file_path_str in classification.unsupported:
            self.logger.warning(f"Skipped unsupported file: {Path(file_path_str).name}")

        return documents

    def _append_if_nonempty(
        self, documents: list[Document], file_path: Path, text: str
    ) -> None:
        if text.strip():
            documents.append(
                Document(
                    text=text,
                    metadata={
                        "file_name": file_path.name,
                        "file_path": str(file_path),
                    },
                )
            )
            self.logger.info(f"Loaded: {file_path.name} ({len(text)} chars)")
        else:
            self.logger.warning(f"Skipped empty document: {file_path.name}")

    def _extract_pdf_text(self, file_path: Path) -> str:
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(file_path)
            texts = [page.get_text() for page in doc]
            doc.close()
            return "\n\n".join(texts)
        except ImportError:
            self.logger.warning("PyMuPDF not installed. Cannot extract PDF text.")
            return ""
        except Exception as exc:
            self.logger.error(f"Failed to extract PDF text: {exc}")
            return ""

    def _extract_epub_text(self, file_path: Path) -> str:
        """Extract text from EPUB files."""
        try:
            from ebooklib import epub
            import re

            book = epub.read_epub(str(file_path))
            chapters: list[str] = []

            for item in book.get_items():
                if item.get_type() == epub.ITEM_DOCUMENT:
                    try:
                        content = item.get_content().decode('utf-8', errors='ignore')
                        # Strip HTML tags
                        text = self._strip_html_tags(content)
                        if text.strip():
                            chapters.append(text)
                    except Exception as exc:
                        self.logger.warning(f"Failed to extract chapter: {exc}")
                        continue

            return "\n\n".join(chapters)
        except ImportError:
            self.logger.warning("ebooklib not installed. Cannot extract EPUB text.")
            return ""
        except Exception as exc:
            self.logger.error(f"Failed to extract EPUB text: {exc}")
            return ""

    def _strip_html_tags(self, html_content: str) -> str:
        """Strip HTML tags from content and return plain text."""
        import re
        import html

        # Remove script and style tags with their content
        text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # Remove all HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)

        # Unescape HTML entities
        text = html.unescape(text)

        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)

        return text.strip()
