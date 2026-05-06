# AI Legal System

A comprehensive AI-powered legal assistant designed to provide accurate legal analysis, semantic search, and structured responses. Built with a robust backend integrating the native Google Gemini API and OpenRouter, leveraging retrieval-augmented generation (RAG) to process and synthesize complex legal documentation.

## Features

- **Document Ingestion & Chunking**: Upload legal documents and automatically process them into manageable semantic chunks for high-accuracy retrieval.
- **Retrieval-Augmented Generation (RAG)**: Leverages OpenSearch for fast, hybrid vector search to pull relevant legal context.
- **Advanced LLM Integration**: Direct integration with Google Gemini API and OpenRouter for high-quality legal reasoning and summarization.
- **Traceable Citations**: Generated responses include precise citations linking back to the original uploaded documents and exact sections.
- **Background Processing**: Robust Celery worker queue backed by Redis to handle heavy extraction and embedding tasks asynchronously.
- **Modern Web Interface**: A responsive React/Vite frontend tailored for interacting with legal data and managing ingestion jobs.

## Tech Stack

- **Backend**: Python, FastAPI, Celery, SQLAlchemy, Alembic
- **Frontend**: React, TypeScript, Vite, Tailwind CSS
- **Datastores**: PostgreSQL (relational data), OpenSearch (vector embeddings & text search), Redis (caching & task queues)
- **AI Models**: Google Gemini API, OpenRouter
- **Infrastructure**: Docker & Docker Compose

## Quick Start (Development)

### Prerequisites
- Docker and Docker Desktop
- Node.js (v18+)

### 1. Environment Setup
Clone the repository and configure your environment variables:
```bash
git clone https://github.com/youssef123tt/AI_LegalSystem.git
cd AI_LegalSystem
cp .env.example .env
```
*Note: Make sure to fill in your `GEMINI_API_KEY` and/or `OPENROUTER_API_KEY` in the `.env` file.*

### 2. Start Backend Services
Launch the entire backend infrastructure (PostgreSQL, OpenSearch, Redis, API, and Worker) using Docker Compose:

```bash
docker compose -f infra/docker-compose.yml up --build
```
- API will be available at `http://localhost:8000`
- Swagger API Docs at `http://localhost:8000/docs`

### 3. Start Web UI
Open a new terminal and start the Vite development server:

```bash
cd apps/web
npm install
npm run dev
```
The Web UI will be available at `http://localhost:5173`.

## Architecture Overview

1. **FastAPI (`apps/api`)**: Handles REST requests, document uploads, and conversational RAG endpoints.
2. **Celery Worker (`apps/worker`)**: Picks up ingestion jobs, extracts text, generates embeddings, and indexes them into OpenSearch.
3. **Database (`apps/shared`)**: Shared PostgreSQL models, Alembic migrations, and core business logic.
4. **Web Frontend (`apps/web`)**: The conversational and administrative interface.

## Documentation
For deeper dives into the implementation, refer to the `docs/` directory:
- [Architecture Overview](docs/ARCHITECTURE.md)
- [Web Stack & Plan](docs/WEB_STACK_AND_PLAN.md)
- [OpenSearch & Chunking Guide](docs/OPENSEARCH_AND_CHUNKING_GUIDE.md)
- [Database Migrations](docs/database_migrations_explained.md)

## License
MIT License
