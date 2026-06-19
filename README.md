# New Modular Monolith Backend

This is a clean, minimal backend skeleton using FastAPI, SQLAlchemy (async), and Alembic.

## Setup

1. **Environment Variables**:
   Copy `.env.example` to `.env` and fill in the values.
   ```bash
   cp .env.example .env
   ```

2. **Install Dependencies**:
   Create a virtual environment and install dependencies.
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Run the Server**:
   ```bash
   uvicorn main:app --reload
   ```

## Architecture Overview
This project follows a Modular Monolith architecture.
- `src/core/`: Configuration, database setup, exceptions, security, etc.
- `src/common/`: Shared base classes, enums, utils.
- `src/infrastructure/`: External integrations (e.g., mail).
- `src/modules/`: Feature modules. Each module is self-contained with its own models, schemas, repository, service, and router.
