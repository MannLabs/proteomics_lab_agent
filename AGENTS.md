# AGENDS.md

This file provides guidance to AI coding agents when working with code in this repository.

## Project Overview

This is a multimodal agentic AI framework for proteomics laboratory work that uses Google's Agent Development Kit (ADK), Gemini models, and Vertex AI. The system captures and shares practical expertise by linking written instructions to real-world laboratory work through video analysis.

## Architecture

### Root Agent and Sub-Agents

The project uses a hierarchical agent architecture with a root orchestrator and specialized sub-agents:

- **Root Agent** (`proteomics_lab_agent/agent.py`): Orchestrates all sub-agents and provides common tools like datetime functions
- **Sub-Agents** (`proteomics_lab_agent/sub_agents/`):
  - `protocol_generator_agent`: Analyzes video/audio to generate formatted protocols
  - `lab_note_generator_agent`: Compares researcher actions on video against reference protocols
  - `lab_knowledge_agent`: Retrieves documents from Confluence via MCP server
  - `instrument_agent`: Monitors mass spectrometer performance via AlphaKraken MCP server
  - `qc_memory_agent`: Logs QC ratings using local SQLite database via MCP server
  - `video_analyzer_agent`: Video analysis utilities

### Sub-Agent Structure

Each sub-agent follows this pattern:
```
sub_agents/<agent_name>/
├── __init__.py          # Exports the agent
├── agent.py             # Agent definition with ADK Agent/LlmAgent
├── prompt.py            # Agent-specific prompt/instructions
└── [additional modules] # Agent-specific utilities
```

### MCP Server Integration

The project uses MCP (Model Context Protocol) servers for external integrations:

- **AlphaKraken MCP**: Proteomics analysis platform integration (Docker container)
- **Confluence MCP**: Knowledge management system integration (Docker container)
- **QC Memory MCP**: Local SQLite database server (`qc_memory_agent/server.py`)

MCP servers are integrated via:
- `MCPToolset` with `StreamableHTTPServerParams` for HTTP-based servers (AlphaKraken, Confluence)
- `MCPToolset` with `StdioServerParameters` for local stdio-based servers (QC Memory)

### Database Schema

The QC Memory agent uses SQLite with schema versioning:
- Database location: `proteomics_lab_agent/sub_agents/qc_memory_agent/database.db`
- Schema management: `create_db.py` creates database, `db_interface.py` provides CRUD operations
- Schema version checking enforced on every connection (see `get_db_connection()` in `db_interface.py`)
- Compatible schema version defined by `COMPATIBLE_SCHEMA_VERSION` constant

## Development Commands

### Environment Setup

1. Create and activate virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
pip install -r requirements/requirements.txt
pip install -r requirements/requirements_development.txt  # for development
```

3. Authenticate with Google Cloud:
```bash
gcloud auth login
gcloud init
```

4. Configure environment variables:
   - Copy `.env.example` to `.env` and fill in values
   - Copy `.env.secrets.example` to `.env.secrets` and fill in secrets

### Running the Agent

Start MCP server containers (from project root):
```bash
docker compose --env-file ./.env.secrets --env-file ./.env up confluence_mcp alphakraken_mcp
```

Run the agent (in separate terminal):
```bash
adk run proteomics_lab_agent              # CLI interface
adk web                                    # Web UI (local only)
adk web --host 0.0.0.0                    # Web UI (accessible on network)
```

Or run via Docker Compose (full deployment):
```bash
docker compose --env-file ./.env.secrets --env-file ./.env up
```

### Testing and Code Quality

Run pre-commit hooks:
```bash
pre-commit run --all-files
```

Individual checks:
```bash
ruff format .                    # Format code
ruff check --fix .               # Lint and auto-fix
detect-secrets scan --exclude-files testfiles --exclude-lines '"(hash|id|image/\w+)":.*' > .secrets.baseline
detect-secrets audit .secrets.baseline
```

### Docker Operations

Build containers:
```bash
docker compose --env-file ./.env.secrets --env-file ./.env build
```

Start in production (detached):
```bash
docker compose --env-file ./.env.secrets --env-file ./.env up -d
```

Stop containers:
```bash
docker container stop python_lab_agent alphakraken_mcp confluence_mcp
```

### Database Operations

Check QC Memory database (requires sqlite3):
```bash
sqlite3 proteomics_lab_agent/sub_agents/qc_memory_agent/database.db
```

## Configuration

### Model Configuration

Models are configured in `proteomics_lab_agent/config.py`:
- `model`: Default model for generation tasks (currently "gemini-2.5-flash")
- `analysis_model`: Model for video analysis (currently "gemini-2.5-pro")
- `temperature`: Controls output randomness (default 0.9)

### Environment Variables

Key environment variables in `.env`:
- `GOOGLE_CLOUD_PROJECT`: GCP project ID
- `GOOGLE_CLOUD_STORAGE_BUCKET`: Bucket for video storage
- `ALPHAKRAKEN_MCP_URL`: AlphaKraken MCP server URL (differs between local/docker)
- `CONFLUENCE_MCP_URL`: Confluence MCP server URL (differs between local/docker)
- `SPACE_KEY`, `PROTOCOL_PAGE`, `LAB_NOTE_PAGE`: Confluence configuration
- `LOCAL_FOLDER_PATH`: Local path for video files

Secret variables in `.env.secrets`:
- AlphaKraken database credentials
- Confluence API token and credentials
- Service account file path

## Code Style and Linting

Project uses Ruff for linting and formatting with extensive rule set (see `pyproject.toml`).

Notable ignored rules:
- `E501`: Line length (ruff auto-wraps code)
- `S101`: Allow assert statements
- `D104`: Missing docstring in public package
- `E402`: Module import not at top (for notebooks)
- `S608`: SQL injection checks disabled (uses parameterized queries)

## Important Patterns

### Adding a New Sub-Agent

1. Create directory under `proteomics_lab_agent/sub_agents/<agent_name>/`
2. Implement `agent.py` with ADK Agent or LlmAgent
3. Define instructions in `prompt.py`
4. Export agent in `__init__.py`
5. Import and register in root `proteomics_lab_agent/agent.py`

### Video Processing

Videos must be uploaded to Google Cloud Storage before processing. The agent expects:
- Videos in GCS bucket (configured via `GCS_BUCKET_PATH`)
- Local path mapping for development (via `LOCAL_FOLDER_PATH`)
- Video analysis uses `config.analysis_model` (higher capacity model)

### Error Handling

Custom exception hierarchy in `db_interface.py`:
- `DatabaseError`: Base exception for database operations
- `ValidationError`: Data validation errors
- `SessionError`: Session processing errors

Use specific helper functions for common errors (e.g., `_raise_schema_not_found_error()`)

## Jupyter Notebooks

Located in `nbs/`:
- `database_test.ipynb`: Database function development/debugging
- `protocolGeneration.ipynb`: Protocol generation pipeline development
- `videoToLabNotes_adk_workflow.ipynb`: Lab note generation pipeline development

## Pre-commit Hooks

The CI pipeline enforces all pre-commit checks. Key hooks:
- `ruff-format` and `ruff`: Code formatting and linting
- `detect-secrets`: Prevent secret commits (baseline in `.secrets.baseline`)
- `no-commit-to-branch`: Prevent direct commits to main
- Standard checks: YAML/JSON validation, trailing whitespace, merge conflicts

## Deployment

The project supports both development and production deployment via Docker Compose. The deployment includes three containers:
- `python_lab_agent`: Main agent application
- `alphakraken_mcp`: Proteomics analysis MCP server
- `confluence_mcp`: Knowledge management MCP server

Persistent data is mounted from `deployment_data/` including:
- Evaluation datasets (`.evalset.json` files)
- QC Memory database (`database.db`)