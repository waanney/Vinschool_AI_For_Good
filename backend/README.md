# Vinschool AI Educational Support System

Multi-agent AI system for educational support built with PydanticAI, Milvus, and FastAPI.

## Features

### Teaching Assistant Agent

- **Question Answering**: RAG-based question answering with context retrieval
- **Content Summarization**: Daily lesson summaries for students and parents
- **Exercise Generation**: Personalized practice problems based on student level
- **Smart Escalation**: Automatic routing to teachers for complex questions

### Content Processing Agent

- **Document Parsing**: Supports PPTX, DOCX, PDF, and images
- **Vietnamese OCR**: Tesseract-based OCR with Vietnamese language support
- **Lesson Image Parsing**: Upload a lesson photo and Gemini 2.5 Pro extracts structured content (subject, title, key points, homework) and stores it in Milvus
- **Vector Embeddings**: Automatic embedding generation and storage in Milvus
- **Metadata Extraction**: Keyword and summary generation

### Grading Agent

- **Automated Grading**: Rubric-based homework evaluation via Gemini vision
- **Handwriting Support**: OCR-first for handwritten submissions, with direct vision grading as fallback when Tesseract is unavailable
- **Two-Tier Feedback**: Concise feedback (≤100 chars, for Google Chat reply & LMS table) and detailed feedback (4-6 sentence paragraph from Cô Hana, for email & LMS detail modal)
- **Cô Hana Persona**: AI always speaks as "Cô Hana"
- **Vietnamese Name Convention**: Uses last 2 words of student's full name; preserves diacritical marks exactly as received
- **Milvus Grading Storage**: After grading, results (score, feedback, detailed feedback) are stored in Milvus so students can later `/ask` about their grades
- **Teacher Override**: Teachers can review and adjust AI grades

### Notification Service

- **Multi-Channel Delivery**: Email (SMTP), Google Chat (Webhooks), Zalo (clone UI with REST polling)
- **Teacher Escalation**: Automatic email to teacher when AI confidence is low, with link to the Google Chat space where the student asked
- **Low Grade Alert**: Email to teacher when a student scores below threshold (default: 7.0/10.0)
- **Daily Summary (Students)**: AI-generated plain text summary sent to class Google Chat group
- **Daily Summary (Parents)**: Same AI summary sent to Zalo clone UI
- **Automatic Scheduler**: `DailySummaryScheduler` fires at 18:00 every day (configurable via `DAILY_SUMMARY_HOUR`/`DAILY_SUMMARY_MINUTE`) to send the daily summary to both channels
- **Workflow Integration**: `DailyContentWorkflow` automatically sends notifications after generating the AI summary
- **Retry Logic**: Automatic retry with exponential backoff for failed deliveries

### Interactive Chat Service (Cô Hana)

- **Channel-Aware AI**: Two separate personas — parent-facing (Zalo) and student-facing (Google Chat)
- **Zalo commands**: `/dailysum` (hardcoded demo summary — no API cost)
- **Google Chat commands**: `/ask`, `/grade`, `/hw`, `/dailysum`, `/help` when @mentioning the bot; any other mention is silently ignored
- **Demo Trigger Phrases** (Google Chat only): Natural-language phrases like `Cô ơi chấm bài...`, `Cô ơi ngày mai có...` etc. return hardcoded responses for live demos — no AI cost. See [DEMO.md](DEMO.md) for the full list.
- **Single-Message Flow**: Every command returns exactly one reply — no intermediate "thinking" or typing indicator messages
- **Message Debouncing**: Rapid messages from the same user are batched (3s quiet window) into a single AI request
- **Conversation History**: Per-user history (last 10 messages) for contextual follow-ups
- **Smart Escalation**: Zalo → polite apology only; Google Chat → email to teacher + student notification
- **Grading Context Retrieval**: When a student `/ask`s about their grades, Milvus is queried for relevant grading results which are injected into the LLM prompt so Cô Hana can answer with actual score, feedback, and detailed feedback
- **Lesson Context**: AI answers are grounded in lesson data — reads from **Milvus** in production, falls back to `data/lesson.txt` for local development

## Architecture

```text
┌─────────────────────────────────────────────────────┐
│                   FastAPI Application               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐     │
│  │  Teacher   │  │  Student   │  │   Admin    │     │
│  │   Routes   │  │   Routes   │  │   Routes   │     │
│  └────────────┘  └────────────┘  └────────────┘     │
└─────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────┐
│              Workflow Orchestration                 │
│  ┌──────────────┐  ┌───────────┐  ┌──────────┐      │
│  │Daily Content │  │ Question  │  │ Homework │      │
│  │   Workflow   │  │ Workflow  │  │ Workflow │      │
│  └──────────────┘  └───────────┘  └──────────┘      │
└─────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────┐
│               PydanticAI Agents                     │
│  ┌──────────────┐  ┌───────────┐  ┌──────────┐      │
│  │  Teaching    │  │  Content  │  │ Grading  │      │
│  │  Assistant   │  │ Processor │  │  Agent   │      │
│  └──────────────┘  └───────────┘  └──────────┘      │
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
│  │  │     Zalo      │  │ Google Chat @bot   │   │   │
│  │  │   (parents)   │  │    (students)      │   │   │
│  │  └───────────────┘  └────────────────────┘   │   │
│  │        ↕ Debouncer → PydanticAI Agent        │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                          │
┌───────────────────────┬─────────────────────────────┐
│    Milvus Vector DB   │    PostgreSQL Database      │
│ (Documents + Grading) │  (Student, Teacher, etc.)   │
└───────────────────────┴─────────────────────────────┘
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
   DEFAULT_LLM_MODEL=gemini-2.5-pro
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
   - API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Milvus Management UI (Attu): [http://localhost:3000](http://localhost:3000)

### Development Setup (Without Docker)

#### Using uv (recommended - faster)

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv pip install -e .[dev]

# Option A: Local Milvus + PostgreSQL via Docker
docker-compose up -d milvus postgres

# Option B: Cloud services (Zilliz Cloud + Render PostgreSQL)
# Set MILVUS_URI, MILVUS_TOKEN, DATABASE_URL in .env — no Docker needed

# Run development server
uvicorn api.main:app --reload
```

#### Using pip

```bash
pip install -e .[dev]

# Start Milvus and PostgreSQL (or use cloud services via .env)
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

```text
backend/
├── agents/                  # PydanticAI agents
│   ├── base/                       # Base agent classes
│   ├── teaching_assistant/         # Q&A, summarization, exercises
│   ├── content_processor/          # Document processing
│   └── grading/                    # Homework grading
├── api/                     # FastAPI application
│   ├── main.py                     # App initialization
│   └── routes/                     # API endpoints
├── config/                  # Configuration management
├── database/                # Database clients
│   ├── milvus_client.py            # Milvus vector DB
│   ├── postgres_client.py          # PostgreSQL
│   └── repositories/               # Data access layer
│       ├── daily_lesson_repository.py     # Daily lesson storage
│       ├── document_repository.py         # Document storage
│       ├── grading_repository.py          # Grading results → Milvus
│       └── student_profile_repository.py  # Student profile storage
├── domain/                  # Domain models (DDD)
│   ├── models/                     # Entities
│   └── repositories/               # Repository interfaces
├── services/                # Business services
│   ├── chat/                       # Interactive AI chat (Cô Hana)
│   │   ├── chat_service.py                # Channel-aware LLM orchestrator
│   │   ├── debouncer.py                   # Per-user message debouncing
│   │   ├── google_chat_listener.py        # Pub/Sub consumer + Chat API replier
│   │   └── submission_store.py            # In-memory store for /grade submissions
│   ├── scheduler.py                # 6pm daily summary scheduler + /dailysum trigger
│   └── notification/               # Notification service
│       ├── models.py                      # Notification data models
│       ├── base.py                        # BaseNotifier interface
│       ├── email_notifier.py              # SMTP email (escalation + low grade)
│       ├── google_chat_notifier.py        # Google Chat (daily summary only)
│       ├── zalo_notifier.py               # Zalo clone UI (in-memory store → REST polling)
│       └── notification_service.py        # Main orchestrator + factory methods
├── utils/                   # Utilities
│   ├── embeddings.py               # Embedding generation
│   ├── document_parser.py          # Document parsing
│   ├── gemini_vision.py            # Gemini 2.5 Pro image/OCR parsing
│   └── logger.py                   # Logging setup
├── workflow/                # Workflow orchestration
│   ├── daily_content_workflow.py
│   ├── homework_grading_workflow.py
│   ├── practice_exercise_workflow.py
│   └── question_answering_workflow.py
├── docker-compose.yml       # Docker orchestration
├── Dockerfile               # Container definition
└── pyproject.toml           # Dependencies
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
DEFAULT_LLM_MODEL=gemini-2.5-pro
GRADING_LLM_MODEL=gemini-2.5-pro
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
# Database — pick ONE option:
# Option A: Full DATABASE_URL (Render, Heroku, Neon, etc.)
#   When set, individual POSTGRES_* vars are ignored for connections.
#   For Render: use the EXTERNAL hostname (dpg-xxx-a.region.render.com).
#   The internal hostname (dpg-xxx-a) is only reachable from inside Render.
DATABASE_URL=postgresql://user:password@dpg-xxx-a.oregon-postgres.render.com/vinschool_ai
# Option B: Individual vars (local Docker Compose — default)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=vinschool_ai
POSTGRES_USER=vinschool
POSTGRES_PASSWORD=your_password

# Milvus — pick ONE option:
# Option A: Zilliz Cloud (managed Milvus)
MILVUS_URI=https://your-cluster.serverless.gcp-us-west1.cloud.zilliz.com
MILVUS_TOKEN=your-zilliz-api-token
# Option B: Local Milvus (Docker Compose — default)
MILVUS_HOST=localhost
MILVUS_PORT=19530
# Shared
MILVUS_COLLECTION_PREFIX=vinschool   # 4 collections: vinschool_documents, vinschool_grading_results, vinschool_student_profiles, vinschool_daily_lessons

# LLM
DEFAULT_PROVIDER=google              # openai, google, or anthropic
GEMINI_API_KEY=your_gemini_key
DEFAULT_LLM_MODEL=gemini-2.5-flash
GRADING_LLM_MODEL=gemini-2.5-flash

# Embeddings
EMBEDDING_PROVIDER=google
EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIMENSION=768

# Workflows
ENABLE_AUTO_GRADING=true
TEACHER_ESCALATION_THRESHOLD=0.6

# Daily Summary Scheduler (24-hour clock)
DAILY_SUMMARY_HOUR=18
DAILY_SUMMARY_MINUTE=0
```

### Notification Service Configuration

The Notification Service sends **one-way** messages to teachers, students, and parents.
Each notification type targets specific channels — there is no chat or reply.

| Type                     | Channel(s)    | When it fires                                                                                            |
| ------------------------ | ------------- | -------------------------------------------------------------------------------------------------------- |
| Teacher Escalation       | Email (SMTP)  | AI not confident → email teacher with link to the Google Chat space                                      |
| Low Grade Alert          | Email (SMTP)  | Student scores below threshold (default 7/10)                                                            |
| Daily Summary (students) | Google Chat   | `DailyContentWorkflow` generates AI summary → text posted to class space                                 |
| Daily Summary (parents)  | Zalo clone UI | Same AI summary → stored for REST polling                                                                |
| Daily Summary (auto)     | Both channels | `DailySummaryScheduler` fires automatically at `DAILY_SUMMARY_HOUR:DAILY_SUMMARY_MINUTE` (default 18:00) |

#### Email (SMTP) Setup

1. **Step 1: Get Gmail App Password**
   1. Go to [myaccount.google.com](https://myaccount.google.com)
   2. Navigate to **Security & sign-in** → **2-Step Verification** → Turn on 2-Step Verification
   3. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
   4. Type name in **App name**: Vinschool AI (your choice)
   5. Click **Create** and copy the 16-character password (`abcd efgh ijkl mnop`)

2. **Step 2: Configure `.env`**

```bash
ENABLE_EMAIL_NOTIFICATIONS=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password                 # abcdefghijklmnop (no spaces)
SMTP_USE_TLS=true
TEACHER_EMAIL=teacher@vinschool.edu.vn,teacher2@vinschool.edu.vn  # Comma-separated list of recipients for escalation/low-grade emails
NOTIFICATION_SENDER_EMAIL=your-email@gmail.com  # Must match SMTP_USERNAME for Gmail
NOTIFICATION_SENDER_NAME=Vinschool AI Assistant

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
Use `GOOGLE_CREDENTIALS_JSON` to pass the service account key as a single-line
JSON string (for local dev, run `cat key.json | jq -c` to get the compact form).

```bash
ENABLE_GOOGLE_CHAT_NOTIFICATIONS=true
GOOGLE_CLOUD_PROJECT_ID=your-gcp-project-id
GOOGLE_CHAT_PUBSUB_SUBSCRIPTION=projects/your-gcp-project-id/subscriptions/chat-events-sub
GOOGLE_CREDENTIALS_JSON={"type":"service_account","project_id":"...","private_key_id":"...","private_key":"...","client_email":"...@...iam.gserviceaccount.com",...}
GOOGLE_CHAT_SPACE_ID=spaces/AAAAxxxxxx
```

#### Zalo Clone UI

The Zalo channel stores plain-text messages in-memory; the frontend polls `GET /api/zalo/messages` every 3 seconds.

**How it works:**

1. `DailyContentWorkflow` generates AI summary
2. `ZaloNotifier` stores the AI's full text in `zalo_message_store`
3. Frontend (`ZaloDesktopChat.tsx` / `ZaloMobileChat.tsx`) polls and renders

**Zalo API endpoints:**

| Method   | Endpoint                       | Description                                     |
| -------- | ------------------------------ | ----------------------------------------------- |
| `GET`    | `/api/zalo/messages`           | List all stored messages                        |
| `POST`   | `/api/zalo/send-demo`          | Send the hardcoded daily summary to the Zalo UI |
| `POST`   | `/api/zalo/chat`               | `/dailysum` — hardcoded demo summary            |
| `DELETE` | `/api/zalo/messages`           | Clear all messages                              |
| `POST`   | `/api/zalo/send-daily-summary` | Send AI-generated daily summary to Zalo UI      |

**Submission API endpoints** (populated by Google Chat `/grade` command):

| Method | Endpoint                             | Description                                                  |
| ------ | ------------------------------------ | ------------------------------------------------------------ |
| `GET`  | `/api/teacher/submissions`           | List all graded submissions (includes `low_grade_threshold`) |
| `POST` | `/api/teacher/submissions/{id}/view` | Mark a submission as viewed by teacher                       |
| `GET`  | `/uploads/submissions/{file}`        | Serve submitted homework images (static mount)               |

**Student profile API endpoints:**

| Method | Endpoint                            | Description                                           |
| ------ | ----------------------------------- | ----------------------------------------------------- |
| `POST` | `/api/student/profile`              | Create or update a student profile in Milvus (upsert) |
| `GET`  | `/api/student/profile/{student_id}` | Retrieve a student profile by student_id              |

**Daily lesson API endpoints:**

| Method | Endpoint                                | Description                                                                     |
| ------ | --------------------------------------- | ------------------------------------------------------------------------------- |
| `POST` | `/api/teacher/daily-lesson`             | Upload a daily lesson entry (JSON) to Milvus                                    |
| `POST` | `/api/teacher/daily-lesson/parse-image` | Upload a lesson image, parse it with Gemini 2.5 Pro vision, and store in Milvus |
| `GET`  | `/api/teacher/daily-lessons/{date}`     | Retrieve all lessons for a specific date                                        |

> **Note:** Zalo uses an in-memory store — messages are lost when the server restarts. For production, replace with Zalo OA API integration. Submissions also use an in-memory store for the demo. Uploaded images are persisted in `uploads/submissions/` and served as static files at `/uploads/`.

#### Notification Demos

| Command                                               | What it does                                                     |
| ----------------------------------------------------- | ---------------------------------------------------------------- |
| `python -m scripts.demo_notification --dry-run`       | Preview all notification types without sending                   |
| `python -m scripts.demo_notification --escalation`    | Send teacher escalation email                                    |
| `python -m scripts.demo_notification --low-grade`     | Send low grade alert email                                       |
| `python -m scripts.demo_notification --daily-summary` | Send daily summary to Google Chat                                |
| `python -m scripts.demo_notification --daily-parent`  | Send daily summary to Zalo clone UI (requires `run_zalo_server`) |
| `python -m scripts.demo_notification --all`           | Run all demos above                                              |

### Chat Service Configuration

The Chat Service provides **bidirectional** AI Q&A. Students and parents can ask questions and receive instant answers grounded in `data/lesson.txt`.

| Channel     | Audience | Commands                                                       | Persona               | Escalation Behaviour           |
| ----------- | -------- | -------------------------------------------------------------- | --------------------- | ------------------------------ |
| Zalo clone  | Parents  | `/dailysum`                                                    | Kính ngữ (formal)     | N/A                            |
| Google Chat | Students | `/ask <question>`, `/grade`, `/hw [môn]`, `/dailysum`, `/help` | Thân thiện (friendly) | Email teacher + notify student |

> **Google Chat prefix required**: The bot responds to slash commands (`/ask`, `/grade`, `/hw`, `/dailysum`, `/help`) and demo trigger phrases (see [DEMO.md](DEMO.md)). Other @mentions are silently ignored.

**Key features:**

- **Message debouncing**: Rapid messages from the same user are batched (3 s quiet window) into a single AI request
- **Conversation history**: Per-user history (last 10 messages) for contextual follow-ups
- **Smart escalation**: When confidence is low, Google Chat triggers an email to the teacher with a link to the space; Zalo sends a polite apology only

#### Zalo commands — Quick Test

```bash
# Terminal 1 — Start standalone Zalo server
cd backend && python -m scripts.run_zalo_server

# Terminal 2 — Start frontend
cd frontend && npm run dev
```

1. Open [http://localhost:3000/zalo/desktop](http://localhost:3000/zalo/desktop) (or [http://localhost:3000/zalo/mobile](http://localhost:3000/zalo/mobile)) to access the Zalo clone UI
2. Type `/dailysum` to get the hardcoded demo summary (no API cost)

#### Google Chat commands — Quick Test

```bash
cd backend && python -m scripts.run_google_chat
```

Send in Google Chat:

- `@Vinschool Bot /ask Bài tập Toán tuần này là gì?`
- `@Vinschool Bot /grade` (kèm ảnh bài tập)
- `@Vinschool Bot /hw Toán`
- `@Vinschool Bot /dailysum`
- `@Vinschool Bot Cô ơi ngày mai có bài tập nào tới hạn không?` (demo trigger)

See [DEMO.md](DEMO.md) for the full demo trigger phrase guide.

Or test from terminal:

```bash
# Hardcoded demo summary (no API cost)
curl -X POST http://localhost:8000/api/zalo/chat \
  -H "Content-Type: application/json" \
  -d '{"sender": "Phụ huynh Alex", "text": "/dailysum"}'
```

#### Google Chat commands

Students use slash commands or demo trigger phrases when @mentioning the bot. Run the listener:

```bash
cd backend && python -m scripts.run_google_chat
```

The bot responds to `/ask`, `/grade`, `/hw`, `/dailysum`, and `/help` prefixes, plus demo trigger phrases (see [DEMO.md](DEMO.md)). For example:

- `@Vinschool Bot /ask Hôm nay học bài gì?`
- `@Vinschool Bot /grade` (attach homework images)
- `@Vinschool Bot /hw` (suggest supplementary homework based on profile)
- `@Vinschool Bot /hw Toán` (suggest homework for a specific subject)
- `@Vinschool Bot /dailysum`
- `@Vinschool Bot /help`
- `@Vinschool Bot Cô ơi ngày mai có bài tập nào tới hạn không?` (demo trigger)

The `/grade` command accepts attached images, grades them using Gemini Vision API, persists the images in `uploads/submissions/`, stores the result in the LMS dashboard, stores the grading result in Milvus (for later `/ask` retrieval), and sends a low-grade alert email if the score is below `LOW_GRADE_THRESHOLD`. All timestamps are stored in UTC with timezone info so the LMS displays the correct local time.

After grading, if the same student uses `/ask` to ask about their score or feedback, Cô Hana retrieves the relevant grading results from Milvus and answers with actual data (score, feedback, and detailed feedback).

The `/hw` command generates personalised supplementary homework suggestions based on the student's Milvus profile (strengths, weaknesses, subjects, learning level) and recent grading results. Student profiles are stored in the `vinschool_student_profiles` collection and can be created via the `POST /api/student/profile` endpoint or seeded using:

```bash
cd backend && python -m scripts.seed_student_profiles
```

The `/dailysum` and `/ask` commands use lesson content from the `vinschool_daily_lessons` Milvus collection. If the collection is empty, they fall back to reading `data/lesson.txt`. To populate the collection from the lesson file:

```bash
cd backend && python -m scripts.seed_daily_lessons
```

Every command returns a single reply — no intermediate typing indicators.

#### Chat Demos

| Command                              | What it does                       |
| ------------------------------------ | ---------------------------------- |
| `python -m scripts.demo_chat`        | Direct LLM call (no server needed) |
| `python -m scripts.demo_chat --http` | Via HTTP (needs running server)    |

#### Escalation `.env`

```bash
TEACHER_EMAIL=teacher@vinschool.edu.vn,teacher2@vinschool.edu.vn  # Comma-separated; all teachers receive escalation emails
```

## Contributing

1. Follow PEP 8 style guide
2. Use type hints
3. Write docstrings for all public functions
4. Add tests for new features
5. Update documentation

## License

Proprietary - Vinschool
