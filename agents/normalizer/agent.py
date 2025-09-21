"""
Normalizer Agent for Product Feedback Miner.

This agent cleans and normalizes raw feedback data from the Ingestor Agent,
preparing it for further processing by the Classifier Agent.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from agents.base.agent import BaseAgent, AgentResult, AgentContext
from agents.normalizer.processors.html_cleaner import HTMLCleaner
from agents.normalizer.processors.pii_scrubber import PIIScrubber
from agents.normalizer.processors.deduplicator import Deduplicator
from agents.normalizer.processors.language_detector import LanguageDetector
from database.models import RawFeedback, ProcessedDocument, SourceType, ProcessingStatus
from config.settings import config

logger = logging.getLogger(__name__)

class NormalizerAgent(BaseAgent):
    """
    Normalizer Agent for cleaning and normalizing feedback data.
    
    This agent processes raw feedback data through multiple cleaning stages:
    1. HTML cleaning and text extraction
    2. PII scrubbing for privacy protection
    3. Deduplication across sources
    4. Language detection and filtering
    5. Text normalization and validation
    """
    
    def __init__(self, config_overrides: Optional[Dict[str, Any]] = None):
        super().__init__("normalizer", config_overrides)
        
        # Initialize processors
        self.html_cleaner = HTMLCleaner()
        self.pii_scrubber = PIIScrubber()
        self.deduplicator = Deduplicator(
            similarity_threshold=self.config.get("similarity_threshold", 0.85)
        )
        self.language_detector = LanguageDetector(
            default_language=self.config.get("default_language", "en")
        )
        
        # Configuration
        self.batch_size = self.config.get("batch_size", 50)
        self.enable_pii_scrubbing = self.config.get("enable_pii_scrubbing", True)
        self.enable_deduplication = self.config.get("enable_deduplication", True)
        self.enable_language_filtering = self.config.get("enable_language_filtering", True)
        self.target_language = self.config.get("target_language", "en")
        self.min_word_count = self.config.get("min_word_count", 5)
        self.max_word_count = self.config.get("max_word_count", 10000)
    
    async def process(self, context: AgentContext) -> AgentResult:
        """
        Main processing method for the Normalizer Agent.
        
        Args:
            context: Agent context with execution metadata
            
        Returns:
            AgentResult: Processing results and statistics
        """
        start_time = datetime.utcnow()
        total_items = 0
        successful_items = 0
        failed_items = 0
        
        try:
            self.logger.info("Starting data normalization process")
            
            # Get raw feedback items to process
            raw_items = await self._get_pending_raw_feedback()
            total_items = len(raw_items)
            
            if not raw_items:
                self.logger.info("No raw feedback items to process")
                return AgentResult(
                    success=True,
                    items_processed=0,
                    items_successful=0,
                    items_failed=0,
                    execution_time=(datetime.utcnow() - start_time).total_seconds()
                )
            
            self.logger.info(f"Processing {total_items} raw feedback items")
            
            # Process items in batches
            processed_items = []
            for i in range(0, len(raw_items), self.batch_size):
                batch = raw_items[i:i + self.batch_size]
                batch_processed = await self._process_batch(batch)
                processed_items.extend(batch_processed)
                
                # Log progress
                self.logger.info(f"Processed batch {i//self.batch_size + 1}/{(len(raw_items) + self.batch_size - 1)//self.batch_size}")
            
            # Deduplication (if enabled)
            if self.enable_deduplication and processed_items:
                self.logger.info("Running deduplication")
                dedup_results = self.deduplicator.find_duplicates(processed_items)
                processed_items = dedup_results['unique_items']
                
                self.logger.info(f"Deduplication: {dedup_results['duplicate_count']} duplicates found, {dedup_results['unique_count']} unique items")
            
            # Language filtering (if enabled)
            if self.enable_language_filtering and processed_items:
                self.logger.info(f"Filtering by language: {self.target_language}")
                original_count = len(processed_items)
                processed_items = self.language_detector.filter_by_language(
                    processed_items, self.target_language
                )
                filtered_count = original_count - len(processed_items)
                
                if filtered_count > 0:
                    self.logger.info(f"Language filtering: {filtered_count} items filtered out")
            
            # Store processed documents
            for item in processed_items:
                try:
                    await self._store_processed_document(item)
                    successful_items += 1
                except Exception as e:
                    self.logger.error(f"Failed to store processed document: {e}")
                    failed_items += 1
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            self.logger.info(
                f"Normalization completed: {successful_items}/{total_items} items processed successfully"
            )
            
            return AgentResult(
                success=True,
                items_processed=total_items,
                items_successful=successful_items,
                items_failed=failed_items,
                execution_time=execution_time,
                metadata={
                    'duplicates_found': dedup_results.get('duplicate_count', 0) if self.enable_deduplication else 0,
                    'language_filtered': filtered_count if self.enable_language_filtering else 0,
                    'pii_scrubbed': sum(1 for item in processed_items if item.get('pii_detected', [])),
                    'average_word_count': sum(item.get('word_count', 0) for item in processed_items) / len(processed_items) if processed_items else 0
                }
            )
            
        except Exception as e:
            self.logger.error(f"Normalizer Agent failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                items_processed=total_items,
                items_successful=successful_items,
                items_failed=failed_items,
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                error_message=str(e)
            )
    
    def get_input_dependencies(self) -> List[str]:
        """Get list of agent names that this agent depends on for input."""
        return ["ingestor"]  # Depends on Ingestor Agent
    
    async def _get_pending_raw_feedback(self) -> List[Dict[str, Any]]:
        """Get raw feedback items that need processing."""
        async with self.get_db_session() as session:
            # Get raw feedback items that haven't been processed yet
            raw_items = session.query(RawFeedback).filter(
                ~RawFeedback.processed_docs.any()
            ).limit(1000).all()  # Limit to prevent memory issues
            
            return [
                {
                    'id': item.id,
                    'source_type': item.source_type,
                    'source_id': item.source_id,
                    'url': item.url,
                    'title': item.title,
                    'content': item.content,
                    'author': item.author,
                    'author_url': item.author_url,
                    'timestamp': item.timestamp,
                    'raw_metadata': item.raw_metadata or {}
                }
                for item in raw_items
            ]
    
    async def _process_batch(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a batch of raw feedback items."""
        processed_items = []
        
        for item in batch:
            try:
                processed_item = await self._process_single_item(item)
                if processed_item:
                    processed_items.append(processed_item)
            except Exception as e:
                self.logger.error(f"Failed to process item {item.get('id')}: {e}")
                continue
        
        return processed_items
    
    async def _process_single_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single raw feedback item."""
        try:
            # Step 1: HTML cleaning
            cleaned_title = self.html_cleaner.clean_title(item.get('title', ''))
            cleaned_content = self.html_cleaner.clean_html(item.get('content', ''))
            
            # Step 2: PII scrubbing (if enabled)
            if self.enable_pii_scrubbing:
                title_pii = self.pii_scrubber.scrub_pii(cleaned_title)
                content_pii = self.pii_scrubber.scrub_pii(cleaned_content)
                
                cleaned_title = title_pii['scrubbed_text']
                cleaned_content = content_pii['scrubbed_text']
                
                pii_detected = title_pii['pii_detected'] + content_pii['pii_detected']
            else:
                pii_detected = []
            
            # Step 3: Language detection
            full_text = f"{cleaned_title} {cleaned_content}"
            lang_result = self.language_detector.detect_language(full_text)
            
            # Step 4: Word count and validation
            word_count = len(cleaned_content.split())
            
            # Validate content quality (more lenient)
            if word_count < max(2, self.min_word_count):  # At least 2 words, or config minimum
                self.logger.warning(f"Item {item.get('id')} has too few words ({word_count}), skipping")
                return None
            
            if word_count > self.max_word_count:
                self.logger.warning(f"Item {item.get('id')} has too many words ({word_count}), truncating")
                cleaned_content = ' '.join(cleaned_content.split()[:self.max_word_count])
                word_count = self.max_word_count
            
            # Step 5: Create processed document
            processed_item = {
                'raw_feedback_id': item['id'],
                'title': cleaned_title,
                'body': cleaned_content,
                'author': item.get('author', ''),
                'timestamp': item.get('timestamp'),
                'url': item.get('url', ''),
                'language': lang_result['language'],
                'word_count': word_count,
                'processing_status': 'completed',
                'pii_detected': pii_detected,
                'language_confidence': lang_result['confidence'],
                'processing_metadata': {
                    'html_cleaned': True,
                    'pii_scrubbed': self.enable_pii_scrubbing,
                    'language_detected': lang_result['method'],
                    'original_title_length': len(item.get('title', '')),
                    'original_content_length': len(item.get('content', '')),
                    'processing_timestamp': datetime.utcnow().isoformat()
                }
            }
            
            return processed_item
            
        except Exception as e:
            self.logger.error(f"Error processing item {item.get('id')}: {e}")
            return None
    
    async def _store_processed_document(self, item: Dict[str, Any]) -> None:
        """Store processed document in the database."""
        async with self.get_db_session() as session:
            # Create ProcessedDocument
            processed_doc = ProcessedDocument(
                raw_feedback_id=item['raw_feedback_id'],
                title=item['title'],
                body=item['body'],
                author=item['author'],
                timestamp=item['timestamp'],
                url=item['url'],
                language=item['language'],
                word_count=item['word_count'],
                processing_status=ProcessingStatus.COMPLETED,
                processing_errors=None
            )
            
            session.add(processed_doc)
            session.commit()
            
            # Update raw feedback status
            raw_feedback = session.query(RawFeedback).filter(
                RawFeedback.id == item['raw_feedback_id']
            ).first()
            
            if raw_feedback:
                raw_feedback.processing_status = ProcessingStatus.COMPLETED
                session.commit()
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        async with self.get_db_session() as session:
            # Count processed documents
            total_processed = session.query(ProcessedDocument).count()
            
            # Count by language
            language_stats = {}
            for doc in session.query(ProcessedDocument).all():
                lang = doc.language or 'unknown'
                language_stats[lang] = language_stats.get(lang, 0) + 1
            
            # Count by source
            source_stats = {}
            for doc in session.query(ProcessedDocument).join(RawFeedback).all():
                source = doc.raw_feedback.source_type
                source_stats[source] = source_stats.get(source, 0) + 1
            
            return {
                'total_processed': total_processed,
                'language_distribution': language_stats,
                'source_distribution': source_stats,
                'average_word_count': sum(doc.word_count or 0 for doc in session.query(ProcessedDocument).all()) / total_processed if total_processed > 0 else 0
            }
