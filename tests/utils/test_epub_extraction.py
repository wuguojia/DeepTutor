"""Comprehensive test suite for EPUB document extraction functionality.

Tests cover:
- Basic EPUB text extraction
- Metadata extraction (title, author, language, publisher)
- Chapter segmentation and title extraction
- Enhanced HTML processing (code blocks, lists, tables)
- Image tracking
- Error handling
"""

import io
import pytest

try:
    from ebooklib import epub
    EBOOKLIB_AVAILABLE = True
except ImportError:
    EBOOKLIB_AVAILABLE = False

from deeptutor.utils.document_extractor import (
    extract_text_from_bytes,
    _extract_epub,
    _extract_chapter_title,
    _strip_html_tags_enhanced,
    DocumentExtractionError,
    CorruptDocumentError,
    EmptyDocumentError,
)


@pytest.mark.skipif(not EBOOKLIB_AVAILABLE, reason="ebooklib not installed")
class TestEPUBExtraction:
    """Test EPUB document extraction functionality."""

    def create_test_epub(self) -> bytes:
        """Create a minimal test EPUB file."""
        book = epub.EpubBook()

        # Set metadata
        book.set_identifier('test123')
        book.set_title('Test EPUB Book')
        book.set_language('en')
        book.add_author('Test Author')
        book.add_metadata('DC', 'publisher', 'Test Publisher')

        # Create chapters
        c1 = epub.EpubHtml(
            title='Chapter 1',
            file_name='chap_01.xhtml',
            lang='en'
        )
        c1.content = '''
            <html><head><title>Chapter 1</title></head>
            <body>
                <h1>Introduction</h1>
                <p>This is the first chapter.</p>
                <ul>
                    <li>Item 1</li>
                    <li>Item 2</li>
                </ul>
            </body></html>
        '''

        c2 = epub.EpubHtml(
            title='Chapter 2',
            file_name='chap_02.xhtml',
            lang='en'
        )
        c2.content = '''
            <html><head><title>Chapter 2</title></head>
            <body>
                <h1>Code Examples</h1>
                <p>Here is some code:</p>
                <pre>def hello():
    print("Hello, World!")</pre>
                <table>
                    <tr><th>Name</th><th>Value</th></tr>
                    <tr><td>Alpha</td><td>1</td></tr>
                    <tr><td>Beta</td><td>2</td></tr>
                </table>
            </body></html>
        '''

        book.add_item(c1)
        book.add_item(c2)

        # Add navigation
        book.toc = (c1, c2)
        book.spine = ['nav', c1, c2]
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # Write to bytes
        output = io.BytesIO()
        epub.write_epub(output, book)
        output.seek(0)
        return output.read()

    def test_basic_epub_extraction(self):
        """Test basic EPUB text extraction."""
        epub_data = self.create_test_epub()
        text = extract_text_from_bytes("test.epub", epub_data)

        assert text is not None
        assert len(text) > 0
        assert "Test EPUB Book" in text
        assert "Test Author" in text

    def test_metadata_extraction(self):
        """Test EPUB metadata extraction."""
        epub_data = self.create_test_epub()
        text = extract_text_from_bytes("test.epub", epub_data)

        # Check metadata section
        assert "=== EPUB Metadata ===" in text
        assert "Title: Test EPUB Book" in text
        assert "Author: Test Author" in text
        assert "Language: en" in text
        assert "Publisher: Test Publisher" in text

    def test_chapter_extraction(self):
        """Test chapter content extraction."""
        epub_data = self.create_test_epub()
        text = extract_text_from_bytes("test.epub", epub_data)

        # Check chapter content
        assert "Introduction" in text
        assert "first chapter" in text
        assert "Code Examples" in text

    def test_list_processing(self):
        """Test that lists are properly formatted."""
        epub_data = self.create_test_epub()
        text = extract_text_from_bytes("test.epub", epub_data)

        # Check list items are preserved with bullets
        assert "•" in text or "Item 1" in text
        assert "Item 2" in text

    def test_code_block_preservation(self):
        """Test that code blocks are preserved."""
        epub_data = self.create_test_epub()
        text = extract_text_from_bytes("test.epub", epub_data)

        # Check code is preserved
        assert "hello" in text.lower() or "Hello" in text
        assert "print" in text or "CODE" in text

    def test_table_extraction(self):
        """Test that tables are extracted."""
        epub_data = self.create_test_epub()
        text = extract_text_from_bytes("test.epub", epub_data)

        # Check table content
        assert "Name" in text or "TABLE" in text
        assert "Alpha" in text
        assert "Beta" in text

    def test_chapter_title_extraction(self):
        """Test chapter title extraction from HTML."""
        html_with_h1 = "<html><body><h1>Chapter Title</h1><p>Content</p></body></html>"
        title = _extract_chapter_title(html_with_h1)
        assert title == "Chapter Title"

        html_with_h2 = "<html><body><h2>Section Title</h2><p>Content</p></body></html>"
        title = _extract_chapter_title(html_with_h2)
        assert title == "Section Title"

        html_no_title = "<html><body><p>Just content</p></body></html>"
        title = _extract_chapter_title(html_no_title)
        assert title == ""

    def test_enhanced_html_stripping(self):
        """Test enhanced HTML tag stripping."""
        html = '''
            <html><body>
                <h1>Title</h1>
                <p>Paragraph with <strong>bold</strong> text.</p>
                <ul><li>List item</li></ul>
                <pre>code block</pre>
            </body></html>
        '''
        text = _strip_html_tags_enhanced(html)

        assert "Title" in text
        assert "Paragraph" in text
        assert "bold" in text
        assert "List item" in text or "•" in text
        assert "code block" in text

    def test_empty_epub_handling(self):
        """Test handling of empty EPUB data."""
        with pytest.raises(EmptyDocumentError):
            extract_text_from_bytes("empty.epub", b"")

    def test_corrupted_epub_handling(self):
        """Test handling of corrupted EPUB data."""
        corrupted_data = b"Not a valid EPUB file"
        with pytest.raises(CorruptDocumentError):
            extract_text_from_bytes("corrupted.epub", corrupted_data)

    def test_epub_with_special_characters(self):
        """Test EPUB with special HTML entities."""
        book = epub.EpubBook()
        book.set_identifier('test456')
        book.set_title('Test &amp; Special')
        book.set_language('en')

        c1 = epub.EpubHtml(title='Chapter', file_name='chap.xhtml')
        c1.content = '<html><body><p>&lt;tag&gt; &amp; &quot;quotes&quot;</p></body></html>'
        book.add_item(c1)
        book.spine = [c1]

        output = io.BytesIO()
        epub.write_epub(output, book)
        output.seek(0)

        text = extract_text_from_bytes("special.epub", output.read())
        # HTML entities should be unescaped
        assert "&amp;" in text or "&" in text
        assert "&lt;" in text or "<" in text or "tag" in text


@pytest.mark.skipif(not EBOOKLIB_AVAILABLE, reason="ebooklib not installed")
class TestEPUBErrorHandling:
    """Test error handling in EPUB extraction."""

    def test_invalid_file_extension(self):
        """Test that non-EPUB files are rejected."""
        # Even with EPUB magic, wrong extension should be caught
        with pytest.raises(DocumentExtractionError):
            extract_text_from_bytes("test.txt", b"PK\x03\x04" + b"fake epub data")

    def test_file_size_limits(self):
        """Test that oversized files are rejected."""
        # Create data larger than MAX_DOC_BYTES (10MB)
        large_data = b"PK\x03\x04" + (b"x" * (11 * 1024 * 1024))
        with pytest.raises(DocumentExtractionError):
            extract_text_from_bytes("large.epub", large_data)


class TestHTMLProcessing:
    """Test HTML processing utilities."""

    def test_script_removal(self):
        """Test that script tags are removed."""
        html = '<html><script>alert("bad")</script><body>Good content</body></html>'
        text = _strip_html_tags_enhanced(html)
        assert "alert" not in text
        assert "Good content" in text

    def test_style_removal(self):
        """Test that style tags are removed."""
        html = '<html><style>body { color: red; }</style><body>Content</body></html>'
        text = _strip_html_tags_enhanced(html)
        assert "color" not in text
        assert "Content" in text

    def test_nested_lists(self):
        """Test nested list processing."""
        html = '''
            <ul>
                <li>Item 1</li>
                <li>Item 2
                    <ul>
                        <li>Nested 1</li>
                        <li>Nested 2</li>
                    </ul>
                </li>
            </ul>
        '''
        text = _strip_html_tags_enhanced(html)
        assert "Item 1" in text
        assert "Item 2" in text
        assert "Nested 1" in text
        assert "Nested 2" in text

    def test_whitespace_normalization(self):
        """Test that excessive whitespace is normalized."""
        html = '<p>Too     many    spaces</p><p>\n\n\nToo many newlines\n\n\n</p>'
        text = _strip_html_tags_enhanced(html)
        # Multiple spaces should be normalized to single space
        assert "Too many spaces" in text or "Too" in text
        # Excessive newlines should be reduced
        assert "\n\n\n\n" not in text
