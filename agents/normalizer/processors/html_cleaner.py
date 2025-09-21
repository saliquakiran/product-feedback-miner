"""
HTML cleaning processor for the Normalizer Agent.

This module provides functionality to clean HTML content and extract
plain text while preserving important formatting.
"""

import re
from bs4 import BeautifulSoup
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class HTMLCleaner:
    """HTML cleaning utility for feedback content."""
    
    def __init__(self):
        self.soup_parser = "html.parser"
        
    def clean_html(self, html_content: str) -> str:
        """
        Clean HTML content and extract plain text.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            Cleaned plain text content
        """
        if not html_content:
            return ""
        
        try:
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, self.soup_parser)
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up whitespace
            text = self._clean_whitespace(text)
            
            # Preserve line breaks from block elements
            text = self._preserve_line_breaks(html_content, text)
            
            return text.strip()
            
        except Exception as e:
            logger.warning(f"HTML cleaning failed: {e}")
            # Fallback to basic HTML tag removal
            return self._basic_html_clean(html_content)
    
    def _clean_whitespace(self, text: str) -> str:
        """Clean up excessive whitespace."""
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Replace multiple newlines with double newline
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        return text
    
    def _preserve_line_breaks(self, original_html: str, cleaned_text: str) -> str:
        """Preserve important line breaks from block elements."""
        # Add line breaks after block elements
        block_elements = ['p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']
        
        for element in block_elements:
            # Add line break after closing tags
            pattern = f'</{element}>'
            cleaned_text = re.sub(pattern, f'</{element}>\n', cleaned_text)
        
        return cleaned_text
    
    def _basic_html_clean(self, html_content: str) -> str:
        """Basic HTML cleaning as fallback."""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_content)
        
        # Decode HTML entities
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        text = text.replace('&nbsp;', ' ')
        
        # Clean whitespace
        text = self._clean_whitespace(text)
        
        return text.strip()
    
    def extract_links(self, html_content: str) -> list:
        """
        Extract links from HTML content.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            List of extracted links
        """
        if not html_content:
            return []
        
        try:
            soup = BeautifulSoup(html_content, self.soup_parser)
            links = []
            
            for link in soup.find_all('a', href=True):
                links.append({
                    'url': link['href'],
                    'text': link.get_text().strip()
                })
            
            return links
            
        except Exception as e:
            logger.warning(f"Link extraction failed: {e}")
            return []
    
    def extract_images(self, html_content: str) -> list:
        """
        Extract image information from HTML content.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            List of extracted images
        """
        if not html_content:
            return []
        
        try:
            soup = BeautifulSoup(html_content, self.soup_parser)
            images = []
            
            for img in soup.find_all('img', src=True):
                images.append({
                    'src': img['src'],
                    'alt': img.get('alt', ''),
                    'title': img.get('title', '')
                })
            
            return images
            
        except Exception as e:
            logger.warning(f"Image extraction failed: {e}")
            return []
    
    def clean_title(self, title: str) -> str:
        """
        Clean HTML from titles.
        
        Args:
            title: Raw title content
            
        Returns:
            Cleaned title
        """
        if not title:
            return ""
        
        # Remove HTML tags
        cleaned = self.clean_html(title)
        
        # Limit title length
        if len(cleaned) > 200:
            cleaned = cleaned[:200] + "..."
        
        return cleaned.strip()
