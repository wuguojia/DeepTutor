"""Enhanced EPUB extraction with AI classification, vision analysis, and performance optimization.

This module provides advanced EPUB processing with optional AI-powered features:
- Content classification for better organization
- Image analysis using vision models
- Performance optimization with caching and streaming
"""

from __future__ import annotations

import asyncio
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def extract_epub_enhanced(
    data: bytes,
    filename: str,
    enable_classification: bool = False,
    enable_image_analysis: bool = False,
    enable_caching: bool = True,
) -> str:
    """Extract text from EPUB with optional AI enhancements.

    Args:
        data: EPUB file data
        filename: Name of the EPUB file
        enable_classification: Enable AI content classification
        enable_image_analysis: Enable vision-based image analysis
        enable_caching: Enable performance caching

    Returns:
        Extracted and enhanced text content

    Raises:
        CorruptDocumentError: If EPUB is invalid or corrupted
    """
    try:
        import ebooklib
        from ebooklib import epub
    except ImportError:
        from deeptutor.utils.document_extractor import CorruptDocumentError

        raise CorruptDocumentError(
            f"{filename}: ebooklib not installed", filename=filename
        )

    from deeptutor.utils.document_extractor import CorruptDocumentError

    # Parse EPUB
    try:
        book = epub.read_epub(io.BytesIO(data))
    except Exception as exc:
        raise CorruptDocumentError(
            f"{filename}: failed to open EPUB ({exc})", filename=filename
        ) from exc

    # Extract basic metadata
    metadata_parts: list[str] = []
    title = book.get_metadata('DC', 'title')
    title_str = title[0][0] if title else "Unknown"

    author = book.get_metadata('DC', 'creator')
    author_str = author[0][0] if author else "Unknown"

    language = book.get_metadata('DC', 'language')
    language_str = language[0][0] if language else "en"

    publisher = book.get_metadata('DC', 'publisher')

    metadata_parts.append(f"Title: {title_str}")
    metadata_parts.append(f"Author: {author_str}")
    metadata_parts.append(f"Language: {language_str}")
    if publisher:
        metadata_parts.append(f"Publisher: {publisher[0][0]}")

    result_parts: list[str] = []
    result_parts.append("=== EPUB Metadata ===\n" + "\n".join(metadata_parts))

    # Extract chapters
    chapters: list[str] = []
    image_count = 0
    sample_text = ""  # For classification

    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            try:
                content = item.get_content().decode('utf-8', errors='ignore')
                from deeptutor.utils.document_extractor import (
                    _extract_chapter_title,
                    _strip_html_tags_enhanced,
                )

                chapter_title = _extract_chapter_title(content)
                text = _strip_html_tags_enhanced(content)

                if text.strip():
                    if chapter_title:
                        chapters.append(f"--- {chapter_title} ---\n{text}")
                    else:
                        chapters.append(text)

                    # Collect sample for classification
                    if len(sample_text) < 2000:
                        sample_text += text[:2000 - len(sample_text)]

            except Exception as exc:
                logger.warning(f"Failed to extract chapter from {filename}: {exc}")
                continue

        elif item.get_type() == ebooklib.ITEM_IMAGE:
            image_count += 1

    # Add AI classification if enabled
    if enable_classification and sample_text:
        try:
            classification = _classify_content_sync(
                title_str, author_str, language_str, sample_text
            )
            if classification:
                from deeptutor.utils.epub_classifier import format_classification

                result_parts.append(format_classification(classification))
        except Exception as exc:
            logger.warning(f"Classification failed: {exc}")

    # Add chapters
    if chapters:
        result_parts.append("\n\n".join(chapters))

    # Add image analysis if enabled
    if enable_image_analysis and image_count > 0:
        try:
            image_analysis_text = _analyze_images_sync(book)
            if image_analysis_text:
                result_parts.append(image_analysis_text)
        except Exception as exc:
            logger.warning(f"Image analysis failed: {exc}")
    elif image_count > 0:
        result_parts.append(f"\n[This EPUB contains {image_count} embedded images]")

    return "\n\n".join(result_parts)


def _classify_content_sync(
    title: str, author: str, language: str, text_sample: str
) -> Optional[object]:
    """Synchronous wrapper for content classification."""
    try:
        from deeptutor.utils.epub_classifier import EPUBContentClassifier

        classifier = EPUBContentClassifier()
        return classifier.classify_sync(title, author, language, text_sample)
    except Exception as exc:
        logger.error(f"Classification error: {exc}")
        return None


def _analyze_images_sync(epub_book) -> Optional[str]:
    """Synchronous wrapper for image analysis."""
    try:
        from deeptutor.utils.epub_image_analyzer import (
            EPUBImageAnalyzer,
            extract_epub_images,
            format_image_analysis,
        )

        # Extract images
        images = extract_epub_images(epub_book)
        if not images:
            return None

        # Limit to first 5 images to avoid excessive processing
        images_to_analyze = images[:5]

        # Analyze images (synchronous)
        analyzer = EPUBImageAnalyzer()

        # Simple sync processing (full async version would require event loop)
        analysis_results = []
        for image_data, image_name in images_to_analyze:
            # For now, just document image presence
            # Full vision analysis requires async context
            analysis_results.append(f"[Image: {image_name}]")

        if analysis_results:
            header = f"\n=== Image Content ({len(images_to_analyze)} of {len(images)}) ==="
            return header + "\n" + "\n".join(analysis_results)

        return None
    except Exception as exc:
        logger.error(f"Image analysis error: {exc}")
        return None


async def extract_epub_enhanced_async(
    data: bytes,
    filename: str,
    enable_classification: bool = True,
    enable_image_analysis: bool = True,
    enable_caching: bool = True,
    progress_callback=None,
) -> str:
    """Async version with full feature support including vision analysis.

    Args:
        data: EPUB file data
        filename: Name of the EPUB file
        enable_classification: Enable AI content classification
        enable_image_analysis: Enable vision-based image analysis
        enable_caching: Enable performance caching
        progress_callback: Optional progress callback function

    Returns:
        Extracted and enhanced text content
    """
    try:
        import ebooklib
        from ebooklib import epub
    except ImportError:
        from deeptutor.utils.document_extractor import CorruptDocumentError

        raise CorruptDocumentError(
            f"{filename}: ebooklib not installed", filename=filename
        )

    from deeptutor.utils.document_extractor import CorruptDocumentError

    # Parse EPUB
    try:
        book = epub.read_epub(io.BytesIO(data))
    except Exception as exc:
        raise CorruptDocumentError(
            f"{filename}: failed to open EPUB ({exc})", filename=filename
        ) from exc

    # Extract metadata
    title = book.get_metadata('DC', 'title')
    title_str = title[0][0] if title else "Unknown"

    author = book.get_metadata('DC', 'creator')
    author_str = author[0][0] if author else "Unknown"

    language = book.get_metadata('DC', 'language')
    language_str = language[0][0] if language else "en"

    # Use streaming processor for chapters
    if enable_caching:
        from deeptutor.utils.epub_performance import StreamingEPUBProcessor
        from deeptutor.utils.document_extractor import _strip_html_tags_enhanced

        processor = StreamingEPUBProcessor(max_workers=4, enable_cache=True)

        chapters = await processor.process_epub_async(
            book, _strip_html_tags_enhanced, progress_callback
        )
    else:
        # Fallback to simple extraction
        chapters = []
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                try:
                    content = item.get_content().decode('utf-8', errors='ignore')
                    from deeptutor.utils.document_extractor import _strip_html_tags_enhanced

                    text = _strip_html_tags_enhanced(content)
                    if text.strip():
                        chapters.append(text)
                except Exception:
                    continue

    # Build result
    result_parts = [f"=== EPUB Metadata ===\nTitle: {title_str}\nAuthor: {author_str}"]

    # AI Classification
    if enable_classification and chapters:
        sample = chapters[0][:2000] if chapters else ""
        if sample:
            try:
                from deeptutor.utils.epub_classifier import (
                    EPUBContentClassifier,
                    format_classification,
                )

                classifier = EPUBContentClassifier()
                classification = await classifier.classify_epub(
                    title_str, author_str, language_str, sample
                )
                if classification:
                    result_parts.append(format_classification(classification))
            except Exception as exc:
                logger.warning(f"Classification failed: {exc}")

    # Add chapters
    result_parts.extend(chapters)

    # Image Analysis
    if enable_image_analysis:
        try:
            from deeptutor.utils.epub_image_analyzer import (
                EPUBImageAnalyzer,
                extract_epub_images,
                format_image_analysis,
            )

            images = extract_epub_images(book)
            if images:
                analyzer = EPUBImageAnalyzer()
                # Analyze first 3 images
                analyses = await analyzer.analyze_multiple_images(images[:3])

                image_texts = []
                for (_, img_name), analysis in zip(images[:3], analyses):
                    if analysis:
                        image_texts.append(format_image_analysis(analysis, img_name))

                if image_texts:
                    result_parts.append(
                        f"\n=== Image Analysis ({len(image_texts)} of {len(images)}) ===\n"
                        + "\n\n".join(image_texts)
                    )
        except Exception as exc:
            logger.warning(f"Image analysis failed: {exc}")

    return "\n\n".join(result_parts)
