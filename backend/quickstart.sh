#!/bin/bash
# Quick start script for Vinschool AI Backend

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  🚀 Vinschool AI Backend - Quick Start                     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your API key:"
    echo "   - For OpenAI: OPENAI_API_KEY=sk-..."
    echo "   - For Gemini: GOOGLE_API_KEY=..."
    echo "   - For Claude: ANTHROPIC_API_KEY=..."
    echo ""
    read -p "Press Enter after you've configured .env..."
fi

echo "1️⃣  Starting Docker services (Milvus + PostgreSQL)..."
docker-compose up -d milvus postgres etcd minio

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

echo ""
echo "2️⃣  Initializing Milvus collections..."
python scripts/init_milvus.py

echo ""
echo "3️⃣  Starting backend API..."
echo "   You can access:"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - Milvus UI: http://localhost:3000"
echo ""

# Check if running in dev mode
if [ "$1" == "dev" ]; then
    echo "🔧 Running in DEVELOPMENT mode with hot reload..."
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
else
    echo "🚀 Starting full stack with Docker Compose..."
    docker-compose up -d
    echo ""
    echo "✅ All services started!"
    echo ""
    echo "📊 Service Status:"
    docker-compose ps
    echo ""
    echo "📝 View logs with: docker-compose logs -f backend"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ✅ Vinschool AI Backend is ready!                         ║"
echo "╚════════════════════════════════════════════════════════════╝"
