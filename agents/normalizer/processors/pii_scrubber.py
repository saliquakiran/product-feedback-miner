"""
PII (Personally Identifiable Information) scrubbing processor.

This module provides functionality to detect and remove PII from
feedback content to protect user privacy.
"""

import re
from typing import List, Dict, Any, Optional, Set, Tuple
import logging

logger = logging.getLogger(__name__)

class PIIScrubber:
    """PII scrubbing utility for feedback content."""
    
    def __init__(self):
        # Email pattern
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )
        
        # Phone number patterns
        self.phone_patterns = [
            re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),  # US format
            re.compile(r'\b\(\d{3}\)\s*\d{3}[-.]?\d{4}\b'),  # US format with parentheses
            re.compile(r'\b\+1[-.]?\d{3}[-.]?\d{3}[-.]?\d{4}\b'),  # International
        ]
        
        # Credit card patterns
        self.credit_card_pattern = re.compile(
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
        )
        
        # SSN pattern
        self.ssn_pattern = re.compile(
            r'\b\d{3}-?\d{2}-?\d{4}\b'
        )
        
        # Common name patterns (basic)
        self.name_patterns = [
            re.compile(r'\b(?:Mr|Mrs|Ms|Dr)\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b'),
            re.compile(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'),  # First Last
        ]
        
        # IP address pattern
        self.ip_pattern = re.compile(
            r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        )
        
        # URL pattern
        self.url_pattern = re.compile(
            r'https?://[^\s<>"{}|\\^`\[\]]+'
        )
    
    def scrub_pii(self, text: str) -> Dict[str, Any]:
        """
        Scrub PII from text content.
        
        Args:
            text: Raw text content
            
        Returns:
            Dictionary with scrubbed text and PII detection info
        """
        if not text:
            return {
                'scrubbed_text': '',
                'pii_detected': [],
                'pii_count': 0
            }
        
        original_text = text
        pii_detected = []
        
        # Scrub emails
        text, email_count = self._scrub_emails(text)
        if email_count > 0:
            pii_detected.append(f"{email_count} email addresses")
        
        # Scrub phone numbers
        text, phone_count = self._scrub_phone_numbers(text)
        if phone_count > 0:
            pii_detected.append(f"{phone_count} phone numbers")
        
        # Scrub credit cards
        text, cc_count = self._scrub_credit_cards(text)
        if cc_count > 0:
            pii_detected.append(f"{cc_count} credit card numbers")
        
        # Scrub SSNs
        text, ssn_count = self._scrub_ssns(text)
        if ssn_count > 0:
            pii_detected.append(f"{ssn_count} SSNs")
        
        # Scrub names (basic)
        text, name_count = self._scrub_names(text)
        if name_count > 0:
            pii_detected.append(f"{name_count} potential names")
        
        # Scrub IP addresses
        text, ip_count = self._scrub_ip_addresses(text)
        if ip_count > 0:
            pii_detected.append(f"{ip_count} IP addresses")
        
        # Scrub URLs (optional - might be useful to keep)
        # text, url_count = self._scrub_urls(text)
        
        return {
            'scrubbed_text': text,
            'pii_detected': pii_detected,
            'pii_count': len(pii_detected),
            'original_length': len(original_text),
            'scrubbed_length': len(text)
        }
    
    def _scrub_emails(self, text: str) -> Tuple[str, int]:
        """Scrub email addresses from text."""
        matches = self.email_pattern.findall(text)
        count = len(matches)
        
        if count > 0:
            # Replace with masked version
            text = self.email_pattern.sub(
                lambda m: self._mask_email(m.group()), text
            )
        
        return text, count
    
    def _scrub_phone_numbers(self, text: str) -> Tuple[str, int]:
        """Scrub phone numbers from text."""
        total_count = 0
        
        for pattern in self.phone_patterns:
            matches = pattern.findall(text)
            count = len(matches)
            total_count += count
            
            if count > 0:
                text = pattern.sub('[PHONE]', text)
        
        return text, total_count
    
    def _scrub_credit_cards(self, text: str) -> Tuple[str, int]:
        """Scrub credit card numbers from text."""
        matches = self.credit_card_pattern.findall(text)
        count = len(matches)
        
        if count > 0:
            text = self.credit_card_pattern.sub('[CREDIT_CARD]', text)
        
        return text, count
    
    def _scrub_ssns(self, text: str) -> Tuple[str, int]:
        """Scrub SSNs from text."""
        matches = self.ssn_pattern.findall(text)
        count = len(matches)
        
        if count > 0:
            text = self.ssn_pattern.sub('[SSN]', text)
        
        return text, count
    
    def _scrub_names(self, text: str) -> Tuple[str, int]:
        """Scrub potential names from text."""
        total_count = 0
        
        for pattern in self.name_patterns:
            matches = pattern.findall(text)
            count = len(matches)
            total_count += count
            
            if count > 0:
                text = pattern.sub('[NAME]', text)
        
        return text, total_count
    
    def _scrub_ip_addresses(self, text: str) -> Tuple[str, int]:
        """Scrub IP addresses from text."""
        matches = self.ip_pattern.findall(text)
        count = len(matches)
        
        if count > 0:
            text = self.ip_pattern.sub('[IP_ADDRESS]', text)
        
        return text, count
    
    def _scrub_urls(self, text: str) -> Tuple[str, int]:
        """Scrub URLs from text."""
        matches = self.url_pattern.findall(text)
        count = len(matches)
        
        if count > 0:
            text = self.url_pattern.sub('[URL]', text)
        
        return text, count
    
    def _mask_email(self, email: str) -> str:
        """Mask email address while preserving domain."""
        if '@' not in email:
            return '[EMAIL]'
        
        local, domain = email.split('@', 1)
        
        if len(local) <= 2:
            masked_local = '*' * len(local)
        else:
            masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
        
        return f"{masked_local}@{domain}"
    
    def detect_pii_types(self, text: str) -> List[str]:
        """
        Detect what types of PII are present in text.
        
        Args:
            text: Text content to analyze
            
        Returns:
            List of PII types detected
        """
        pii_types = []
        
        if self.email_pattern.search(text):
            pii_types.append('email')
        
        if any(pattern.search(text) for pattern in self.phone_patterns):
            pii_types.append('phone')
        
        if self.credit_card_pattern.search(text):
            pii_types.append('credit_card')
        
        if self.ssn_pattern.search(text):
            pii_types.append('ssn')
        
        if any(pattern.search(text) for pattern in self.name_patterns):
            pii_types.append('name')
        
        if self.ip_pattern.search(text):
            pii_types.append('ip_address')
        
        return pii_types
