"""Vision model integration for EPUB image analysis.

Extracts and analyzes images from EPUB files using vision models to provide
rich descriptions and context about visual content.
"""

from __future__ import annotations

import base64
import io
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ImageAnalysis:
    """Analysis result for an image."""

    description: str  # Detailed description of the image
    image_type: str  # 'diagram', 'photo', 'chart', 'illustration', 'screenshot', 'map'
    contains_text: bool  # Whether image contains readable text
    extracted_text: str  # OCR text if available
    educational_value: str  # 'high', 'medium', 'low'
    caption: Optional[str] = None  # Generated caption


class EPUBImageAnalyzer:
    """Analyze images from EPUB using vision models."""

    def __init__(self, vision_client=None, vision_model: Optional[str] = None):
        """Initialize image analyzer with optional vision client.

        Args:
            vision_client: Vision-capable LLM client. If None, will be lazy-loaded.
            vision_model: Specific model to use for vision tasks. If None, uses config default.
        """
        self.vision_client = vision_client
        self.vision_model = vision_model
        self._vision_loaded = False

    def _ensure_vision_client(self):
        """Lazy load vision client if not provided."""
        if self.vision_client is None and not self._vision_loaded:
            try:
                from deeptutor.services.llm.multimodal import get_vision_client

                self.vision_client = get_vision_client()
                self._vision_loaded = True

                # Get vision model from config if not specified
                if self.vision_model is None:
                    from deeptutor.services.llm.config import get_llm_config
                    try:
                        llm_config = get_llm_config()
                        self.vision_model = llm_config.get_vision_model()
                    except Exception:
                        pass  # Will use client's default model
            except Exception as exc:
                logger.warning(f"Failed to load vision client: {exc}")
                self._vision_loaded = True

    async def analyze_image(
        self, image_data: bytes, image_name: str, context: Optional[str] = None
    ) -> Optional[ImageAnalysis]:
        """Analyze an image using vision models.

        Args:
            image_data: Raw image bytes
            image_name: Name/filename of the image
            context: Optional context about where the image appears

        Returns:
            ImageAnalysis object or None if analysis fails
        """
        self._ensure_vision_client()

        if self.vision_client is None:
            logger.warning("Vision client not available, skipping image analysis")
            return None

        try:
            # Encode image as base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')

            # Determine image format
            image_format = self._detect_image_format(image_data, image_name)

            # Create analysis prompt
            prompt = self._create_analysis_prompt(image_name, context)

            # Call vision model
            response = await self._call_vision_model(image_base64, image_format, prompt)

            if response:
                return self._parse_analysis_response(response)

        except Exception as exc:
            logger.error(f"Image analysis failed for {image_name}: {exc}")

        return None

    def _detect_image_format(self, image_data: bytes, image_name: str) -> str:
        """Detect image format from data or filename.

        Args:
            image_data: Raw image bytes
            image_name: Image filename

        Returns:
            Image format ('jpeg', 'png', 'gif', 'webp', etc.)
        """
        # Check magic bytes
        if image_data.startswith(b'\xff\xd8\xff'):
            return 'jpeg'
        elif image_data.startswith(b'\x89PNG'):
            return 'png'
        elif image_data.startswith(b'GIF'):
            return 'gif'
        elif image_data.startswith(b'RIFF') and b'WEBP' in image_data[:20]:
            return 'webp'

        # Fallback to extension
        ext = image_name.lower().split('.')[-1]
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp']:
            return ext

        return 'jpeg'  # Default

    def _create_analysis_prompt(self, image_name: str, context: Optional[str]) -> str:
        """Create prompt for vision model analysis."""
        prompt = """Analyze this image from an educational book and provide:

1. A detailed description of what you see
2. The type of image (diagram, photo, chart, illustration, screenshot, map, etc.)
3. Whether it contains readable text (yes/no)
4. Any text visible in the image (OCR)
5. Educational value (high/medium/low)
6. A concise caption suitable for accessibility

Respond in JSON format:
{
  "description": "detailed description",
  "image_type": "diagram",
  "contains_text": true,
  "extracted_text": "text from image",
  "educational_value": "high",
  "caption": "brief caption"
}"""

        if context:
            prompt += f"\n\nContext: This image appears in a section about: {context}"

        return prompt

    async def _call_vision_model(
        self, image_base64: str, image_format: str, prompt: str
    ) -> Optional[str]:
        """Call vision model with the image and prompt."""
        try:
            # Prepare image message
            image_url = f"data:image/{image_format};base64,{image_base64}"

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ]

            # Prepare model kwargs if vision_model is specified
            model_kwargs = {}
            if self.vision_model:
                model_kwargs['model'] = self.vision_model

            # Call vision client
            if hasattr(self.vision_client, 'create_completion'):
                response = await self.vision_client.create_completion(
                    messages=messages, temperature=0.3, max_tokens=800, **model_kwargs
                )
                return response.get('content', '')
            elif hasattr(self.vision_client, 'chat'):
                response = await self.vision_client.chat(
                    messages=messages, temperature=0.3, **model_kwargs
                )
                return response.get('content', '')
            else:
                logger.warning("Vision client has no recognized completion method")
                return None

        except Exception as exc:
            logger.error(f"Vision model call failed: {exc}")
            return None

    def _parse_analysis_response(self, response: str) -> Optional[ImageAnalysis]:
        """Parse vision model response into ImageAnalysis object."""
        try:
            import json

            # Extract JSON from response
            json_str = response.strip()
            if json_str.startswith('```json'):
                json_str = json_str[7:]
            if json_str.startswith('```'):
                json_str = json_str[3:]
            if json_str.endswith('```'):
                json_str = json_str[:-3]

            data = json.loads(json_str.strip())

            return ImageAnalysis(
                description=data.get('description', 'No description available'),
                image_type=data.get('image_type', 'image'),
                contains_text=data.get('contains_text', False),
                extracted_text=data.get('extracted_text', ''),
                educational_value=data.get('educational_value', 'medium'),
                caption=data.get('caption'),
            )
        except json.JSONDecodeError as exc:
            logger.error(f"Failed to parse image analysis JSON: {exc}")
            return None
        except Exception as exc:
            logger.error(f"Failed to create ImageAnalysis object: {exc}")
            return None

    async def analyze_multiple_images(
        self, images: list[tuple[bytes, str]], context: Optional[str] = None
    ) -> list[ImageAnalysis]:
        """Analyze multiple images in parallel.

        Args:
            images: List of (image_data, image_name) tuples
            context: Optional context for all images

        Returns:
            List of ImageAnalysis objects (None for failed analyses)
        """
        import asyncio

        tasks = [
            self.analyze_image(image_data, image_name, context)
            for image_data, image_name in images
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [r if isinstance(r, ImageAnalysis) else None for r in results]


def format_image_analysis(analysis: ImageAnalysis, image_name: str) -> str:
    """Format image analysis as readable text.

    Args:
        analysis: ImageAnalysis object
        image_name: Name of the image

    Returns:
        Formatted string representation
    """
    lines = [f"[Image: {image_name}]"]

    if analysis.caption:
        lines.append(f"Caption: {analysis.caption}")

    lines.append(f"Type: {analysis.image_type.title()}")
    lines.append(f"Description: {analysis.description}")

    if analysis.contains_text and analysis.extracted_text:
        lines.append(f"Text in image: {analysis.extracted_text}")

    lines.append(f"Educational value: {analysis.educational_value.title()}")

    return "\n".join(lines)


def extract_epub_images(epub_book) -> list[tuple[bytes, str]]:
    """Extract all images from an EPUB book.

    Args:
        epub_book: ebooklib EpubBook object

    Returns:
        List of (image_data, image_name) tuples
    """
    try:
        import ebooklib
        from ebooklib import epub
    except ImportError:
        logger.error("ebooklib not installed")
        return []

    images = []
    for item in epub_book.get_items():
        if item.get_type() == ebooklib.ITEM_IMAGE:
            try:
                image_data = item.get_content()
                image_name = item.get_name() or f"image_{len(images)}"
                images.append((image_data, image_name))
            except Exception as exc:
                logger.warning(f"Failed to extract image: {exc}")
                continue

    return images
