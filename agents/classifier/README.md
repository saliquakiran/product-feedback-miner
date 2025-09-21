# Classifier Agent

The Classifier Agent is responsible for categorizing and analyzing processed feedback documents using AI-powered classification.

## Overview

The Classifier Agent takes cleaned feedback documents from the Normalizer Agent and:

1. **Categorizes feedback type**: bug, feature request, UX, pricing, docs, performance, security, integration, or other
2. **Assigns severity levels**: critical, high, medium, low, or minimal
3. **Identifies components**: authentication, UI, API, database, payment, etc.
4. **Extracts metadata**: keywords, sentiment, urgency indicators, version info
5. **Calculates confidence scores**: for each classification dimension

## Features

- **OpenAI Integration**: Uses GPT-3.5-turbo for intelligent classification
- **Batch Processing**: Efficiently processes multiple documents at once
- **Confidence Scoring**: Provides confidence levels for all classifications
- **Business Rules**: Applies validation and adjustment rules
- **Metrics Tracking**: Comprehensive statistics and performance monitoring
- **Error Handling**: Robust error handling with fallback mechanisms

## Architecture

### Models

- **ClassificationResult**: Core data structure for classification results
- **ClassificationBatch**: Batch processing container
- **ClassificationMetrics**: Performance tracking and statistics
- **ClassificationRules**: Business logic and validation rules

### Components

- **ClassifierAgent**: Main agent implementation
- **ClassificationPrompt**: OpenAI prompt templates
- **ClassificationRules**: Validation and adjustment logic

## Usage

### Basic Classification

```python
from agents.classifier.agent import ClassifierAgent

# Initialize the agent
classifier = ClassifierAgent({
    "batch_size": 20,
    "confidence_threshold": 0.5,
    "model_name": "gpt-3.5-turbo"
})

# Classify a single feedback item
result = await classifier.classify_single_feedback(
    title="API timeout errors",
    content="The API is frequently timing out...",
    author="developer123"
)

print(f"Type: {result.feedback_type}")
print(f"Severity: {result.severity_level}")
print(f"Component: {result.component}")
print(f"Confidence: {result.overall_confidence}")
```

### Batch Processing

```python
# Process multiple documents
documents = [
    {"id": "doc1", "title": "Bug report", "body": "..."},
    {"id": "doc2", "title": "Feature request", "body": "..."}
]

results = await classifier.process_batch(documents)
```

### Configuration

The Classifier Agent supports various configuration options:

```python
config = {
    "batch_size": 20,                    # Documents per batch
    "confidence_threshold": 0.5,         # Minimum confidence threshold
    "enable_batch_processing": True,     # Enable batch processing
    "model_name": "gpt-3.5-turbo",      # OpenAI model to use
    "max_tokens": 1000,                  # Max tokens per request
    "temperature": 0.1,                  # Response randomness (0-1)
    "max_retries": 3,                    # Retry attempts for failed requests
    "timeout": 60                        # Request timeout in seconds
}
```

## Classification Types

### Feedback Types

- **BUG**: Issues, errors, broken functionality
- **FEATURE_REQUEST**: Requests for new functionality
- **UX**: User experience issues, usability problems
- **PRICING**: Cost, billing, pricing concerns
- **DOCS**: Documentation issues, unclear instructions
- **PERFORMANCE**: Speed, responsiveness, resource usage
- **SECURITY**: Security vulnerabilities, privacy concerns
- **INTEGRATION**: Third-party integrations, API issues
- **OTHER**: Anything that doesn't fit other categories

### Severity Levels

- **CRITICAL**: System down, data loss, security breach
- **HIGH**: Major functionality broken, significant impact
- **MEDIUM**: Moderate impact, workaround available
- **LOW**: Minor issues, cosmetic problems
- **MINIMAL**: Enhancement suggestions, nice-to-have

### Components

- **AUTHENTICATION**: Login, auth, user management
- **UI**: User interface, frontend
- **API**: Backend API, endpoints
- **DATABASE**: Data storage, queries
- **PAYMENT**: Billing, transactions
- **NOTIFICATIONS**: Alerts, messages
- **SEARCH**: Search functionality
- **DASHBOARD**: Main interface
- **SETTINGS**: Configuration, preferences
- **MOBILE**: Mobile app features
- **DESKTOP**: Desktop app features
- **INTEGRATION**: Third-party integrations
- **SECURITY**: Security features
- **PERFORMANCE**: Performance optimization
- **OTHER**: Other components

## Business Rules

The Classifier Agent applies several business rules:

1. **Feature Request Severity**: Feature requests cannot be critical or high severity
2. **Bug Severity**: Bug reports cannot be minimal severity
3. **Confidence Validation**: Confidence scores must be between 0.0 and 1.0
4. **Low Confidence Warning**: Results with <30% confidence trigger warnings

## Metrics and Monitoring

The agent tracks comprehensive metrics:

- **Processing Statistics**: Total classified, success rate, failure rate
- **Performance Metrics**: Average processing time, confidence scores
- **Distribution Analysis**: Type, severity, and component distributions
- **Quality Metrics**: Classification accuracy and consistency

## Error Handling

The agent includes robust error handling:

- **API Failures**: Automatic retries with exponential backoff
- **Invalid Responses**: Fallback to individual processing
- **Validation Errors**: Logging and graceful degradation
- **Connection Issues**: Timeout handling and reconnection

## Testing

Run the test suite:

```bash
pytest tests/agents/classifier/ -v
```

Run the example:

```bash
python examples/classifier_example.py
```

## Dependencies

- **OpenAI**: AI classification service
- **SQLAlchemy**: Database operations
- **asyncio**: Async processing
- **pydantic**: Data validation
- **pytest**: Testing framework

## Environment Variables

Required environment variables:

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

Optional configuration:

```bash
CLASSIFIER_BATCH_SIZE=20
CLASSIFIER_CONFIDENCE_THRESHOLD=0.5
CLASSIFIER_MODEL_NAME=gpt-3.5-turbo
CLASSIFIER_TEMPERATURE=0.1
```

## Performance Considerations

- **Batch Processing**: Use batch processing for better efficiency
- **Rate Limiting**: Respect OpenAI API rate limits
- **Caching**: Consider caching for repeated classifications
- **Monitoring**: Monitor API usage and costs
- **Error Handling**: Implement proper retry logic

## Future Enhancements

- **Custom Models**: Support for fine-tuned models
- **Multi-language**: Support for non-English feedback
- **Learning**: Continuous improvement from feedback
- **Custom Rules**: User-defined classification rules
- **Analytics**: Advanced classification analytics

