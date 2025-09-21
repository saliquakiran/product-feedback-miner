"""
Deduplication processor for the Normalizer Agent.

This module provides functionality to detect and handle duplicate
feedback content across different sources.
"""

import hashlib
from typing import List, Dict, Any, Set, Tuple
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)

class Deduplicator:
    """Deduplication utility for feedback content."""
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self.content_hashes: Set[str] = set()
        self.processed_urls: Set[str] = set()
    
    def find_duplicates(self, feedback_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Find duplicate feedback items.
        
        Args:
            feedback_items: List of feedback items to check
            
        Returns:
            Dictionary with duplicate analysis results
        """
        if not feedback_items:
            return {
                'duplicates': [],
                'unique_items': [],
                'duplicate_count': 0,
                'unique_count': 0
            }
        
        duplicates = []
        unique_items = []
        processed_hashes = set()
        
        for item in feedback_items:
            # Generate content hash
            content_hash = self._generate_content_hash(item)
            
            # Check for exact duplicates
            if content_hash in processed_hashes:
                duplicates.append({
                    'item': item,
                    'duplicate_type': 'exact',
                    'content_hash': content_hash
                })
                continue
            
            # Check for similar content
            is_similar = self._check_similarity(item, unique_items)
            
            if is_similar:
                duplicates.append({
                    'item': item,
                    'duplicate_type': 'similar',
                    'similarity_score': is_similar['similarity_score'],
                    'similar_to': is_similar['similar_item']
                })
            else:
                unique_items.append(item)
                processed_hashes.add(content_hash)
        
        return {
            'duplicates': duplicates,
            'unique_items': unique_items,
            'duplicate_count': len(duplicates),
            'unique_count': len(unique_items)
        }
    
    def _generate_content_hash(self, item: Dict[str, Any]) -> str:
        """Generate hash for content deduplication."""
        # Combine title and content for hashing
        content = f"{item.get('title', '')} {item.get('content', '')}"
        
        # Normalize content for hashing
        content = content.lower().strip()
        
        # Generate MD5 hash
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _check_similarity(self, item: Dict[str, Any], existing_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check if item is similar to existing items."""
        item_content = f"{item.get('title', '')} {item.get('content', '')}"
        item_content = item_content.lower().strip()
        
        for existing_item in existing_items:
            existing_content = f"{existing_item.get('title', '')} {existing_item.get('content', '')}"
            existing_content = existing_content.lower().strip()
            
            # Calculate similarity
            similarity = self._calculate_similarity(item_content, existing_content)
            
            if similarity >= self.similarity_threshold:
                return {
                    'similarity_score': similarity,
                    'similar_item': existing_item
                }
        
        return None
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        if not text1 or not text2:
            return 0.0
        
        # Use SequenceMatcher for similarity calculation
        matcher = SequenceMatcher(None, text1, text2)
        return matcher.ratio()
    
    def merge_duplicates(self, duplicates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge duplicate items into single items.
        
        Args:
            duplicates: List of duplicate items
            
        Returns:
            List of merged items
        """
        merged_items = []
        processed_groups = set()
        
        for duplicate in duplicates:
            if duplicate['duplicate_type'] == 'exact':
                # For exact duplicates, keep the most recent one
                item = duplicate['item']
                if item['url'] not in processed_groups:
                    merged_items.append(item)
                    processed_groups.add(item['url'])
            
            elif duplicate['duplicate_type'] == 'similar':
                # For similar items, merge metadata
                item = duplicate['item']
                similar_item = duplicate['similar_item']
                
                if item['url'] not in processed_groups:
                    # Merge metadata
                    merged_item = self._merge_item_metadata(item, similar_item)
                    merged_items.append(merged_item)
                    processed_groups.add(item['url'])
        
        return merged_items
    
    def _merge_item_metadata(self, item1: Dict[str, Any], item2: Dict[str, Any]) -> Dict[str, Any]:
        """Merge metadata from two similar items."""
        merged = item1.copy()
        
        # Merge raw metadata
        if 'raw_metadata' in item1 and 'raw_metadata' in item2:
            merged['raw_metadata'] = {
                **item1['raw_metadata'],
                **item2['raw_metadata']
            }
        
        # Add merge information
        merged['merge_info'] = {
            'merged_with': item2.get('url', ''),
            'merge_timestamp': item1.get('timestamp', ''),
            'merge_reason': 'similar_content'
        }
        
        return merged
    
    def detect_cross_source_duplicates(self, feedback_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect duplicates across different sources.
        
        Args:
            feedback_items: List of feedback items from different sources
            
        Returns:
            List of cross-source duplicate groups
        """
        # Group items by content similarity
        duplicate_groups = []
        processed_items = set()
        
        for i, item1 in enumerate(feedback_items):
            if i in processed_items:
                continue
            
            group = [item1]
            processed_items.add(i)
            
            for j, item2 in enumerate(feedback_items[i+1:], i+1):
                if j in processed_items:
                    continue
                
                # Check if items are from different sources
                if item1.get('source_type') != item2.get('source_type'):
                    similarity = self._calculate_similarity(
                        f"{item1.get('title', '')} {item1.get('content', '')}",
                        f"{item2.get('title', '')} {item2.get('content', '')}"
                    )
                    
                    if similarity >= self.similarity_threshold:
                        group.append(item2)
                        processed_items.add(j)
            
            if len(group) > 1:
                duplicate_groups.append({
                    'group': group,
                    'sources': list(set(item.get('source_type') for item in group)),
                    'similarity_score': similarity
                })
        
        return duplicate_groups
    
    def get_deduplication_stats(self, feedback_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get deduplication statistics.
        
        Args:
            feedback_items: List of feedback items
            
        Returns:
            Dictionary with deduplication statistics
        """
        duplicate_analysis = self.find_duplicates(feedback_items)
        
        # Calculate source distribution
        source_counts = {}
        for item in feedback_items:
            source = item.get('source_type', 'unknown')
            source_counts[source] = source_counts.get(source, 0) + 1
        
        # Calculate duplicate types
        exact_duplicates = sum(1 for d in duplicate_analysis['duplicates'] 
                             if d['duplicate_type'] == 'exact')
        similar_duplicates = sum(1 for d in duplicate_analysis['duplicates'] 
                               if d['duplicate_type'] == 'similar')
        
        return {
            'total_items': len(feedback_items),
            'unique_items': duplicate_analysis['unique_count'],
            'duplicate_items': duplicate_analysis['duplicate_count'],
            'exact_duplicates': exact_duplicates,
            'similar_duplicates': similar_duplicates,
            'deduplication_rate': duplicate_analysis['duplicate_count'] / len(feedback_items) if feedback_items else 0,
            'source_distribution': source_counts
        }
