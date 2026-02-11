#  Quick Start Guide - Vinschool AI

## Cách 1: Demo Nhanh (Không cần Docker)

Test các agents trực tiếp với demo script:

```bash
# 1. Setup môi trường
cp .env.example .env
# Sửa .env:
# - GEMINI_API_KEY=your-key
# - EMBEDDING_PROVIDER=google
# - EMBEDDING_MODEL=text-embedding-004

# 2. Install dependencies (dùng UV cho local - nhanh hơn)
uv pip install -e .  # hoặc: pip install -e .

# 3. Chạy demo
python scripts/demo.py
```

> **Note:** UV khuyên dùng cho local development. Docker build tự động dùng pip.

**Demo script sẽ test:**
- ✅ Teaching Assistant: Trả lời câu hỏi về phân số
- ✅ Content Summarization: Tóm tắt bài học
- ✅ Exercise Generation: Tạo bài tập cá nhân hóa
- ✅ Homework Grading: Chấm bài tự động với feedback

---

## Cách 2: Chạy Full System (Docker)

### Quick Start Script

```bash
# Chạy tất cả trong 1 lệnh
./quickstart.sh

# Hoặc dev mode với hot reload
./quickstart.sh dev
```

### Manual Setup

```bash
# 1. Setup environment
cpenv.example .env
# Edit .env với API key

# 2. Start services
docker-compose up -d

# 3. Init Milvus
python scripts/init_milvus.py

# 4. Access
# - API: http://localhost:8000/docs
# - Milvus UI: http://localhost:3000
```

---

## Test API với cURL

### 1. Upload Document (Teacher)

```bash
# Tạo file test
echo "Bài học về phân số: 1/2 + 1/4 = 3/4" > lesson.txt

curl -X POST "http://localhost:8000/api/teacher/upload" \
  -F "file=@lesson.txt" \
  -F "title=Lesson: Fractions" \
  -F "subject=Mathematics" \
  -F "grade=9" \
  -F "teacher_id=$(uuidgen)" \
  -F "generate_summary=true"
```

### 2. Ask Question (Student)

```bash
curl -X POST "http://localhost:8000/api/student/question" \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "student-123",
    "question": "How do I add fractions?",
    "grade": 9,
    "subject": "Mathematics"
  }'
```

### 3. Submit Homework (Student)

```bash
# Tạo bài làm
echo "1/2 + 1/4 = 3/4" > homework.txt

curl -X POST "http://localhost:8000/api/student/homework/submit" \
  -F "assignment_id=$(uuidgen)" \
  -F "student_id=student-123" \
  -F "file=@homework.txt" \
  -F "auto_grade=true"
```

---

##  Chọn LLM Provider

### OpenAI (Default)
```bash
DEFAULT_PROVIDER=openai
OPENAI_API_KEY=sk-your-key
DEFAULT_LLM_MODEL=gpt-4-turbo-preview
```

### Google Gemini (Khuyên dùng - free quota tốt)
```bash
DEFAULT_PROVIDER=google
GEMINI_API_KEY=your-gemini-key  # Get tại: https://aistudio.google.com/
DEFAULT_LLM_MODEL=gemini-2.0-flash-exp
```

### Anthropic Claude
```bash
DEFAULT_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-key
DEFAULT_LLM_MODEL=claude-3-opus-20240229
```

---

##  Monitoring

```bash
# View logs
docker-compose logs -f backend

# Check status
docker-compose ps

# Stop all
docker-compose down
```

---

## ⚡ Development Tips

```bash
# Install với uv (nhanh hơn)
uv pip install -e .[dev]

# Run tests
pytest

# Format code
black .
ruff check .

# Run local (không Docker)
uvicorn api.main:app --reload
```

---

##  Troubleshooting

**Lỗi: "OPENAI_API_KEY not configured"**
→ Check file `.env` có đúng API key chưa

**Lỗi: Milvus connection failed**
→ Chạy: `docker-compose up -d milvus`

**Port 8000 đã được dùng**
→ Sửa port trong `docker-compose.yml` hoặc kill process

---

## 📚 Next Steps

1. ✅ Test demo script → hiểu workflow
2. ✅ Start API → test với Swagger UI
3. ✅ Upload real documents → build knowledge base
4. ✅ Integrate frontend → build UI

**Docs:** http://localhost:8000/docs
