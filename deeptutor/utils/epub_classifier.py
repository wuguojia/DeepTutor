"""AI-driven EPUB content classification.

Uses LLM to analyze and classify EPUB content for better organization,
search, and personalized learning experiences.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class EPUBClassification:
    """Classification result for an EPUB document."""

    document_type: str  # 'technical', 'fiction', 'academic', 'reference', 'textbook'
    topics: list[str]  # Main topics covered
    difficulty_level: str  # 'beginner', 'intermediate', 'advanced', 'expert'
    key_concepts: list[str]  # Important concepts identified
    summary: str  # Brief summary of the content
    language_style: str  # 'formal', 'casual', 'academic', 'conversational'
    target_audience: str  # Who the book is for
    confidence_score: float  # 0.0 to 1.0


class EPUBContentClassifier:
    """AI-powered EPUB content classifier using LLM."""

    def __init__(self, llm_client=None):
        """Initialize classifier with optional LLM client.

        Args:
            llm_client: LLM client instance. If None, will be lazy-loaded.
        """
        self.llm_client = llm_client
        self._llm_loaded = False

    def _ensure_llm_client(self):
        """Lazy load LLM client if not provided."""
        if self.llm_client is None and not self._llm_loaded:
            try:
                from deeptutor.services.llm.client import LLMClient
                from deeptutor.services.config.loader import load_config

                config = load_config()
                self.llm_client = LLMClient(config)
                self._llm_loaded = True
            except Exception as exc:
                logger.warning(f"Failed to load LLM client: {exc}")
                self._llm_loaded = True  # Mark as attempted

    async def classify_epub(
        self,
        title: str,
        author: str,
        language: str,
        text_sample: str,
        metadata: Optional[dict] = None,
    ) -> Optional[EPUBClassification]:
        """Classify EPUB content using AI.

        Args:
            title: Book title
            author: Book author
            language: Book language
            text_sample: Sample text from the book (first ~2000 chars)
            metadata: Additional metadata

        Returns:
            EPUBClassification object or None if classification fails
        """
        self._ensure_llm_client()

        if self.llm_client is None:
            logger.warning("LLM client not available, skipping classification")
            return None

        # Prepare classification prompt
        prompt = self._create_classification_prompt(
            title, author, language, text_sample, metadata
        )

        try:
            # Call LLM for classification
            response = await self._call_llm(prompt)
            if response:
                return self._parse_classification_response(response)
        except Exception as exc:
            logger.error(f"Classification failed: {exc}")

        return None

    def _create_classification_prompt(
        self,
        title: str,
        author: str,
        language: str,
        text_sample: str,
        metadata: Optional[dict],
    ) -> str:
        """Create prompt for LLM classification."""
        prompt = f"""Analyze and classify the following book based on its metadata and content sample.

Book Information:
- Title: {title}
- Author: {author}
- Language: {language}

Content Sample (first 2000 characters):
{text_sample[:2000]}

Please provide a detailed classification in JSON format with the following fields:

{{
  "document_type": "one of: technical, fiction, academic, reference, textbook, novel, biography, self-help",
  "topics": ["list", "of", "main", "topics"],
  "difficulty_level": "one of: beginner, intermediate, advanced, expert",
  "key_concepts": ["important", "concepts", "identified"],
  "summary": "Brief 2-3 sentence summary of the content",
  "language_style": "one of: formal, casual, academic, conversational, professional",
  "target_audience": "who this book is for",
  "confidence_score": 0.85
}}

Respond ONLY with valid JSON, no additional text."""

        return prompt

    async def _call_llm(self, prompt: str) -> Optional[str]:
        """Call LLM with the classification prompt."""
        try:
            # Try to use the LLM client's completion method
            if hasattr(self.llm_client, 'create_completion'):
                response = await self.llm_client.create_completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,  # Lower temperature for more consistent classification
                    max_tokens=1000,
                )
                return response.get('content', '')
            elif hasattr(self.llm_client, 'chat'):
                response = await self.llm_client.chat(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                )
                return response.get('content', '')
            else:
                logger.warning("LLM client has no recognized completion method")
                return None
        except Exception as exc:
            logger.error(f"LLM call failed: {exc}")
            return None

    def _parse_classification_response(self, response: str) -> Optional[EPUBClassification]:
        """Parse LLM response into EPUBClassification object."""
        try:
            # Extract JSON from response (might have markdown code blocks)
            json_str = response.strip()
            if json_str.startswith('```json'):
                json_str = json_str[7:]
            if json_str.startswith('```'):
                json_str = json_str[3:]
            if json_str.endswith('```'):
                json_str = json_str[:-3]

            data = json.loads(json_str.strip())

            return EPUBClassification(
                document_type=data.get('document_type', 'unknown'),
                topics=data.get('topics', []),
                difficulty_level=data.get('difficulty_level', 'intermediate'),
                key_concepts=data.get('key_concepts', []),
                summary=data.get('summary', ''),
                language_style=data.get('language_style', 'formal'),
                target_audience=data.get('target_audience', 'general readers'),
                confidence_score=float(data.get('confidence_score', 0.5)),
            )
        except json.JSONDecodeError as exc:
            logger.error(f"Failed to parse classification JSON: {exc}")
            logger.debug(f"Response was: {response}")
            return None
        except Exception as exc:
            logger.error(f"Failed to create classification object: {exc}")
            return None

    def classify_sync(
        self,
        title: str,
        author: str,
        language: str,
        text_sample: str,
        metadata: Optional[dict] = None,
    ) -> Optional[EPUBClassification]:
        """Synchronous wrapper for classify_epub.

        Args:
            title: Book title
            author: Book author
            language: Book language
            text_sample: Sample text from the book
            metadata: Additional metadata

        Returns:
            EPUBClassification object or None
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in async context, create new loop
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.classify_epub(title, author, language, text_sample, metadata),
                    )
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(
                    self.classify_epub(title, author, language, text_sample, metadata)
                )
        except Exception as exc:
            logger.error(f"Sync classification failed: {exc}")
            return None


def format_classification(classification: EPUBClassification) -> str:
    """Format classification as readable text for inclusion in extracted content.

    Args:
        classification: EPUBClassification object

    Returns:
        Formatted string representation
    """
    lines = [
        "=== AI Content Classification ===",
        f"Type: {classification.document_type.title()}",
        f"Difficulty: {classification.difficulty_level.title()}",
        f"Target Audience: {classification.target_audience}",
        f"Language Style: {classification.language_style.title()}",
    ]

    if classification.topics:
        lines.append(f"Topics: {', '.join(classification.topics[:5])}")

    if classification.key_concepts:
        lines.append(f"Key Concepts: {', '.join(classification.key_concepts[:8])}")

    if classification.summary:
        lines.append(f"\nSummary: {classification.summary}")

    lines.append(f"\n(Classification confidence: {classification.confidence_score:.0%})")

    return "\n".join(lines)
