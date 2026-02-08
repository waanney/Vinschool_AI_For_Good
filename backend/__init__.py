# Vinschool AI Backend

Multi-agent educational support system.

## File Structure Overview

This backend follows Domain-Driven Design and SOLID principles with clear separation of concerns:

- **agents/**: PydanticAI agents (Teaching Assistant, Content Processor, Grading)
- **api/**: FastAPI REST API endpoints  
- **config/**: Configuration management
- **database/**: Milvus vector DB and PostgreSQL clients
- **domain/**: Domain models and repository interfaces
- **utils/**: Shared utilities (embeddings, parsing, logging)
- **workflow/**: Business process orchestration
- **data/**: Sample educational materials (preserved from original)

## Getting Started

See [README.md](README.md) for detailed setup instructions.

## Quick Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down

# Run tests
pytest
```
