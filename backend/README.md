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
- **Multi-Channel Delivery**: Email (SMTP), Google Chat (Webhooks), Zalo (clone UI with REST polling)
- **Teacher Escalation**: Automatic email to teacher when AI confidence is low, with link to the Google Chat space where the student asked
- **Low Grade Alert**: Email to teacher when a student scores below threshold (default: 7.0/10.0)
- **Daily Summary (Students)**: AI-generated plain text summary sent to class Google Chat group with greeting/closing templates
- **Daily Summary (Parents)**: Same AI summary with formal greeting/closing sent to Zalo clone UI
- **Workflow Integration**: `DailyContentWorkflow` automatically sends notifications after generating the AI summary
- **Retry Logic**: Automatic retry with exponential backoff for failed deliveries

### Interactive Chat Service (Cô Hana)
- **Channel-Aware AI**: Two separate personas — parent-facing (Zalo) and student-facing (Google Chat)
- **Zalo `/ask` Command**: Parents type `/ask <question>` in the Zalo clone UI for instant AI answers
- **Google Chat @mention**: Students @mention the bot in Google Chat for AI help
- **Message Debouncing**: Rapid messages from the same user are batched (3s quiet window) into a single AI request
- **Conversation History**: Per-user history (last 10 messages) for contextual follow-ups
- **Smart Escalation**: Zalo → polite apology only; Google Chat → email to teacher + student notification
- **Lesson Context**: AI answers are grounded in `data/lesson.txt` content

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
│  │  ┌─────────┐  ┌─────────────┐  ┌──────────┐  │   │
│  │  │  Email  │  │ Google Chat │  │   Zalo   │  │   │
│  │  │  (SMTP) │  │ (Webhooks)  │  │(clone UI)│  │   │
│  │  └─────────┘  └─────────────┘  └──────────┘  │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │        Chat Service (Cô Hana AI)             │   │
│  │  ┌───────────────┐  ┌────────────────────┐   │   │
│  │  │ Zalo /ask     │  │ Google Chat @bot   │   │   │
│  │  │ (parents)     │  │ (students)         │   │   │
│  │  └───────────────┘  └────────────────────┘   │   │
│  │        ↕ Debouncer → PydanticAI Agent        │   │
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
│   ├── chat/                       # Interactive AI chat (Cô Hana)
│   │   ├── chat_service.py         # Channel-aware LLM orchestrator
│   │   ├── debouncer.py            # Per-user message debouncing
│   │   └── google_chat_listener.py # Pub/Sub consumer + Chat API replier
│   └── notification/               # Notification service
│       ├── models.py               # Notification data models
│       ├── base.py                 # BaseNotifier interface
│       ├── email_notifier.py       # SMTP email (escalation + low grade)
│       ├── google_chat_notifier.py # Google Chat (daily summary only)
│       ├── zalo_notifier.py        # Zalo clone UI (in-memory store → REST polling)
│       └── notification_service.py # Main orchestrator + factory methods
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

### Notification Service

The Notification Service sends **one-way** messages to teachers, students, and parents.
Each notification type targets specific channels — there is no chat or reply.

| Type                     | Channel(s)      | When it fires                                                            |
| ------------------------ | --------------- | ------------------------------------------------------------------------ |
| Teacher Escalation       | Email (SMTP)    | AI not confident → email teacher with link to the Google Chat space      |
| Low Grade Alert          | Email (SMTP)    | Student scores below threshold (default 7/10)                            |
| Daily Summary (students) | Google Chat     | `DailyContentWorkflow` generates AI summary → text posted to class space |
| Daily Summary (parents)  | Zalo clone UI   | Same AI summary with formal greeting/closing → stored for REST polling   |

#### Email (SMTP) Setup

**Step 1: Get Gmail App Password**

1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Navigate to **Security & sign-in** → **2-Step Verification** → Turn on 2-Step Verification
3. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
4. Type name in **App name**: Vinschool AI (your choice)
5. Click **Create** and copy the 16-character password (`abcd efgh ijkl mnop`)

**Step 2: Configure `.env`**

```bash
ENABLE_EMAIL_NOTIFICATIONS=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password # abcdefghijklmnop (no spaces)
SMTP_USE_TLS=true
NOTIFICATION_SENDER_EMAIL=your-email@gmail.com  # Must match SMTP_USERNAME for Gmail
NOTIFICATION_SENDER_NAME=Vinschool AI Assistant
TEACHER_EMAIL=teacher@vinschool.edu.vn          # Recipient for escalation/low-grade emails
LOW_GRADE_THRESHOLD=7.0                         # Students scoring below this get flagged
```

> **Note:** Gmail requires the sender email to match the authenticated account. For a custom sender address like `ai-assistant@vinschool.edu.vn`, use Google Workspace or a transactional email service (SendGrid, Mailgun, Amazon SES).

**Other Email Providers:**

| Provider        | SMTP_HOST           | SMTP_PORT |
| --------------- | ------------------- | --------- |
| Gmail           | smtp.gmail.com      | 587       |
| Outlook/Hotmail | smtp.office365.com  | 587       |
| Yahoo           | smtp.mail.yahoo.com | 587       |

#### Google Chat Setup

Google Chat is used **for daily summaries only** — posted as plain text to the class space.
The notifier supports two modes: Chat API (service account) or Webhook (simpler setup).

**Webhook mode (simpler — Business/Education accounts only):**

1. Open [Google Chat](https://chat.google.com) → create or open a space
2. Click on the Space name → **Apps & integrations** → **Webhooks** → **Add webhooks**
3. Name: "Vinschool AI", click **Save**, copy the webhook URL

```bash
ENABLE_GOOGLE_CHAT_NOTIFICATIONS=true
GOOGLE_CHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/xxx/messages?key=yyy&token=zzz
```

**Chat API mode (service account — supports replies and richer features):**

Configure a GCP service account with Chat API access and set the space name.

```bash
ENABLE_GOOGLE_CHAT_NOTIFICATIONS=true
GOOGLE_CHAT_SPACE_NAME=spaces/AAAA_BBBB
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

#### Zalo Clone UI

The Zalo channel stores plain-text messages in-memory; the frontend polls `GET /api/zalo/messages` every 3 seconds.

**How it works:**
1. `DailyContentWorkflow` generates AI summary
2. `NotificationService` wraps it with greeting/closing templates
3. `ZaloNotifier` stores the full text in `zalo_message_store`
4. Frontend (`ZaloDesktopChat.tsx` / `ZaloMobileChat.tsx`) polls and renders

**Message format:**
```
Bố mẹ các con thân mến,
Cô Hana xin gửi nội dung học tập 2 buổi hôm nay của các con ạ:

<AI-generated summary content here>

Kính mong bố mẹ nhắc nhở các con hoàn thành bài tập đầy đủ giúp cô ạ.
Cảm ơn bố mẹ các con đã đọc tin ạ!
```

**Zalo API endpoints:**

| Method   | Endpoint              | Description                                                          |
| -------- | --------------------- | -------------------------------------------------------------------- |
| `GET`    | `/api/zalo/messages`  | List all stored messages                                             |
| `POST`   | `/api/zalo/send-demo` | Send the hardcoded daily summary to the Zalo UI                      |
| `POST`   | `/api/zalo/chat`      | `/ask` chat with AI (user msg surfaced by frontend, AI reply stored) |
| `DELETE` | `/api/zalo/messages`  | Clear all messages                                                   |

> **Note:** This uses an in-memory store — messages are lost when the server restarts. For production, replace with Zalo OA API integration.

#### Notification Demos

| Command                                               | What it does                                                     |
| ----------------------------------------------------- | ---------------------------------------------------------------- |
| `python scripts/demo_notification.py --dry-run`       | Preview all notification types without sending                   |
| `python scripts/demo_notification.py --escalation`    | Send teacher escalation email                                    |
| `python scripts/demo_notification.py --low-grade`     | Send low grade alert email                                       |
| `python scripts/demo_notification.py --daily-summary` | Send daily summary to Google Chat                                |
| `python scripts/demo_notification.py --daily-parent`  | Send daily summary to Zalo clone UI (requires `run_zalo_server`) |
| `python scripts/demo_notification.py --all`           | Run all demos above                                              |

### Chat Service (Cô Hana)

The Chat Service provides **bidirectional** AI Q&A. Students and parents can ask questions and receive instant answers grounded in `data/lesson.txt`.

| Channel     | Audience | Trigger           | Persona               | Escalation Behaviour           |
| ----------- | -------- | ----------------- | --------------------- | ------------------------------ |
| Zalo clone  | Parents  | `/ask <question>` | Kính ngữ (formal)     | Apologise — no email           |
| Google Chat | Students | @mention bot      | Thân thiện (friendly) | Email teacher + notify student |

**Key features:**
- **Message debouncing**: Rapid messages from the same user are batched (3 s quiet window) into a single AI request
- **Conversation history**: Per-user history (last 10 messages) for contextual follow-ups
- **Smart escalation**: When confidence is low, Google Chat triggers an email to the teacher with a link to the space; Zalo sends a polite apology only

#### Zalo `/ask` — Quick Test

```bash
# Terminal 1 — Start standalone Zalo server
cd backend && python -m scripts.run_zalo_server

# Terminal 2 — Start frontend
cd frontend && npm run dev
```

1. Open http://localhost:3000/zalo-desktop (or `/zalo-mobile`)
2. Type `/ask Bài tập Toán tuần này là gì?` in the chat

Or test from terminal:

```bash
curl -X POST http://localhost:8000/api/zalo/chat \
  -H "Content-Type: application/json" \
  -d '{"sender": "Phụ huynh Alex", "text": "/ask Bài tập Toán tuần này là gì?"}'
```

#### Google Chat @mention

Students @mention the bot in the Google Chat space. Run the listener:

```bash
cd backend && python -m scripts.run_google_chat
```

#### Chat Demos

| Command                              | What it does                       |
| ------------------------------------ | ---------------------------------- |
| `python -m scripts.demo_chat`        | Direct LLM call (no server needed) |
| `python -m scripts.demo_chat --http` | Via HTTP (needs running server)    |

#### Escalation `.env`

```bash
TEACHER_EMAIL=teacher@vinschool.edu.vn  # Recipient for escalation emails
```

## Testing

```bash
# Run all tests (89 tests)
pytest tests/ -v

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test suites
pytest tests/test_chat_service.py -v           # ChatService (24 tests)
pytest tests/test_debouncer.py -v              # MessageDebouncer (9 tests)
pytest tests/test_google_chat_listener.py -v   # GoogleChatListener (10 tests)
pytest tests/test_notification_service.py -v   # NotificationService (46 tests)
```

## Contributing

1. Follow PEP 8 style guide
2. Use type hints
3. Write docstrings for all public functions
4. Add tests for new features
5. Update documentation

## License

Proprietary - Vinschool
