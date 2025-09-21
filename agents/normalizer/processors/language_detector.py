"""
Language detection processor for the Normalizer Agent.

This module provides functionality to detect the language of
feedback content and filter by language if needed.
"""

import re
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class LanguageDetector:
    """Language detection utility for feedback content."""
    
    def __init__(self, default_language: str = "en"):
        self.default_language = default_language
        
        # Common language patterns
        self.language_patterns = {
            'en': {
                'common_words': ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'],
                'patterns': [r'\b(?:the|and|or|but|in|on|at|to|for|of|with|by)\b']
            },
            'es': {
                'common_words': ['el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le'],
                'patterns': [r'\b(?:el|la|de|que|y|a|en|un|es|se|no|te|lo|le)\b']
            },
            'fr': {
                'common_words': ['le', 'de', 'et', 'à', 'un', 'il', 'être', 'et', 'en', 'avoir', 'que', 'pour', 'dans'],
                'patterns': [r'\b(?:le|de|et|à|un|il|être|en|avoir|que|pour|dans)\b']
            },
            'de': {
                'common_words': ['der', 'die', 'das', 'und', 'in', 'den', 'von', 'zu', 'dem', 'mit', 'sich', 'nicht'],
                'patterns': [r'\b(?:der|die|das|und|in|den|von|zu|dem|mit|sich|nicht)\b']
            },
            'it': {
                'common_words': ['il', 'di', 'che', 'e', 'la', 'per', 'con', 'un', 'in', 'da', 'del', 'della', 'dei'],
                'patterns': [r'\b(?:il|di|che|e|la|per|con|un|in|da|del|della|dei)\b']
            },
            'pt': {
                'common_words': ['o', 'de', 'e', 'do', 'da', 'em', 'um', 'para', 'com', 'não', 'uma', 'os', 'as'],
                'patterns': [r'\b(?:o|de|e|do|da|em|um|para|com|não|uma|os|as)\b']
            }
        }
    
    def detect_language(self, text: str) -> Dict[str, Any]:
        """
        Detect the language of text content.
        
        Args:
            text: Text content to analyze
            
        Returns:
            Dictionary with language detection results
        """
        if not text:
            return {
                'language': self.default_language,
                'confidence': 0.0,
                'method': 'default'
            }
        
        # Clean and normalize text
        cleaned_text = self._clean_text(text)
        
        if not cleaned_text:
            return {
                'language': self.default_language,
                'confidence': 0.0,
                'method': 'default'
            }
        
        # Try different detection methods
        results = []
        
        # Method 1: Common word frequency
        word_freq_result = self._detect_by_word_frequency(cleaned_text)
        if word_freq_result:
            results.append(word_freq_result)
        
        # Method 2: Character pattern analysis
        char_pattern_result = self._detect_by_character_patterns(cleaned_text)
        if char_pattern_result:
            results.append(char_pattern_result)
        
        # Method 3: URL and domain analysis
        url_result = self._detect_by_urls(text)
        if url_result:
            results.append(url_result)
        
        # Combine results
        if results:
            best_result = max(results, key=lambda x: x['confidence'])
            return best_result
        else:
            return {
                'language': self.default_language,
                'confidence': 0.5,
                'method': 'fallback'
            }
    
    def _clean_text(self, text: str) -> str:
        """Clean text for language detection."""
        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)
        
        # Remove special characters but keep spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip().lower()
    
    def _detect_by_word_frequency(self, text: str) -> Optional[Dict[str, Any]]:
        """Detect language by analyzing common word frequency."""
        words = text.split()
        if len(words) < 3:
            return None
        
        language_scores = {}
        
        for lang, patterns in self.language_patterns.items():
            score = 0
            total_words = len(words)
            
            for word in words:
                if word in patterns['common_words']:
                    score += 1
            
            # Calculate confidence based on word frequency
            confidence = score / total_words if total_words > 0 else 0
            language_scores[lang] = confidence
        
        if language_scores:
            best_lang = max(language_scores, key=language_scores.get)
            best_score = language_scores[best_lang]
            
            if best_score > 0.1:  # Minimum threshold
                return {
                    'language': best_lang,
                    'confidence': min(best_score, 1.0),
                    'method': 'word_frequency'
                }
        
        return None
    
    def _detect_by_character_patterns(self, text: str) -> Optional[Dict[str, Any]]:
        """Detect language by analyzing character patterns."""
        if len(text) < 10:
            return None
        
        # Character frequency analysis
        char_freq = {}
        for char in text:
            char_freq[char] = char_freq.get(char, 0) + 1
        
        total_chars = len(text)
        
        # Language-specific character patterns
        patterns = {
            'en': {'a': 0.08, 'e': 0.13, 'i': 0.07, 'o': 0.08, 'u': 0.03},
            'es': {'a': 0.12, 'e': 0.14, 'i': 0.06, 'o': 0.09, 'u': 0.05},
            'fr': {'a': 0.08, 'e': 0.15, 'i': 0.07, 'o': 0.05, 'u': 0.06},
            'de': {'a': 0.07, 'e': 0.16, 'i': 0.08, 'o': 0.03, 'u': 0.05}
        }
        
        language_scores = {}
        
        for lang, expected_freq in patterns.items():
            score = 0
            for char, expected in expected_freq.items():
                actual = char_freq.get(char, 0) / total_chars
                # Calculate similarity to expected frequency
                similarity = 1 - abs(actual - expected) / expected
                score += similarity
            
            language_scores[lang] = score / len(expected_freq)
        
        if language_scores:
            best_lang = max(language_scores, key=language_scores.get)
            best_score = language_scores[best_lang]
            
            if best_score > 0.6:  # Minimum threshold
                return {
                    'language': best_lang,
                    'confidence': min(best_score, 1.0),
                    'method': 'character_patterns'
                }
        
        return None
    
    def _detect_by_urls(self, text: str) -> Optional[Dict[str, Any]]:
        """Detect language by analyzing URLs in text."""
        # Extract URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        
        if not urls:
            return None
        
        # Analyze URL patterns for language hints
        language_hints = {
            '.com': 'en',
            '.org': 'en',
            '.net': 'en',
            '.co.uk': 'en',
            '.fr': 'fr',
            '.de': 'de',
            '.es': 'es',
            '.it': 'it',
            '.pt': 'pt'
        }
        
        detected_langs = []
        for url in urls:
            for domain, lang in language_hints.items():
                if domain in url:
                    detected_langs.append(lang)
        
        if detected_langs:
            # Return most common language
            most_common = max(set(detected_langs), key=detected_langs.count)
            confidence = detected_langs.count(most_common) / len(detected_langs)
            
            return {
                'language': most_common,
                'confidence': confidence,
                'method': 'url_analysis'
            }
        
        return None
    
    def filter_by_language(self, items: List[Dict[str, Any]], target_language: str = "en") -> List[Dict[str, Any]]:
        """
        Filter items by language.
        
        Args:
            items: List of feedback items
            target_language: Target language to keep
            
        Returns:
            Filtered list of items
        """
        filtered_items = []
        
        for item in items:
            # Detect language
            lang_result = self.detect_language(
                f"{item.get('title', '')} {item.get('content', '')}"
            )
            
            # Keep items in target language or with low confidence
            if (lang_result['language'] == target_language or 
                lang_result['confidence'] < 0.3):
                item['detected_language'] = lang_result['language']
                item['language_confidence'] = lang_result['confidence']
                filtered_items.append(item)
        
        return filtered_items
    
    def get_language_stats(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get language distribution statistics.
        
        Args:
            items: List of feedback items
            
        Returns:
            Dictionary with language statistics
        """
        language_counts = {}
        confidence_scores = []
        
        for item in items:
            lang_result = self.detect_language(
                f"{item.get('title', '')} {item.get('content', '')}"
            )
            
            lang = lang_result['language']
            confidence = lang_result['confidence']
            
            language_counts[lang] = language_counts.get(lang, 0) + 1
            confidence_scores.append(confidence)
        
        return {
            'language_distribution': language_counts,
            'total_items': len(items),
            'average_confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
            'most_common_language': max(language_counts, key=language_counts.get) if language_counts else 'unknown'
        }
