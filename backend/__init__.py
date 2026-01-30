"""
Vinschool AI Backend

Multi-agent educational support system.

This backend follows Domain-Driven Design and SOLID principles with clear separation of concerns:

- agents/: PydanticAI agents (Teaching Assistant, Content Processor, Grading)
- api/: FastAPI REST API endpoints  
- config/: Configuration management
- database/: Milvus vector DB and PostgreSQL clients
- domain/: Domain models and repository interfaces
- utils/: Shared utilities (embeddings, parsing, logging)
- workflow/: Business process orchestration
- services/: Notification and other services
- data/: Sample educational materials
"""
