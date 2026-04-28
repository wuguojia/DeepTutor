"""Tests for advanced EPUB features: AI classification, vision analysis, and performance optimization."""

import asyncio
import pytest

try:
    from ebooklib import epub

    EBOOKLIB_AVAILABLE = True
except ImportError:
    EBOOKLIB_AVAILABLE = False


@pytest.mark.skipif(not EBOOKLIB_AVAILABLE, reason="ebooklib not installed")
class TestEPUBContentClassifier:
    """Test AI-driven content classification."""

    def test_classifier_initialization(self):
        """Test classifier can be initialized."""
        from deeptutor.utils.epub_classifier import EPUBContentClassifier

        classifier = EPUBContentClassifier()
        assert classifier is not None

    def test_classification_prompt_creation(self):
        """Test classification prompt is properly formatted."""
        from deeptutor.utils.epub_classifier import EPUBContentClassifier

        classifier = EPUBContentClassifier()
        prompt = classifier._create_classification_prompt(
            title="Python Guide",
            author="John Doe",
            language="en",
            text_sample="This is a book about Python programming...",
            metadata=None,
        )

        assert "Python Guide" in prompt
        assert "John Doe" in prompt
        assert "Python programming" in prompt
        assert "document_type" in prompt
        assert "difficulty_level" in prompt

    def test_classification_response_parsing(self):
        """Test parsing of classification JSON response."""
        from deeptutor.utils.epub_classifier import EPUBContentClassifier

        classifier = EPUBContentClassifier()

        # Valid JSON response
        response = """{
  "document_type": "technical",
  "topics": ["python", "programming"],
  "difficulty_level": "intermediate",
  "key_concepts": ["functions", "classes"],
  "summary": "A guide to Python programming",
  "language_style": "formal",
  "target_audience": "developers",
  "confidence_score": 0.9
}"""

        result = classifier._parse_classification_response(response)
        assert result is not None
        assert result.document_type == "technical"
        assert "python" in result.topics
        assert result.difficulty_level == "intermediate"
        assert result.confidence_score == 0.9

    def test_classification_response_with_markdown(self):
        """Test parsing response wrapped in markdown code blocks."""
        from deeptutor.utils.epub_classifier import EPUBContentClassifier

        classifier = EPUBContentClassifier()

        response = """```json
{
  "document_type": "fiction",
  "topics": ["adventure"],
  "difficulty_level": "beginner",
  "key_concepts": [],
  "summary": "An adventure story",
  "language_style": "casual",
  "target_audience": "young adults",
  "confidence_score": 0.85
}
```"""

        result = classifier._parse_classification_response(response)
        assert result is not None
        assert result.document_type == "fiction"
        assert result.confidence_score == 0.85

    def test_format_classification(self):
        """Test formatting classification for display."""
        from deeptutor.utils.epub_classifier import EPUBClassification, format_classification

        classification = EPUBClassification(
            document_type="technical",
            topics=["python", "programming", "web"],
            difficulty_level="intermediate",
            key_concepts=["functions", "classes", "decorators"],
            summary="A comprehensive Python guide",
            language_style="formal",
            target_audience="software developers",
            confidence_score=0.92,
        )

        formatted = format_classification(classification)
        assert "Technical" in formatted
        assert "Intermediate" in formatted
        assert "python" in formatted
        assert "functions" in formatted
        assert "92%" in formatted


@pytest.mark.skipif(not EBOOKLIB_AVAILABLE, reason="ebooklib not installed")
class TestEPUBImageAnalyzer:
    """Test vision model integration for image analysis."""

    def test_analyzer_initialization(self):
        """Test image analyzer can be initialized."""
        from deeptutor.utils.epub_image_analyzer import EPUBImageAnalyzer

        analyzer = EPUBImageAnalyzer()
        assert analyzer is not None

    def test_image_format_detection(self):
        """Test image format detection from magic bytes."""
        from deeptutor.utils.epub_image_analyzer import EPUBImageAnalyzer

        analyzer = EPUBImageAnalyzer()

        # JPEG magic bytes
        jpeg_data = b'\xff\xd8\xff\xe0' + b'\x00' * 100
        assert analyzer._detect_image_format(jpeg_data, "test.jpg") == "jpeg"

        # PNG magic bytes
        png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        assert analyzer._detect_image_format(png_data, "test.png") == "png"

        # GIF magic bytes
        gif_data = b'GIF89a' + b'\x00' * 100
        assert analyzer._detect_image_format(gif_data, "test.gif") == "gif"

    def test_analysis_prompt_creation(self):
        """Test image analysis prompt is properly formatted."""
        from deeptutor.utils.epub_image_analyzer import EPUBImageAnalyzer

        analyzer = EPUBImageAnalyzer()
        prompt = analyzer._create_analysis_prompt("diagram.png", "This is about functions")

        assert "analyze" in prompt.lower()
        assert "JSON" in prompt
        assert "description" in prompt
        assert "functions" in prompt

    def test_analysis_response_parsing(self):
        """Test parsing of image analysis response."""
        from deeptutor.utils.epub_image_analyzer import EPUBImageAnalyzer

        analyzer = EPUBImageAnalyzer()

        response = """{
  "description": "A diagram showing function flow",
  "image_type": "diagram",
  "contains_text": true,
  "extracted_text": "Function A -> Function B",
  "educational_value": "high",
  "caption": "Function call flow diagram"
}"""

        result = analyzer._parse_analysis_response(response)
        assert result is not None
        assert result.description == "A diagram showing function flow"
        assert result.image_type == "diagram"
        assert result.contains_text is True
        assert "Function A" in result.extracted_text
        assert result.educational_value == "high"

    def test_extract_epub_images(self):
        """Test extraction of images from EPUB."""
        from deeptutor.utils.epub_image_analyzer import extract_epub_images
        import io

        # Create a minimal EPUB with an image
        book = epub.EpubBook()
        book.set_identifier('test123')
        book.set_title('Test Book')

        # Add a fake image
        image_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        image = epub.EpubImage()
        image.file_name = 'test.png'
        image.content = image_data
        book.add_item(image)

        images = extract_epub_images(book)
        assert len(images) == 1
        assert images[0][1] == 'test.png'

    def test_format_image_analysis(self):
        """Test formatting image analysis for display."""
        from deeptutor.utils.epub_image_analyzer import ImageAnalysis, format_image_analysis

        analysis = ImageAnalysis(
            description="A code diagram showing class hierarchy",
            image_type="diagram",
            contains_text=True,
            extracted_text="BaseClass -> SubClass",
            educational_value="high",
            caption="Class inheritance diagram",
        )

        formatted = format_image_analysis(analysis, "diagram1.png")
        assert "diagram1.png" in formatted
        assert "Class inheritance diagram" in formatted
        assert "Diagram" in formatted
        assert "class hierarchy" in formatted
        assert "High" in formatted


@pytest.mark.skipif(not EBOOKLIB_AVAILABLE, reason="ebooklib not installed")
class TestEPUBPerformanceOptimization:
    """Test performance optimization features."""

    def test_cache_initialization(self):
        """Test cache can be initialized."""
        from deeptutor.utils.epub_performance import EPUBProcessingCache

        cache = EPUBProcessingCache()
        assert cache is not None

    def test_cache_set_and_get(self):
        """Test basic cache operations."""
        from deeptutor.utils.epub_performance import EPUBProcessingCache

        cache = EPUBProcessingCache()

        # Set and retrieve
        cache.set("test_key", "test_value")
        value = cache.get("test_key")
        assert value == "test_value"

        # Non-existent key
        assert cache.get("nonexistent") is None

    def test_cache_key_computation(self):
        """Test cache key computation from data."""
        from deeptutor.utils.epub_performance import EPUBProcessingCache

        cache = EPUBProcessingCache()

        # Same data should produce same key
        data = b"test data"
        key1 = cache._compute_key(data)
        key2 = cache._compute_key(data)
        assert key1 == key2

        # Different data should produce different keys
        key3 = cache._compute_key(b"different data")
        assert key1 != key3

    def test_streaming_processor_initialization(self):
        """Test streaming processor initialization."""
        from deeptutor.utils.epub_performance import StreamingEPUBProcessor

        processor = StreamingEPUBProcessor(max_workers=2)
        assert processor is not None
        assert processor.max_workers == 2

    def test_progress_tracking(self):
        """Test progress tracking calculations."""
        from deeptutor.utils.epub_performance import ProcessingProgress

        progress = ProcessingProgress(
            total_items=100,
            processed_items=25,
            current_item="chapter_25",
            elapsed_time=10.0,
            estimated_remaining=30.0,
        )

        assert progress.progress_percent == 25.0
        assert progress.current_item == "chapter_25"

    def test_chunked_reader(self):
        """Test chunked text reading."""
        from deeptutor.utils.epub_performance import ChunkedEPUBReader

        reader = ChunkedEPUBReader(chunk_size=100)
        text = "a" * 250

        chunks = list(reader.read_in_chunks(text))
        assert len(chunks) >= 2
        assert sum(len(c) for c in chunks) == len(text)

    @pytest.mark.asyncio
    async def test_async_epub_processing(self):
        """Test async EPUB processing with streaming."""
        from deeptutor.utils.epub_performance import StreamingEPUBProcessor
        import io

        # Create a test EPUB
        book = epub.EpubBook()
        book.set_identifier('test456')
        book.set_title('Test Book')

        # Add chapters
        for i in range(3):
            chapter = epub.EpubHtml(
                title=f'Chapter {i}', file_name=f'chap_{i}.xhtml', lang='en'
            )
            chapter.content = f'<html><body><p>Chapter {i} content</p></body></html>'
            book.add_item(chapter)

        # Process
        processor = StreamingEPUBProcessor(max_workers=2, enable_cache=False)

        def simple_processor(content: str) -> str:
            return content[:100]  # Simple truncation

        results = await processor.process_epub_async(book, simple_processor)
        assert len(results) == 3


@pytest.mark.skipif(not EBOOKLIB_AVAILABLE, reason="ebooklib not installed")
class TestEnhancedEPUBExtraction:
    """Test integrated enhanced EPUB extraction."""

    def test_enhanced_extraction_basic(self):
        """Test basic enhanced extraction without AI features."""
        from deeptutor.utils.epub_enhanced import extract_epub_enhanced
        import io

        # Create a simple EPUB
        book = epub.EpubBook()
        book.set_identifier('test789')
        book.set_title('Test Book')
        book.set_language('en')
        book.add_author('Test Author')

        chapter = epub.EpubHtml(title='Chapter 1', file_name='chap_01.xhtml')
        chapter.content = '<html><body><h1>Introduction</h1><p>Test content</p></body></html>'
        book.add_item(chapter)
        book.spine = [chapter]

        # Write to bytes
        output = io.BytesIO()
        epub.write_epub(output, book)
        epub_data = output.getvalue()

        # Extract (without AI features)
        text = extract_epub_enhanced(
            epub_data,
            "test.epub",
            enable_classification=False,
            enable_image_analysis=False,
        )

        assert "Test Book" in text
        assert "Test Author" in text
        assert "Introduction" in text
        assert "Test content" in text

    @pytest.mark.asyncio
    async def test_enhanced_extraction_async(self):
        """Test async enhanced extraction."""
        from deeptutor.utils.epub_enhanced import extract_epub_enhanced_async
        import io

        # Create a simple EPUB
        book = epub.EpubBook()
        book.set_identifier('test999')
        book.set_title('Async Test Book')
        book.add_author('Async Author')

        chapter = epub.EpubHtml(title='Chapter', file_name='chap.xhtml')
        chapter.content = '<html><body><p>Async content</p></body></html>'
        book.add_item(chapter)
        book.spine = [chapter]

        output = io.BytesIO()
        epub.write_epub(output, book)
        epub_data = output.getvalue()

        # Extract asynchronously (without AI to avoid external dependencies)
        text = await extract_epub_enhanced_async(
            epub_data,
            "test.epub",
            enable_classification=False,
            enable_image_analysis=False,
            enable_caching=True,
        )

        assert "Async Test Book" in text
        assert "Async content" in text
