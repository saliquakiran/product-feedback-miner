"""
Classifier Agent for Product Feedback Miner.

This agent classifies processed feedback documents into categories, assigns severity levels,
and extracts additional metadata using OpenAI's API.
"""

import asyncio
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
import openai
from openai import AsyncOpenAI

from agents.base.agent import BaseAgent, AgentResult, AgentContext
from agents.classifier.models import (
    ClassificationResult, ClassificationBatch, ClassificationMetrics,
    ClassificationPrompt, ClassificationRules, FeedbackType, SeverityLevel, ComponentType
)
from database.models import ProcessedDocument, FeedbackType as DBFeedbackType, PriorityLevel
from config.settings import config
from config.api_keys import api_keys

logger = logging.getLogger(__name__)

class ClassifierAgent(BaseAgent):
    """
    Classifier Agent for feedback categorization and severity assessment.
    
    This agent processes cleaned feedback documents and:
    1. Classifies feedback type (bug, feature request, UX, etc.)
    2. Assigns severity levels (critical, high, medium, low, minimal)
    3. Identifies affected components
    4. Extracts keywords and sentiment
    5. Calculates confidence scores
    """
    
    def __init__(self, config_overrides: Optional[Dict[str, Any]] = None):
        super().__init__("classifier", config_overrides)
        
        # Initialize OpenAI client
        self.openai_client = AsyncOpenAI(
            api_key=api_keys.get_openai_key(),
            timeout=config.agents.classifier_timeout
        )
        
        # Configuration
        self.batch_size = self.config.get("batch_size", 20)
        self.max_retries = self.config.get("max_retries", 3)
        self.confidence_threshold = self.config.get("confidence_threshold", 0.5)
        self.enable_batch_processing = self.config.get("enable_batch_processing", True)
        self.model_name = self.config.get("model_name", "gpt-3.5-turbo")
        self.max_tokens = self.config.get("max_tokens", 1000)
        self.temperature = self.config.get("temperature", 0.1)  # Low temperature for consistency
        
        # Metrics tracking
        self.metrics = ClassificationMetrics()
        
    async def process(self, context: AgentContext) -> AgentResult:
        """
        Main processing method for the Classifier Agent.
        
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
            self.logger.info("Starting feedback classification process")
            
            # Get processed documents to classify
            documents = await self._get_pending_documents()
            total_items = len(documents)
            
            if not documents:
                self.logger.info("No documents to classify")
                return AgentResult(
                    success=True,
                    items_processed=0,
                    items_successful=0,
                    items_failed=0,
                    execution_time=(datetime.utcnow() - start_time).total_seconds()
                )
            
            self.logger.info(f"Classifying {total_items} documents")
            
            # Process documents in batches
            if self.enable_batch_processing and total_items > 1:
                results = await self._process_batch_classification(documents)
            else:
                results = await self._process_individual_classification(documents)
            
            # Store classification results
            for result in results:
                try:
                    await self._store_classification_result(result)
                    successful_items += 1
                except Exception as e:
                    self.logger.error(f"Failed to store classification result: {e}")
                    failed_items += 1
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            self.logger.info(
                f"Classification completed: {successful_items}/{total_items} items classified successfully"
            )
            
            return AgentResult(
                success=True,
                items_processed=total_items,
                items_successful=successful_items,
                items_failed=failed_items,
                execution_time=execution_time,
                metadata={
                    'average_confidence': self.metrics.average_confidence,
                    'success_rate': self.metrics.get_success_rate(),
                    'type_distribution': self.metrics.type_distribution,
                    'severity_distribution': self.metrics.severity_distribution,
                    'component_distribution': self.metrics.component_distribution
                }
            )
            
        except Exception as e:
            self.logger.error(f"Classifier Agent failed: {e}", exc_info=True)
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
        return ["normalizer"]  # Depends on Normalizer Agent
    
    async def _get_pending_documents(self) -> List[Dict[str, Any]]:
        """Get processed documents that need classification."""
        async with self.get_db_session() as session:
            # Get documents that haven't been classified yet
            documents = session.query(ProcessedDocument).filter(
                ProcessedDocument.feedback_type.is_(None)  # Not yet classified
            ).limit(1000).all()  # Limit to prevent memory issues
            
            return [
                {
                    'id': doc.id,
                    'title': doc.title,
                    'body': doc.body,
                    'author': doc.author,
                    'timestamp': doc.timestamp,
                    'url': doc.url,
                    'language': doc.language,
                    'word_count': doc.word_count,
                    'raw_feedback_id': doc.raw_feedback_id
                }
                for doc in documents
            ]
    
    async def _process_batch_classification(self, documents: List[Dict[str, Any]]) -> List[ClassificationResult]:
        """Process documents in batches for efficiency."""
        results = []
        
        for i in range(0, len(documents), self.batch_size):
            batch = documents[i:i + self.batch_size]
            batch_results = await self._classify_batch(batch)
            results.extend(batch_results)
            
            # Log progress
            self.logger.info(f"Processed batch {i//self.batch_size + 1}/{(len(documents) + self.batch_size - 1)//self.batch_size}")
        
        return results
    
    async def _process_individual_classification(self, documents: List[Dict[str, Any]]) -> List[ClassificationResult]:
        """Process documents individually."""
        results = []
        
        for i, document in enumerate(documents):
            try:
                result = await self._classify_single_document(document)
                if result:
                    results.append(result)
            except Exception as e:
                self.logger.error(f"Failed to classify document {document.get('id')}: {e}")
                continue
            
            # Log progress
            if (i + 1) % 10 == 0:
                self.logger.info(f"Processed {i + 1}/{len(documents)} documents")
        
        return results
    
    async def _classify_batch(self, documents: List[Dict[str, Any]]) -> List[ClassificationResult]:
        """Classify a batch of documents using OpenAI."""
        try:
            # Prepare batch data for OpenAI
            feedback_items = []
            for doc in documents:
                feedback_items.append({
                    "item_id": str(doc['id']),
                    "title": doc['title'],
                    "content": doc['body'],
                    "author": doc['author'] or "unknown",
                    "source_type": "processed_document"
                })
            
            # Create batch prompt
            prompt = ClassificationPrompt.get_batch_classification_prompt().format(
                feedback_items=json.dumps(feedback_items, indent=2)
            )
            
            # Call OpenAI API
            response = await self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are an expert product feedback classifier. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            # Parse response
            content = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            json_start = content.find('[')
            json_end = content.rfind(']') + 1
            if json_start != -1 and json_end > json_start:
                json_content = content[json_start:json_end]
                classifications = json.loads(json_content)
            else:
                raise ValueError("No valid JSON found in OpenAI response")
            
            # Convert to ClassificationResult objects
            results = []
            for i, classification in enumerate(classifications):
                if i < len(documents):
                    result = self._parse_classification_result(classification, documents[i])
                    if result:
                        results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Batch classification failed: {e}")
            # Fallback to individual classification
            return await self._process_individual_classification(documents)
    
    async def _classify_single_document(self, document: Dict[str, Any]) -> Optional[ClassificationResult]:
        """Classify a single document using OpenAI."""
        try:
            # Create single document prompt
            prompt = ClassificationPrompt.get_classification_prompt().format(
                title=document['title'],
                content=document['body'],
                author=document['author'] or "unknown",
                source_type="processed_document"
            )
            
            # Call OpenAI API
            response = await self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are an expert product feedback classifier. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            # Parse response
            content = response.choices[0].message.content.strip()
            
            # Extract JSON from response with better error handling
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_content = content[json_start:json_end]
                try:
                    classification = json.loads(json_content)
                except json.JSONDecodeError as e:
                    self.logger.warning(f"JSON decode error: {e}. Content: {json_content[:200]}...")
                    # Try to fix common JSON issues
                    json_content = self._fix_json_content(json_content)
                    classification = json.loads(json_content)
            else:
                raise ValueError("No valid JSON found in OpenAI response")
            
            # Convert to ClassificationResult
            result = self._parse_classification_result(classification, document)
            return result
            
        except Exception as e:
            self.logger.error(f"Single document classification failed: {e}")
            return None
    
    def _parse_classification_result(self, classification: Dict[str, Any], document: Dict[str, Any]) -> Optional[ClassificationResult]:
        """Parse OpenAI response into ClassificationResult."""
        try:
            # Extract and validate classification data with fallbacks
            feedback_type = self._parse_feedback_type(classification.get('feedback_type', 'other'))
            severity_level = self._parse_severity_level(classification.get('severity_level', 'medium'))
            component = self._parse_component_type(classification.get('component', 'other'))
            
            # Extract confidence scores
            type_confidence = float(classification.get('type_confidence', 0.5))
            severity_confidence = float(classification.get('severity_confidence', 0.5))
            component_confidence = float(classification.get('component_confidence', 0.5))
            
            # Calculate overall confidence
            overall_confidence = (type_confidence + severity_confidence + component_confidence) / 3.0
            
            # Create result
            result = ClassificationResult(
                document_id=str(document['id']),  # Add document_id
                feedback_type=feedback_type,
                severity_level=severity_level,
                component=component,
                type_confidence=type_confidence,
                severity_confidence=severity_confidence,
                component_confidence=component_confidence,
                overall_confidence=overall_confidence,
                version=classification.get('version'),
                keywords=classification.get('keywords', []),
                sentiment=classification.get('sentiment'),
                urgency_indicators=classification.get('urgency_indicators', [])
            )
            
            # Apply business rules
            result = ClassificationRules.adjust_classification(result)
            
            # Validate result
            is_valid, errors = ClassificationRules.validate_classification(result)
            if not is_valid:
                self.logger.warning(f"Classification validation failed: {errors}")
                # Still use the result but log the issues
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to parse classification result: {e}")
            return None
    
    def _parse_feedback_type(self, value: str) -> FeedbackType:
        """Parse feedback type with intelligent fallbacks."""
        if not value:
            return FeedbackType.OTHER
        
        value = value.lower().strip()
        
        # Direct mapping
        if value in [ft.value for ft in FeedbackType]:
            return FeedbackType(value)
        
        # Fuzzy matching
        if 'bug' in value or 'error' in value or 'issue' in value:
            return FeedbackType.BUG
        elif 'feature' in value or 'request' in value or 'enhancement' in value:
            return FeedbackType.FEATURE_REQUEST
        elif 'ux' in value or 'ui' in value or 'interface' in value or 'design' in value:
            return FeedbackType.UX
        elif 'price' in value or 'cost' in value or 'billing' in value:
            return FeedbackType.PRICING
        elif 'doc' in value or 'help' in value or 'guide' in value:
            return FeedbackType.DOCS
        elif 'performance' in value or 'speed' in value or 'slow' in value:
            return FeedbackType.PERFORMANCE
        elif 'security' in value or 'secure' in value or 'vulnerability' in value:
            return FeedbackType.SECURITY
        elif 'integration' in value or 'api' in value or 'connect' in value:
            return FeedbackType.INTEGRATION
        else:
            return FeedbackType.OTHER
    
    def _parse_severity_level(self, value: str) -> SeverityLevel:
        """Parse severity level with intelligent fallbacks."""
        if not value:
            return SeverityLevel.MEDIUM
        
        value = value.lower().strip()
        
        # Direct mapping
        if value in [sl.value for sl in SeverityLevel]:
            return SeverityLevel(value)
        
        # Fuzzy matching
        if 'critical' in value or 'urgent' in value or 'emergency' in value:
            return SeverityLevel.CRITICAL
        elif 'high' in value or 'important' in value:
            return SeverityLevel.HIGH
        elif 'medium' in value or 'normal' in value or 'moderate' in value:
            return SeverityLevel.MEDIUM
        elif 'low' in value or 'minor' in value:
            return SeverityLevel.LOW
        elif 'minimal' in value or 'trivial' in value:
            return SeverityLevel.MINIMAL
        else:
            return SeverityLevel.MEDIUM
    
    def _parse_component_type(self, value: str) -> ComponentType:
        """Parse component type with intelligent fallbacks."""
        if not value:
            return ComponentType.OTHER
        
        value = value.lower().strip()
        
        # Direct mapping
        if value in [ct.value for ct in ComponentType]:
            return ComponentType(value)
        
        # Fuzzy matching
        if 'auth' in value or 'login' in value or 'password' in value:
            return ComponentType.AUTHENTICATION
        elif 'ui' in value or 'interface' in value or 'frontend' in value:
            return ComponentType.UI
        elif 'api' in value or 'endpoint' in value:
            return ComponentType.API
        elif 'database' in value or 'db' in value or 'data' in value:
            return ComponentType.DATABASE
        elif 'payment' in value or 'billing' in value or 'checkout' in value:
            return ComponentType.PAYMENT
        elif 'notification' in value or 'alert' in value or 'email' in value:
            return ComponentType.NOTIFICATIONS
        elif 'search' in value or 'find' in value:
            return ComponentType.SEARCH
        elif 'dashboard' in value or 'home' in value:
            return ComponentType.DASHBOARD
        elif 'setting' in value or 'config' in value or 'preference' in value:
            return ComponentType.SETTINGS
        elif 'mobile' in value or 'phone' in value or 'app' in value:
            return ComponentType.MOBILE
        elif 'desktop' in value or 'pc' in value:
            return ComponentType.DESKTOP
        elif 'integration' in value or 'connect' in value:
            return ComponentType.INTEGRATION
        elif 'security' in value or 'secure' in value:
            return ComponentType.SECURITY
        elif 'performance' in value or 'speed' in value:
            return ComponentType.PERFORMANCE
        else:
            return ComponentType.OTHER
    
    def _fix_json_content(self, json_content: str) -> str:
        """Fix common JSON issues in OpenAI responses."""
        import re
        
        # Remove trailing commas before closing braces/brackets
        json_content = re.sub(r',(\s*[}\]])', r'\1', json_content)
        
        # Fix single quotes to double quotes
        json_content = re.sub(r"'([^']*)':", r'"\1":', json_content)
        json_content = re.sub(r":\s*'([^']*)'", r': "\1"', json_content)
        
        # Fix unescaped quotes in strings
        json_content = re.sub(r'([^\\])"([^"]*)"([^"]*)"', r'\1"\2\3"', json_content)
        
        return json_content
    
    async def _store_classification_result(self, result: ClassificationResult) -> None:
        """Store classification result in the database."""
        async with self.get_db_session() as session:
            # Find the processed document
            document = session.query(ProcessedDocument).filter(
                ProcessedDocument.id == result.document_id
            ).first()
            
            if not document:
                self.logger.error(f"Document not found for classification result")
                return
            
            # Update document with classification results
            document.feedback_type = result.feedback_type.value
            document.severity_score = self._convert_severity_to_score(result.severity_level)
            document.component = result.component.value
            document.version = result.version
            document.confidence_score = result.overall_confidence
            
            # Store additional metadata
            if not document.processing_errors:
                document.processing_errors = {}
            
            document.processing_errors.update({
                'classification_metadata': {
                    'type_confidence': result.type_confidence,
                    'severity_confidence': result.severity_confidence,
                    'component_confidence': result.component_confidence,
                    'keywords': result.keywords,
                    'sentiment': result.sentiment,
                    'urgency_indicators': result.urgency_indicators,
                    'classification_timestamp': result.classification_timestamp.isoformat(),
                    'model_version': result.model_version
                }
            })
            
            session.commit()
            
            # Update metrics
            processing_time = (datetime.utcnow() - result.classification_timestamp).total_seconds() * 1000
            self.metrics.add_classification(result, processing_time)
    
    def _convert_severity_to_score(self, severity_level: SeverityLevel) -> float:
        """Convert severity level to numeric score (0-1)."""
        severity_scores = {
            SeverityLevel.CRITICAL: 1.0,
            SeverityLevel.HIGH: 0.8,
            SeverityLevel.MEDIUM: 0.6,
            SeverityLevel.LOW: 0.4,
            SeverityLevel.MINIMAL: 0.2
        }
        return severity_scores.get(severity_level, 0.5)
    
    async def classify_single_feedback(self, title: str, content: str, author: str = "unknown") -> Optional[ClassificationResult]:
        """Classify a single piece of feedback (for testing or manual use)."""
        document = {
            'id': 'manual_classification',
            'title': title,
            'content': content,
            'author': author,
            'body': content,
            'timestamp': datetime.utcnow(),
            'url': '',
            'language': 'en',
            'word_count': len(content.split())
        }
        
        return await self._classify_single_document(document)
    
    async def get_classification_stats(self) -> Dict[str, Any]:
        """Get classification statistics."""
        return self.metrics.to_dict()
    
    async def test_openai_connection(self) -> bool:
        """Test OpenAI API connection."""
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": "Test connection. Respond with 'OK'."}
                ],
                max_tokens=10,
                temperature=0
            )
            return response.choices[0].message.content.strip() == "OK"
        except Exception as e:
            self.logger.error(f"OpenAI connection test failed: {e}")
            return False

