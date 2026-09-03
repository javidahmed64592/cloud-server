# Cloud Server - AI Agent Instructions

## Project Overview

A full-stack cloud file storage server with FastAPI backend and Next.js frontend. Built on `python-template-server` as foundation.
Provides file upload/download, thumbnail generation, metadata management, and a modern web UI for browsing files.
Backend extends `TemplateServer` from python-template-server, frontend is a React SPA with TypeScript.

## Architecture & Key Components

### Full Stack Architecture

- **Backend**: FastAPI server (`CloudServer` class) extending `python-template-server.TemplateServer`
- **Frontend**: Next.js 16 + React 19 + TypeScript, built as static export and served by FastAPI
- **Database**: SQLite for file metadata (SQLAlchemy ORM)
- **Storage**: Local filesystem with thumbnail generation for images/videos
- **Deployment**: Multi-stage Docker build (frontend → backend → runtime)

### Backend Architecture (`cloud_server/`)

**Entry Point**: `main.py:run()` → instantiates `CloudServer` (subclass of `TemplateServer`) → calls `.run()`

**CloudServer Class** (`server.py`):

- Extends `python-template-server.TemplateServer` for auth, rate limiting, CORS, security headers
- Initializes storage directories (`server/storage/`, `server/storage/.thumbnails/`)
- Configures `FilesMetadataDatabaseManager` for file metadata persistence
- Synchronizes storage with database on startup
- Generates thumbnails for existing files on startup

**File Operations Router** (`routers/files_router.py`):

- `GET /api/files/` - List all files with metadata
- `POST /api/files/` - Upload file (chunked streaming, size validation)
- `GET /api/files/{file_id}` - Download file
- `DELETE /api/files/{file_id}` - Delete file and metadata
- `PATCH /api/files/{file_id}/metadata` - Update file metadata (rename, move)
- `GET /api/files/{file_id}/thumbnail` - Get thumbnail for images/videos

**Thumbnail Generator** (`thumbnail_generator.py`):

- Generates 200x200 thumbnails for images (PNG, JPG, GIF, WebP) using Pillow
- Generates video thumbnails from first frame using OpenCV
- Stores thumbnails in `.thumbnails/` subdirectory
- Automatically syncs with storage on server startup

**Database Manager** (`db/files_metadata_database_manager.py`):

- SQLAlchemy ORM with SQLite backend
- Stores file metadata: id, filename, parent_directory, mime_type, size, uploaded_at, updated_at
- Synchronizes with storage directory (adds missing, removes orphaned)
- CRUD operations for file metadata

### Frontend Architecture (`cloud-server-frontend/`)

**Framework**: Next.js 16 (App Router) + React 19 + TypeScript + Tailwind CSS

**Key Routes**:

- `/` - Redirects to `/drive`
- `/drive` - File browser interface (main app)
- `/login` - Authentication page
- `/not-found` - 404 page

**State Management**:

- `AuthContext` - Authentication state, API key management
- Zustand (via `contexts/`) for client-side state

**API Client** (`lib/api.ts`):

- Axios-based client with error handling
- Proxies to backend in dev, same-origin in production
- Functions mirror backend routes: `listFiles()`, `uploadFile()`, `deleteFile()`, etc.

**Key Components** (`components/`):

- `Navigation` - App header with health indicator
- `HealthIndicator` - Backend health status badge
- `drive/FileGrid` - Grid view of files and folders
- `drive/FileCard` - Individual file display with thumbnail
- `drive/FolderCard` - Folder display
- `drive/UploadButton` - File upload dialog
- `drive/FileViewer` - File preview/download modal
- `drive/MoveDialog` - Move/rename file dialog
- `drive/Breadcrumb` - Directory navigation

**Testing**: Jest + React Testing Library, 100% coverage goal

### Configuration System

**Backend Config** (`configuration/config.json`):

```json
{
  "security": {...},           // HSTS, CSP headers
  "cors": {...},              // CORS settings (enabled for frontend)
  "rate_limit": {...},        // Rate limiting (100/minute)
  "json_response": {...},     // JSON serialization
  "db": {
    "db_directory": "data",
    "files_metadata_db_filename": "files_metadata.db"
  },
  "storage_config": {
    "upload_chunk_size_kb": 8,
    "max_file_size_mb": 2000,
    "thumbnail_size": [200, 200]
  }
}
```

**Environment Variables** (`.env`):

- `HOST` - Server host (default: 0.0.0.0)
- `PORT` - Server port (default: 8000)
- `NGINX_PROXY_URL` - Optional Nginx proxy URL

### Docker Multi-Stage Build

**Stage 1 (frontend-builder)**:

- Node 25 Alpine base
- Builds Next.js static export to `out/` directory
- All frontend assets become static HTML/CSS/JS

**Stage 2 (backend-builder)**:

- Python 3.13 slim base
- Installs `uv` for dependency management
- Builds Python wheel from `cloud_server/` source
- Copies built frontend from Stage 1 to `static/` directory

**Stage 3 (runtime)**:

- Python 3.13 slim base
- Installs wheel + dependencies via `uv`
- Copies configuration, sets up entrypoint
- Health check: `curl -k https://localhost:8000/api/health`

## Developer Workflows

### Essential Commands

**Backend Development**:

```bash
# Setup (first time)
uv sync                          # Install Python dependencies
uv run generate-new-token        # Generate API key for testing

# Development
uv run cloud-server              # Start backend server (http://localhost:8000)
uv run -m pytest                 # Run backend tests with coverage
uv run -m ty check .             # Type checking
uv run -m ruff check .           # Linting
```

**Frontend Development**:

```bash
cd cloud-server-frontend
npm install                      # Install dependencies
npm run dev                      # Start dev server (http://localhost:3000)
npm test                         # Run tests
npm run test:coverage            # Run tests with coverage
npm run type-check               # TypeScript checking
npm run lint                     # ESLint
npm run format                   # Prettier
npm run quality                  # All quality checks
```

**Docker Development**:

```bash
docker compose up --build -d     # Build + start container
docker compose logs -f cloud-server  # View logs
docker compose down              # Stop and remove container
```

### Testing Patterns

**Backend Tests** (`tests/`):

- **Fixtures**: All tests use `conftest.py` fixtures, auto-mock `pyhere.here()` to tmp_path
- **Config Mocking**: Use fixtures for consistent test config
- **Integration Tests**: FastAPI TestClient with auth headers
- **Coverage Target**: 80% (configured in pyproject.toml)
- **Pattern**: Unit tests per module (test\_\*.py) + integration tests (test_server.py)

**Frontend Tests** (`cloud-server-frontend/src/**/__tests__/`):

- **Framework**: Jest + React Testing Library + jest-dom
- **Mocking**: Mock API calls with Jest
- **Coverage**: 100% goal, HTML reports in `coverage/`
- **Pattern**: Component tests in `__tests__/` subdirectories

### Project-Specific Conventions

**Backend Code Organization**:

- `server.py` - CloudServer class (main server)
- `main.py` - Entry point and CLI
- `models.py` - Pydantic models (config + API responses)
- `routers/` - FastAPI routers (files_router.py)
- `db/` - Database managers (SQLAlchemy)
- `thumbnail_generator.py` - Image/video thumbnail generation

**Frontend Code Organization**:

- `src/app/` - Next.js pages (App Router)
- `src/components/` - React components
- `src/lib/` - API client and utilities
- `src/contexts/` - React context providers

**API Design**:

- **Prefix**: All routes under `/api`
- **Authentication**: API key via `X-API-Key` header (inherited from template server)
- **Response Models**: All endpoints return `BaseResponse` subclasses with code/message/timestamp
- **File Upload**: Chunked streaming (8KB chunks), size validation (max 2GB)
- **Error Handling**: HTTPException with proper status codes

**Database Patterns**:

- **ORM**: SQLAlchemy with declarative models
- **Timestamps**: Unix timestamps (integers) for uploaded_at/updated_at
- **Paths**: Store relative paths from storage root, compute absolute at runtime
- **Sync**: Database synchronized with filesystem on startup

**Thumbnail Generation**:

- **Images**: Pillow with LANCZOS resampling, preserve aspect ratio
- **Videos**: OpenCV extracts first frame, then Pillow for resize
- **Storage**: `.thumbnails/` subdirectory with same structure as storage
- **Formats**: Always output as PNG for consistency
- **Async**: Generated during upload, served as FileResponse

### Security Patterns

- **Never log secrets**: Print tokens via `print()`, not `logger`
- **Path validation**: Use Pydantic validators, Path objects
- **Security headers**: HSTS, CSP, X-Frame-Options (inherited from template server)
- **API authentication**: SHA-256 hashed tokens with X-API-Key header
- **CORS**: Enabled for frontend, configurable origins
- **File validation**: Size limits, MIME type detection

### Logging Format

- Format: `[DD/MM/YYYY | HH:MM:SS] (LEVEL) module: message`
- Request tracking: `"Request: GET /api/files/ from 192.168.1.1"`
- File operations: `"Uploaded file: example.jpg (1.5 MB)"`
- Database sync: `"Synchronized 42 files metadata entries with storage directory."`

## Development Constraints

### Backend Testing Requirements

- Use fixtures for CloudServer instantiation
- Test async endpoints with `@pytest.mark.asyncio`
- Mock file I/O operations for unit tests
- Test thumbnail generation with sample images/videos
- Verify database synchronization logic

### Frontend Testing Requirements

- Mock all API calls with Jest
- Test user interactions with @testing-library/user-event
- Test async state updates and loading states
- Test error handling and toast notifications
- Verify routing and navigation

### CI/CD Validation

All PRs must pass:

**Backend CI**:

1. `validate-pyproject` - pyproject.toml schema validation
2. `ruff` - linting (120 char line length)
3. `ty` - 100% type coverage (strict mode)
4. `pytest` - 80% code coverage
5. `bandit` - security scanning
6. `pip-audit` - dependency vulnerability audit

**Frontend CI**:

1. `type-check` - TypeScript validation
2. `lint` - ESLint
3. `format` - Prettier
4. `test` - Jest with coverage

**Docker CI**:

1. `build` - Multi-stage Docker build
2. `health-check` - Verify container starts and responds

## Quick Reference

### Key Backend Files

- `cloud_server/server.py` - CloudServer class
- `cloud_server/main.py` - Entry point
- `cloud_server/models.py` - Pydantic models
- `cloud_server/routers/files_router.py` - File operations API
- `cloud_server/db/files_metadata_database_manager.py` - Database manager
- `cloud_server/thumbnail_generator.py` - Thumbnail generation
- `configuration/config.json` - Server configuration
- `tests/` - Backend tests

### Key Frontend Files

- `cloud-server-frontend/src/app/drive/page.tsx` - Main file browser
- `cloud-server-frontend/src/lib/api.ts` - API client
- `cloud-server-frontend/src/components/drive/` - File browser components
- `cloud-server-frontend/src/contexts/AuthContext.tsx` - Auth state
- `cloud-server-frontend/package.json` - Dependencies and scripts

### Storage Structure

```
server/
  storage/                    # User files
    .thumbnails/              # Generated thumbnails
      <file_id>.png          # Thumbnail for file_id
    file1.jpg
    folder1/
      file2.pdf
data/
  files_metadata.db          # SQLite database
```

### API Endpoints

- `GET /api/health` - Health check
- `GET /api/auth_enabled` - Check if auth is enabled
- `GET /api/files/` - List all files
- `POST /api/files/` - Upload file
- `GET /api/files/{id}` - Download file
- `DELETE /api/files/{id}` - Delete file
- `PATCH /api/files/{id}/metadata` - Update metadata
- `GET /api/files/{id}/thumbnail` - Get thumbnail
