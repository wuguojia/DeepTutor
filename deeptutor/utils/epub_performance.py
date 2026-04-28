"""Advanced performance optimization for EPUB processing.

Provides streaming, parallel processing, caching, and progress tracking
for efficient handling of large EPUB files.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProcessingProgress:
    """Progress information for EPUB processing."""

    total_items: int
    processed_items: int
    current_item: str
    elapsed_time: float
    estimated_remaining: float
    cancelled: bool = False

    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage."""
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100


class EPUBProcessingCache:
    """Cache for EPUB processing results."""

    def __init__(self, cache_dir: Optional[Path] = None, max_size_mb: int = 100):
        """Initialize cache.

        Args:
            cache_dir: Directory for cache storage. None for in-memory only.
            max_size_mb: Maximum cache size in MB
        """
        self.cache_dir = cache_dir
        self.max_size_mb = max_size_mb
        self._memory_cache: dict[str, tuple[str, float]] = {}  # key -> (value, timestamp)
        self._max_memory_items = 50

        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)

    def _compute_key(self, data: bytes, metadata: Optional[dict] = None) -> str:
        """Compute cache key from data and metadata."""
        hasher = hashlib.sha256()
        hasher.update(data)
        if metadata:
            import json

            hasher.update(json.dumps(metadata, sort_keys=True).encode())
        return hasher.hexdigest()

    def get(self, key: str) -> Optional[str]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        # Check memory cache first
        if key in self._memory_cache:
            value, _ = self._memory_cache[key]
            return value

        # Check disk cache
        if self.cache_dir:
            cache_file = self.cache_dir / f"{key}.txt"
            if cache_file.exists():
                try:
                    value = cache_file.read_text(encoding='utf-8')
                    # Add to memory cache
                    self._memory_cache[key] = (value, time.time())
                    self._evict_old_memory_entries()
                    return value
                except Exception as exc:
                    logger.warning(f"Failed to read cache file: {exc}")

        return None

    def set(self, key: str, value: str) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        # Add to memory cache
        self._memory_cache[key] = (value, time.time())
        self._evict_old_memory_entries()

        # Add to disk cache
        if self.cache_dir:
            try:
                cache_file = self.cache_dir / f"{key}.txt"
                cache_file.write_text(value, encoding='utf-8')
                self._check_disk_cache_size()
            except Exception as exc:
                logger.warning(f"Failed to write cache file: {exc}")

    def _evict_old_memory_entries(self) -> None:
        """Evict old entries from memory cache."""
        if len(self._memory_cache) > self._max_memory_items:
            # Sort by timestamp and keep newest
            sorted_items = sorted(
                self._memory_cache.items(), key=lambda x: x[1][1], reverse=True
            )
            self._memory_cache = dict(sorted_items[: self._max_memory_items])

    def _check_disk_cache_size(self) -> None:
        """Check and limit disk cache size."""
        if not self.cache_dir:
            return

        try:
            total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.txt"))
            max_bytes = self.max_size_mb * 1024 * 1024

            if total_size > max_bytes:
                # Delete oldest files
                files = sorted(self.cache_dir.glob("*.txt"), key=lambda f: f.stat().st_mtime)
                for file in files:
                    file.unlink()
                    total_size -= file.stat().st_size
                    if total_size <= max_bytes * 0.8:  # Keep 80% of max
                        break
        except Exception as exc:
            logger.warning(f"Failed to check cache size: {exc}")

    def clear(self) -> None:
        """Clear all cache."""
        self._memory_cache.clear()
        if self.cache_dir and self.cache_dir.exists():
            for file in self.cache_dir.glob("*.txt"):
                try:
                    file.unlink()
                except Exception as exc:
                    logger.warning(f"Failed to delete cache file: {exc}")


class StreamingEPUBProcessor:
    """Process EPUB files with streaming and parallel processing."""

    def __init__(
        self,
        max_workers: int = 4,
        enable_cache: bool = True,
        cache_dir: Optional[Path] = None,
    ):
        """Initialize streaming processor.

        Args:
            max_workers: Maximum parallel workers
            enable_cache: Whether to enable caching
            cache_dir: Directory for cache storage
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.cache = EPUBProcessingCache(cache_dir) if enable_cache else None
        self._cancelled = False

    async def process_epub_async(
        self,
        epub_book,
        processor_func: Callable,
        progress_callback: Optional[Callable[[ProcessingProgress], None]] = None,
    ) -> list[str]:
        """Process EPUB chapters asynchronously with parallel processing.

        Args:
            epub_book: ebooklib EpubBook object
            processor_func: Function to process each chapter
            progress_callback: Optional callback for progress updates

        Returns:
            List of processed chapter texts
        """
        try:
            import ebooklib
            from ebooklib import epub
        except ImportError:
            logger.error("ebooklib not installed")
            return []

        # Collect all document items
        items = [item for item in epub_book.get_items() if item.get_type() == ebooklib.ITEM_DOCUMENT]

        start_time = time.time()
        processed_chapters = []

        # Process chapters in parallel
        tasks = []
        for idx, item in enumerate(items):
            if self._cancelled:
                break

            task = asyncio.create_task(
                self._process_chapter_async(item, processor_func, idx, len(items))
            )
            tasks.append(task)

            # Update progress
            if progress_callback:
                progress = ProcessingProgress(
                    total_items=len(items),
                    processed_items=idx,
                    current_item=item.get_name() or f"chapter_{idx}",
                    elapsed_time=time.time() - start_time,
                    estimated_remaining=self._estimate_remaining_time(
                        idx, len(items), start_time
                    ),
                    cancelled=self._cancelled,
                )
                progress_callback(progress)

        # Gather results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, str) and result:
                processed_chapters.append(result)
            elif isinstance(result, Exception):
                logger.warning(f"Chapter processing failed: {result}")

        return processed_chapters

    async def _process_chapter_async(
        self, item, processor_func: Callable, idx: int, total: int
    ) -> Optional[str]:
        """Process a single chapter asynchronously."""
        try:
            content = item.get_content().decode('utf-8', errors='ignore')

            # Check cache
            if self.cache:
                cache_key = self.cache._compute_key(content.encode(), {'idx': idx})
                cached_result = self.cache.get(cache_key)
                if cached_result:
                    logger.debug(f"Cache hit for chapter {idx}/{total}")
                    return cached_result

            # Process in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(self.executor, processor_func, content)

            # Cache result
            if self.cache and result:
                self.cache.set(cache_key, result)

            return result

        except Exception as exc:
            logger.error(f"Failed to process chapter {idx}: {exc}")
            return None

    def _estimate_remaining_time(self, processed: int, total: int, start_time: float) -> float:
        """Estimate remaining processing time.

        Args:
            processed: Number of items processed
            total: Total items
            start_time: Processing start time

        Returns:
            Estimated remaining seconds
        """
        if processed == 0:
            return 0.0

        elapsed = time.time() - start_time
        avg_time_per_item = elapsed / processed
        remaining_items = total - processed
        return avg_time_per_item * remaining_items

    def cancel(self) -> None:
        """Cancel ongoing processing."""
        self._cancelled = True

    def shutdown(self) -> None:
        """Shutdown the processor and clean up resources."""
        self.executor.shutdown(wait=False)


class ChunkedEPUBReader:
    """Read EPUB content in chunks for memory efficiency."""

    def __init__(self, chunk_size: int = 50000):
        """Initialize chunked reader.

        Args:
            chunk_size: Size of each text chunk in characters
        """
        self.chunk_size = chunk_size

    def read_in_chunks(self, text: str):
        """Yield text in chunks.

        Args:
            text: Full text to chunk

        Yields:
            Text chunks of approximately chunk_size
        """
        start = 0
        text_len = len(text)

        while start < text_len:
            # Try to break at word boundary
            end = start + self.chunk_size
            if end < text_len:
                # Find last space within chunk
                space_pos = text.rfind(' ', start, end)
                if space_pos > start + self.chunk_size // 2:
                    end = space_pos

            yield text[start:end]
            start = end

    async def process_in_chunks(
        self, text: str, chunk_processor: Callable[[str], str]
    ) -> str:
        """Process text in chunks asynchronously.

        Args:
            text: Full text to process
            chunk_processor: Function to process each chunk

        Returns:
            Combined processed text
        """
        processed_chunks = []

        for chunk in self.read_in_chunks(text):
            loop = asyncio.get_event_loop()
            processed = await loop.run_in_executor(None, chunk_processor, chunk)
            processed_chunks.append(processed)

        return "".join(processed_chunks)
