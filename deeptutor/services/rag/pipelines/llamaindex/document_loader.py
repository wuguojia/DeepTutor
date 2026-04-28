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
        """Extract text from EPUB files with enhanced metadata and structure."""
        try:
            from ebooklib import epub
            import re

            book = epub.read_epub(str(file_path))

            # Extract metadata
            metadata_parts: list[str] = []
            title = book.get_metadata('DC', 'title')
            if title:
                metadata_parts.append(f"Title: {title[0][0]}")

            author = book.get_metadata('DC', 'creator')
            if author:
                metadata_parts.append(f"Author: {author[0][0]}")

            language = book.get_metadata('DC', 'language')
            if language:
                metadata_parts.append(f"Language: {language[0][0]}")

            publisher = book.get_metadata('DC', 'publisher')
            if publisher:
                metadata_parts.append(f"Publisher: {publisher[0][0]}")

            # Build result with metadata
            result_parts: list[str] = []
            if metadata_parts:
                result_parts.append("=== EPUB Metadata ===\n" + "\n".join(metadata_parts))

            chapters: list[str] = []
            image_count = 0

            for item in book.get_items():
                if item.get_type() == epub.ITEM_DOCUMENT:
                    try:
                        content = item.get_content().decode('utf-8', errors='ignore')
                        # Extract chapter title
                        chapter_title = self._extract_chapter_title(content)
                        # Strip HTML tags with enhanced processing
                        text = self._strip_html_tags_enhanced(content)
                        if text.strip():
                            if chapter_title:
                                chapters.append(f"--- {chapter_title} ---\n{text}")
                            else:
                                chapters.append(text)
                    except Exception as exc:
                        self.logger.warning(f"Failed to extract chapter: {exc}")
                        continue
                elif item.get_type() == epub.ITEM_IMAGE:
                    image_count += 1

            if chapters:
                result_parts.append("\n\n".join(chapters))

            if image_count > 0:
                result_parts.append(f"\n[This EPUB contains {image_count} embedded images]")

            return "\n\n".join(result_parts)
        except ImportError:
            self.logger.warning("ebooklib not installed. Cannot extract EPUB text.")
            return ""
        except Exception as exc:
            self.logger.error(f"Failed to extract EPUB text: {exc}")
            return ""

    def _extract_chapter_title(self, html_content: str) -> str:
        """Extract chapter title from HTML content."""
        import re
        import html

        # Try h1 first
        h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_content, re.IGNORECASE | re.DOTALL)
        if h1_match:
            title = re.sub(r'<[^>]+>', '', h1_match.group(1))
            return html.unescape(title).strip()

        # Try h2
        h2_match = re.search(r'<h2[^>]*>(.*?)</h2>', html_content, re.IGNORECASE | re.DOTALL)
        if h2_match:
            title = re.sub(r'<[^>]+>', '', h2_match.group(1))
            return html.unescape(title).strip()

        # Try title tag
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
        if title_match:
            title = re.sub(r'<[^>]+>', '', title_match.group(1))
            return html.unescape(title).strip()

        return ""

    def _strip_html_tags_enhanced(self, html_content: str) -> str:
        """Enhanced HTML tag stripping with structure preservation."""
        import re
        import html

        # Remove script and style tags
        text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # Preserve code blocks
        text = re.sub(r'<pre[^>]*>(.*?)</pre>', r'\n[CODE]\n\1\n[/CODE]\n', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', text, flags=re.DOTALL | re.IGNORECASE)

        # Convert lists
        text = re.sub(r'<li[^>]*>', '\n• ', text, flags=re.IGNORECASE)
        text = re.sub(r'</li>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</?[ou]l[^>]*>', '\n', text, flags=re.IGNORECASE)

        # Convert tables
        text = re.sub(r'<tr[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</tr>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<t[hd][^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</t[hd]>', '\t', text, flags=re.IGNORECASE)
        text = re.sub(r'</?table[^>]*>', '\n[TABLE]\n', text, flags=re.IGNORECASE)

        # Block elements
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</?p[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</?div[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</h[1-6]>', '\n', text, flags=re.IGNORECASE)

        # Remove remaining tags
        text = re.sub(r'<[^>]+>', ' ', text)

        # Unescape entities
        text = html.unescape(text)

        # Clean whitespace
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

        return text.strip()
