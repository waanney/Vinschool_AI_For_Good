# Demo Guide — Hardcoded Responses

This document describes the **demo trigger phrases** used during live presentations.
These phrases produce instant, hardcoded responses — no AI API cost and no network
latency — so the demo always works reliably.

## Overview

| #   | Trigger Phrase                  | Simulates                    | Escalation? |
| --- | ------------------------------- | ---------------------------- | ----------- |
| 1   | `Cô ơi ngày mai có...`          | `/ask` — student question    | No          |
| 2   | `Cô ơi con chưa hiểu...`        | `/ask` — student question    | No          |
| 3   | `Cô ơi mai khai mạc...`         | `/ask` — off-topic question  | **Yes**     |
| 4   | `Cô ơi chấm bài...` + images    | `/grade` — homework grading  | No          |
| 4   | `Cô ơi chấm bài...` (no images) | `/grade` — no images case    | No          |
| 5   | `Cô ơi cho con bài tập...`      | `/hw` — homework suggestions | No          |

Example to copy-paste:

```txt
1. Cô ơi ngày mai có bài tập nào tới hạn cần nộp không cô?

2. Cô ơi con chưa hiểu tại sao thả hai chiếc dù xuống cùng lúc, chiếc dù lớn hơn sẽ rơi chậm hơn ạ.

3. Cô ơi mai khai mạc Edurun thì cần mặc đồng phục như thế nào ạ?

4. Cô ơi chấm bài giúp con với ạ.

5. Cô ơi cho con bài tập để luyện thêm về cộng trừ phân số với mẫu số khác nhau với ạ.
```

> **Channel**: Google Chat only. Zalo only supports `/dailysum` (hardcoded parent-facing summary).

## How It Works

When a student sends a message in Google Chat that **starts with** one of the trigger
phrases (case-insensitive), the bot skips the AI pipeline entirely and returns the
corresponding hardcoded response.

The matching is prefix-based: `"Cô ơi ngày mai có bài tập"` matches because it
starts with `"cô ơi ngày mai có"`.

### Where Are the Responses Defined?

All hardcoded responses are defined in [google_chat_listener.py](services/chat/google_chat_listener.py).

Look for the `DEMO_HARDCODED` dict and `DEMO_GRADE_NO_IMAGES`
class attributes on `GoogleChatListener`.

### Editing Responses Before the Demo

1. Open `backend/services/chat/google_chat_listener.py`
2. Find the `DEMO_HARDCODED` dictionary (search for `DEMO_HARDCODED`)
3. Replace the placeholder text with your scripted responses
4. For the `/grade` demo, edit the grade handler in `_handle_demo_phrase` and `DEMO_GRADE_NO_IMAGES`
5. Restart the server

## Detailed Trigger Descriptions

### 1. `Cô ơi ngày mai có...` — Ask (No Escalation)

**Simulates**: `/ask` with a confident answer.

The student asks about tomorrow's schedule/homework. The response should show
Cô Hana answering confidently from lesson data.

**Example message**:

```txt
@Vinschool Bot Cô ơi ngày mai có bài kiểm tra Toán không ạ?
```

### 2. `Cô ơi con chưa hiểu...` — Ask (No Escalation)

**Simulates**: `/ask` with a confident answer.

The student asks for help understanding a lesson topic. The response should
show Cô Hana explaining a concept in an age-appropriate manner.

**Example message**:

```txt
@Vinschool Bot Cô ơi con chưa hiểu bài phân số
```

### 3. `Cô ơi mai khai mạc...` — Ask (Escalation)

**Simulates**: `/ask` where the question is off-topic / outside lesson scope.

The student asks something unrelated to the curriculum. The response should
show Cô Hana politely indicating she cannot answer and suggesting the student
ask the homeroom teacher. In production this would trigger an email escalation.

**Example message**:

```txt
@Vinschool Bot Cô ơi mai khai mạc hội thao lúc mấy giờ
```

### 4. `Cô ơi chấm bài...` — Grade

**Simulates**: `/grade`

**With images**: The student sends homework photos for grading. The bot returns
a hardcoded score and feedback. A demo submission is also stored in the
in-memory submission store so it appears on the **Teacher LMS Dashboard**
(the frontend TeacherHomeworkTable component polls GET /api/teacher/submissions).

**Without images**: The bot replies asking the student to attach images.

**Example message (with images)**:

```txt
@Vinschool Bot Cô ơi chấm bài giúp con  [📎 ảnh bài tập]
```

### 5. `Cô ơi cho con bài tập...` — Homework Suggestions

**Simulates**: `/hw`

The student asks for extra practice. The bot returns hardcoded personalised
homework suggestions.

**Example message**:

```txt
@Vinschool Bot Cô ơi cho con bài tập Toán thêm
```

## Running the Demo

### Option A: Demo Server (recommended for live demo)

```bash
cd backend
python -m scripts.run_google_chat
```

This starts a lightweight server on port 8000 with the Google Chat Pub/Sub
listener. No PostgreSQL or Milvus needed. The LMS dashboard endpoint
(`GET /api/teacher/submissions`) is included.

### Option B: Full Backend

```bash
cd backend
uvicorn api.main:app --reload
```

The full backend includes the Google Chat listener automatically and also
supports the demo trigger phrases.

### Frontend (Teacher LMS Dashboard)

```bash
cd frontend
npm run dev
```

Open [http://localhost:3000/teacher/dashboard](http://localhost:3000/teacher/dashboard) to see the Teacher Dashboard. When the demo `/grade`
trigger fires (with images), the graded submission will appear in the homework
table within 5 seconds (polling interval).

## Zalo Demo

Zalo supports only the `/dailysum` command, which returns the hardcoded
parent-facing daily summary. No AI cost.

```bash
# Terminal 1 — Zalo server
cd backend && python -m scripts.run_zalo_server

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Open [http://localhost:3000/zalo/desktop](http://localhost:3000/zalo/desktop) and type `/dailysum`.

## Other Slash Commands

These commands are also available (not demo trigger phrases):

| Command           | Description                                  |
| ----------------- | -------------------------------------------- |
| `/ask <question>` | AI Q&A (Cô Hana answers from lesson data)    |
| `/grade` + images | AI grading (Gemini vision)                   |
| `/hw [môn]`       | AI homework suggestions (personalised)       |
| `/dailysum`       | Hardcoded daily summary (real sent at 18:00) |
| `/help`           | List available commands                      |
