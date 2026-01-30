# Vinschool AI Educational Support System

Multi-agent AI system for educational support built with PydanticAI, Milvus, and FastAPI.

## Features

###  Teaching Assistant Agent
- **Question Answering**: RAG-based question answering with context retrieval
- **Content Summarization**: Daily lesson summaries for students and parents
- **Exercise Generation**: Personalized practice problems based on student level
- **Smart Escalation**: Automatic routing to teachers for complex questions

###  Content Processing Agent
- **Document Parsing**: Supports PPTX, DOCX, PDF, and images
- **Vietnamese OCR**: Tesseract-based OCR with Vietnamese language support
- **Vector Embeddings**: Automatic embedding generation and storage in Milvus
- **Metadata Extraction**: Keyword and summary generation

###  Grading Agent
- **Automated Grading**: Rubric-based homework evaluation
- **Handwriting Support**: OCR for handwritten submissions
- **Detailed Feedback**: Strengths, improvements, and personalized comments
- **Teacher Override**: Teachers can review and adjust AI grades

### Notification Service
- **Multi-Channel Delivery**: Email (SMTP) and Google Chat (Webhooks)
- **Teacher Escalation Alerts**: Automatic notification when AI confidence is low
- **Homework Notifications**: Alerts for submissions and grading completion
- **Struggling Student Detection**: Proactive alerts for students needing help
- **Priority-Based Styling**: Visual distinction for urgent vs routine notifications
- **Retry Logic**: Automatic retry with exponential backoff for failed deliveries

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   FastAPI Application                │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐    │
│  │  Teacher   │  │  Student   │  │   Admin    │    │
│  │   Routes   │  │   Routes   │  │   Routes   │    │
│  └────────────┘  └────────────┘  └────────────┘    │
└─────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────┐
│              Workflow Orchestration                  │
│  ┌──────────────┐  ┌───────────┐  ┌──────────┐     │
│  │Daily Content │  │ Question  │  │ Homework │     │
│  │   Workflow   │  │ Workflow  │  │ Workflow │     │
│  └──────────────┘  └───────────┘  └──────────┘     │
└─────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────┐
│               PydanticAI Agents                      │
│  ┌──────────────┐  ┌───────────┐  ┌──────────┐     │
│  │  Teaching    │  │  Content  │  │ Grading  │     │
│  │  Assistant   │  │ Processor │  │  Agent   │     │
│  └──────────────┘  └───────────┘  └──────────┘     │
└─────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────┐
│                    Services                         │
│  ┌──────────────────────────────────────────────┐   │
│  │          Notification Service                │   │
│  │   ┌─────────────┐    ┌──────────────────┐    │   │
│  │   │   Email     │    │   Google Chat    │    │   │
│  │   │   (SMTP)    │    │   (Webhooks)     │    │   │
│  │   └─────────────┘    └──────────────────┘    │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                          │
┌──────────────────────┬──────────────────────────────┐
│    Milvus Vector DB  │    PostgreSQL Database       │
│  (Document Embeddings)│  (Student, Teacher, etc.)   │
└──────────────────────┴──────────────────────────────┘
```

## Quick Start

### Prerequisites
- Docker and Docker Compose
- **API Key** for one of:
  - OpenAI API key, OR
  - Google Gemini API key, OR
  - Anthropic API key
- (Optional) [uv](https://github.com/astral-sh/uv) for faster Python package management

### Installation

1. **Clone and navigate to backend**
   ```bash
   cd backend
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and configure your LLM provider:

   **Option 1: OpenAI (default)**
   ```bash
   DEFAULT_PROVIDER=openai
   OPENAI_API_KEY=sk-your-openai-key
   DEFAULT_LLM_MODEL=gpt-4-turbo-preview
   ```

   **Option 2: Google Gemini**
   ```bash
   DEFAULT_PROVIDER=google
   GEMINI_API_KEY=your-gemini-api-key
   DEFAULT_LLM_MODEL=gemini-1.5-pro
   ```

   **Option 3: Anthropic**
   ```bash
   DEFAULT_PROVIDER=anthropic
   ANTHROPIC_API_KEY=your-anthropic-key
   DEFAULT_LLM_MODEL=claude-3-opus-20240229
   ```

3. **Start services with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - API Documentation: http://localhost:8000/docs
   - Milvus Management UI (Attu): http://localhost:3000

### Development Setup (Without Docker)

**Using uv (recommended - faster)**
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv pip install -e .[dev]

# Start Milvus and PostgreSQL
docker-compose up -d milvus postgres

# Run development server
uvicorn api.main:app --reload
```

**Using pip**
```bash
pip install -e .[dev]
docker-compose up -d milvus postgres
uvicorn api.main:app --reload
```

## API Usage

### Teacher: Upload Content

```bash
curl -X POST "http://localhost:8000/api/teacher/upload" \
  -F "file=@lesson.pptx" \
  -F "title=Unit 9: Fractions" \
  -F "subject=Mathematics" \
  -F "grade=9" \
  -F "teacher_id=your-teacher-uuid" \
  -F "generate_summary=true" \
  -F "generate_exercises=true"
```

### Student: Ask Question

```bash
curl -X POST "http://localhost:8000/api/student/question" \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "your-student-uuid",
    "question": "How do I add fractions with different denominators?",
    "grade": 9,
    "subject": "Mathematics"
  }'
```

### Student: Submit Homework

```bash
curl -X POST "http://localhost:8000/api/student/homework/submit" \
  -F "assignment_id=your-assignment-uuid" \
  -F "student_id=your-student-uuid" \
  -F "file=@homework.jpg" \
  -F "auto_grade=true"
```

## Project Structure

```
backend/
├── agents/                 # PydanticAI agents
│   ├── base/              # Base agent classes
│   ├── teaching_assistant/ # Q&A, summarization, exercises
│   ├── content_processor/ # Document processing
│   └── grading/           # Homework grading
├── api/                   # FastAPI application
│   ├── main.py           # App initialization
│   └── routes/           # API endpoints
├── config/               # Configuration management
├── database/             # Database clients
│   ├── milvus_client.py  # Milvus vector DB
│   ├── postgres_client.py # PostgreSQL
│   └── repositories/     # Data access layer
├── domain/               # Domain models (DDD)
│   ├── models/          # Entities
│   └── repositories/    # Repository interfaces
├── services/                       # Business services
│   └── notification/               # Notification service
│       ├── models.py               # Notification data models
│       ├── base.py                 # BaseNotifier interface
│       ├── email_notifier.py       # SMTP email
│       ├── google_chat_notifier.py # Google Chat webhooks
│       └── notification_service.py # Main orchestrator
├── utils/                # Utilities
│   ├── embeddings.py    # Embedding generation
│   ├── document_parser.py # Document parsing
│   └── logger.py        # Logging setup
├── workflow/             # Workflow orchestration
│   ├── daily_content_workflow.py
│   ├── question_answering_workflow.py
│   └── homework_grading_workflow.py
├── docker-compose.yml    # Docker orchestration
├── Dockerfile           # Container definition
└── pyproject.toml       # Dependencies
```

## Design Principles

### SOLID Principles

- **Single Responsibility**: Each agent, service, and repository has one clear purpose
- **Open/Closed**: Base agent class allows extension without modification
- **Liskov Substitution**: All agents implement the same interface
- **Interface Segregation**: Minimal, focused repository interfaces
- **Dependency Inversion**: Agents depend on repository abstractions

### Domain-Driven Design

- **Entities**: Student, Teacher, Document, Assignment with rich domain methods
- **Value Objects**: StudentId, TeacherId, DocumentId for type safety
- **Repositories**: Abstract data access behind interfaces
- **Workflows**: Orchestrate business processes

## Configuration

### LLM Provider Setup

The system supports **multiple LLM providers**. Configure in `.env`:

#### OpenAI (GPT-4)
```bash
DEFAULT_PROVIDER=openai
OPENAI_API_KEY=sk-your-key
DEFAULT_LLM_MODEL=gpt-4-turbo-preview
GRADING_LLM_MODEL=gpt-4-turbo-preview
```

#### Google Gemini
```bash
DEFAULT_PROVIDER=google
GEMINI_API_KEY=your-gemini-key
DEFAULT_LLM_MODEL=gemini-1.5-pro
GRADING_LLM_MODEL=gemini-1.5-pro
```

#### Anthropic (Claude)
```bash
DEFAULT_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-anthropic-key
DEFAULT_LLM_MODEL=claude-3-opus-20240229
GRADING_LLM_MODEL=claude-3-opus-20240229
```

### Other Configuration

Key environment variables:

```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_DB=vinschool_ai
POSTGRES_USER=vinschool
POSTGRES_PASSWORD=your_password

# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530

# LLM
OPENAI_API_KEY=your_openai_key
DEFAULT_LLM_MODEL=gpt-4-turbo-preview

# Workflows
ENABLE_AUTO_GRADING=true
TEACHER_ESCALATION_THRESHOLD=0.6
```

### Notification Configuration

Enable teacher notifications via email and/or Google Chat:

#### Email (SMTP)
```bash
ENABLE_EMAIL_NOTIFICATIONS=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
NOTIFICATION_SENDER_EMAIL=ai-assistant@vinschool.edu.vn
NOTIFICATION_SENDER_NAME=Vinschool AI Assistant
```

#### Google Chat (Webhooks)
```bash
ENABLE_GOOGLE_CHAT_NOTIFICATIONS=true
GOOGLE_CHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/xxx/messages?key=yyy
```

**Note:** Teachers can also have individual webhook URLs for their specific chat rooms.

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_agents/test_teaching_assistant.py
```

## Contributing

1. Follow PEP 8 style guide
2. Use type hints
3. Write docstrings for all public functions
4. Add tests for new features
5. Update documentation

## License

Proprietary - Vinschool
