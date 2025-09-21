# Product Feedback Miner - Agentic AI Orchestration Pipeline

A **backend-only agentic AI orchestration pipeline** that automatically collects, processes, and prioritizes product feedback from multiple sources using specialized autonomous AI agents.

## 🎯 What It Does

Collects feedback from GitHub, Hacker News, Exa AI, Twitter, and Reddit → Processes through 8 AI agents → Generates prioritized insights and reports for **any product**.

## 🤖 Agentic AI Agent Pipeline

### **1. Ingestor Agent**
- **Purpose**: Collects raw feedback from external sources
- **Sources**: GitHub issues, Hacker News, Exa AI web search, Twitter, Reddit
- **Output**: Raw feedback data stored in database

### **2. Normalizer Agent** 
- **Purpose**: Cleans and standardizes feedback data
- **Processes**: HTML cleaning, deduplication, language detection, PII scrubbing
- **Output**: Clean, normalized documents ready for analysis

### **3. Classifier Agent**
- **Purpose**: Categorizes feedback using OpenAI GPT
- **Classification**: Feedback type (bug, feature, UX), severity level, component
- **Output**: Structured feedback categories with confidence scores

### **4. Clusterer Agent**
- **Purpose**: Groups similar feedback together using semantic embeddings
- **Technology**: Hugging Face + OpenAI embeddings, DBSCAN clustering
- **Output**: Clustered feedback groups for pattern recognition

### **5. Prioritizer Agent**
- **Purpose**: Scores and ranks feedback by business importance
- **Factors**: Severity, reach, recency, user persona, cluster size
- **Output**: Priority-ranked feedback with actionable insights

### **6. Actioner Agent**
- **Purpose**: Creates tickets and takes automated actions
- **Integrations**: Jira, GitHub issues, Slack notifications
- **Output**: Automated ticket creation for high-priority items

### **7. Digestor Agent**
- **Purpose**: Generates reports and analytics
- **Reports**: Executive summaries, trend analysis, priority breakdowns
- **Output**: HTML/JSON reports with actionable insights

### **8. Feedback Loop Agent**
- **Purpose**: Autonomous learning from outcomes and system improvement
- **Learning**: Self-adjusts scoring weights and agent parameters based on resolution outcomes
- **Output**: Continuous system optimization and agent performance improvements

## 🚀 Quick Start

### 1. Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure API keys in .env
GITHUB_TOKEN=your_github_token
EXA_API_KEY=your_exa_api_key
OPENAI_API_KEY=your_openai_api_key
HUGGINGFACE_TOKEN=your_huggingface_token
DATABASE_HOST=localhost
DATABASE_PASSWORD=your_password
```

### 2. Run for Any Product
```bash
# Complete pipeline for any product
python cli.py execute --workflow=full_pipeline --product-name="Slack"
python cli.py execute --workflow=full_pipeline --product-name="Figma"
python cli.py execute --workflow=full_pipeline --product-name="YourProduct"
```

### 3. Alternative Methods

**API Server:**
```bash
python cli.py serve
curl -X POST "http://localhost:8000/api/v1/workflows/execute" \
  -d '{"workflow_name": "full_pipeline", "config": {"product_name": "YourProduct"}}'
```

**Python Integration:**
```python
from agents.ingestor.agent import IngestorAgent
config = {"product_name": "YourProduct"}
ingestor = IngestorAgent(config)
result = await ingestor.process(context)
```

**Scheduled Automation:**
```bash
# Daily runs at 9 AM
0 9 * * * python cli.py execute --workflow=full_pipeline --product-name="YourProduct"
```

## 🔄 Available Workflows

- **`full_pipeline`**: Complete end-to-end processing (recommended)
- **`feedback_processing`**: Ingestion → Classification only
- **`quick_processing`**: Fast real-time analysis
- **`learning_improvement`**: System optimization

## 📊 Use Cases by Role

**Product Managers**: Daily feedback summaries, trend analysis, competitive intelligence  
**Engineering Teams**: Bug prioritization, feature clustering, technical debt identification  
**Customer Success**: Sentiment analysis, pain point identification, support prioritization  
**Executives**: Strategic insights, market feedback, roadmap validation  

## 🎯 Key Features

- **Agentic AI Architecture**: 8 autonomous AI agents working in orchestrated pipeline
- **Universal Product Support**: Works for any product (Slack, Figma, Notion, VS Code, etc.)
- **Multi-Source Data**: GitHub, Hacker News, Exa AI, Twitter, Reddit
- **Autonomous Processing**: Self-managing agents with GPT classification, semantic clustering, intelligent prioritization
- **Flexible Usage**: CLI, API, Python SDK, scheduled automation
- **Actionable Output**: Prioritized insights, automated reports, ticket creation
- **Self-Learning System**: Autonomous agents continuously improve through feedback loop

## 🏗️ Architecture

**Agentic AI Pipeline**: 8 autonomous agents orchestrated in sequential workflow  
**Backend-Only Design**: API-first, microservices-ready, headless automation  
**Database**: PostgreSQL with pgvector for embeddings  
**AI Models**: OpenAI GPT, Hugging Face embeddings, custom ML algorithms  
**Agent Communication**: Inter-agent data flow and dependency management  
**Integrations**: Jira, GitHub, Slack, Email, Webhooks  

## 📈 Output Examples

- **Priority-ranked bug reports** with business impact scores
- **Clustered feature requests** showing user demand patterns  
- **Executive summaries** with key insights and recommendations
- **Automated tickets** in Jira/GitHub for high-priority items
- **Trend analysis** showing feedback patterns over time

## 🔧 Configuration

The system automatically adapts to any product by changing the `product_name` parameter. Data sources, keywords, and queries are dynamically generated based on the product name.

## 🎉 Why Use This?

- **Agentic AI**: Autonomous agents handle complex orchestration automatically
- **Fast Setup**: Get started in minutes, not hours
- **Comprehensive**: End-to-end agentic feedback processing pipeline  
- **Scalable**: From single products to enterprise portfolios
- **Actionable**: Generates prioritized insights, not just data
- **Self-Learning**: Autonomous agents continuously improve through feedback loop
- **Flexible**: Multiple usage methods and integration options

## 📚 Documentation

- **README.md**: Project overview and quick start
- **USER_GUIDE.md**: Comprehensive usage examples  
- **INFRASTRUCTURE_SETUP.md**: Technical setup details

---

**Ready to analyze feedback for any product in minutes!** 🚀
