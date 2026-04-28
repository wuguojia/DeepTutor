# EPUB Document Support in DeepTutor

## Overview

DeepTutor now provides comprehensive support for EPUB (Electronic Publication) documents, a widely-used format for digital books and publications. This document describes the features, usage, and implementation details of EPUB support.

## Features

### 1. **Metadata Extraction**
Automatically extracts and displays rich metadata from EPUB files:
- **Title**: Book title
- **Author**: Author name(s)
- **Language**: Publication language
- **Publisher**: Publisher information
- **Subject**: Subject/category information

### 2. **Enhanced Content Processing**
- **Chapter Segmentation**: Automatically detects and labels chapters with their titles
- **Structure Preservation**: Maintains document structure including:
  - **Code blocks**: Preserved with markers for technical books
  - **Lists**: Converted to bullet points for readability
  - **Tables**: Extracted as tab-separated values
  - **Headings**: Properly hierarchical organization

### 3. **Image Support**
- Tracks embedded images and reports count
- Provides context about visual content in the document

### 4. **Smart HTML Processing**
- Removes scripts and styles while preserving content
- Converts HTML entities to readable text
- Normalizes whitespace intelligently
- Preserves code formatting for technical content

## Usage

### Chat Interface

Simply upload an EPUB file in the chat interface. The system will automatically:
1. Extract the text content
2. Display metadata
3. Process chapter structure
4. Make the content available for conversation

Example:
```bash
# In the chat
User: [Uploads: technical_book.epub]
User: What does this book say about Python decorators?
```

### Knowledge Base (RAG)

Add EPUB files to your knowledge base for long-term reference:

```bash
# Add EPUB to knowledge base
deeptutor kb create my-books --doc book1.epub book2.epub book3.epub

# Query the knowledge base
deeptutor run chat "Summarize the key concepts from the uploaded books" -t rag --kb my-books
```

### Python SDK

```python
from deeptutor.utils.document_extractor import extract_text_from_bytes

# Read EPUB file
with open("book.epub", "rb") as f:
    epub_data = f.read()

# Extract text
text = extract_text_from_bytes("book.epub", epub_data)
print(text)
```

## Technical Details

### File Format
EPUB is a ZIP-based archive format containing:
- XHTML/HTML content files
- CSS stylesheets
- Images and multimedia
- Metadata in XML format

### Processing Pipeline

1. **Validation**: File header verification to prevent spoofing
2. **Parsing**: ebooklib library reads the EPUB structure
3. **Metadata Extraction**: Dublin Core metadata parsed
4. **Content Extraction**:
   - Each chapter (XHTML/HTML) is processed
   - HTML is converted to plain text with structure preservation
   - Chapter titles are extracted from heading tags
5. **Image Tracking**: Count of embedded images is recorded
6. **Assembly**: All parts are combined with clear section markers

### Supported EPUB Versions
- EPUB 2.0
- EPUB 3.0 (with fallback for multimedia content)

### File Size Limits
- Maximum per-file: 10 MB
- Maximum total attachments: 25 MB
- Maximum extracted text per document: 200,000 characters
- Maximum total extracted text per turn: 150,000 characters

## Examples

### Technical Book with Code
```
=== EPUB Metadata ===
Title: Python Programming Guide
Author: Jane Developer
Language: en
Publisher: Tech Books Press

--- Introduction ---
Welcome to Python programming...

--- Chapter 1: Functions ---
Here's a simple function:

[CODE]
def greet(name):
    return f"Hello, {name}!"
[/CODE]

--- Chapter 2: Data Structures ---
Lists in Python:
• Create with square brackets
• Access by index
• Mutable and dynamic

[This EPUB contains 15 embedded images]
```

### Novel or Text-Heavy Book
```
=== EPUB Metadata ===
Title: The Digital Adventure
Author: John Writer
Language: en

--- Chapter 1 ---
The story begins on a rainy afternoon...

--- Chapter 2 ---
As the protagonist ventured forth...

[This EPUB contains 3 embedded images]
```

## Best Practices

### For Users

1. **Use Standard EPUBs**: Ensure your EPUB files follow the standard format
2. **Check File Size**: Keep files under 10 MB for optimal performance
3. **Organize by Topic**: Group related EPUBs in the same knowledge base
4. **DRM-Free**: Only use DRM-free EPUB files (DRM-protected files cannot be processed)

### For Developers

1. **Error Handling**: Always wrap EPUB processing in try-except blocks
2. **Streaming**: For large EPUBs, consider processing chapters incrementally
3. **Metadata**: Check for metadata presence before accessing
4. **Testing**: Use the comprehensive test suite in `tests/utils/test_epub_extraction.py`

## Troubleshooting

### Common Issues

**Issue**: "ebooklib not installed"
**Solution**: Install with `pip install ebooklib>=0.18`

**Issue**: "failed to open EPUB"
**Solution**:
- Verify the file is a valid EPUB (not renamed PDF or other format)
- Check if file is DRM-protected (not supported)
- Ensure file is not corrupted

**Issue**: "no extractable text"
**Solution**:
- File may contain only images (scanned book)
- Check if EPUB has actual text content vs. image-based pages

**Issue**: Extracted text is garbled
**Solution**:
- File may use non-standard encoding
- Try re-saving the EPUB with a standard EPUB editor

### Performance Optimization

For large EPUB collections:
1. Index files during low-traffic periods
2. Use batch processing for multiple files
3. Consider splitting very large EPUBs into volumes
4. Enable caching for frequently accessed content

## Implementation Details

### Key Files

- `deeptutor/utils/document_extractor.py`: Chat attachment extraction
- `deeptutor/services/rag/pipelines/llamaindex/document_loader.py`: RAG pipeline integration
- `deeptutor/services/rag/file_routing.py`: File type classification
- `deeptutor/utils/document_validator.py`: Upload validation
- `tests/utils/test_epub_extraction.py`: Comprehensive test suite

### Dependencies

```toml
# pyproject.toml
[project.optional-dependencies]
cli = [
    "ebooklib>=0.18",  # EPUB parsing
    # ... other dependencies
]
```

## Future Enhancements

Planned improvements for EPUB support:

1. **Full Image Extraction**: Extract and process embedded images with vision models
2. **EPUB3 Multimedia**: Support for audio and video embedded in EPUB3
3. **Advanced Navigation**: Table of contents extraction and navigation
4. **Annotations**: Support for EPUB annotations and highlights
5. **Multi-language**: Enhanced support for non-English EPUBs with better encoding detection
6. **Performance**: Streaming processing for very large EPUBs (>50MB)
7. **Interactive Content**: Support for EPUB3 interactive features
8. **Format Conversion**: Integration with Calibre for other e-book formats (MOBI, AZW3)

## Contributing

To contribute to EPUB support:

1. Review the existing implementation in `document_extractor.py`
2. Add tests to `test_epub_extraction.py`
3. Update this documentation
4. Submit a pull request with clear description of changes

## Resources

- [EPUB Specification](http://idpf.org/epub)
- [ebooklib Documentation](https://github.com/aerkalov/ebooklib)
- [EPUB3 Overview](http://epubzone.org/)

## Support

For issues or questions:
- GitHub Issues: [DeepTutor Issues](https://github.com/wuguojia/DeepTutor/issues)
- Check the troubleshooting section above
- Review test examples in the test suite

---

**Last Updated**: 2026-04-28
**Version**: 1.3.1 with EPUB support
