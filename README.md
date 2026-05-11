[![Python](https://img.shields.io/badge/Python-3.13-3776AB.svg?style=flat&logo=python&logoColor=ffd343)](https://docs.python.org/3.13/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![CI](https://img.shields.io/github/actions/workflow/status/javidahmed64592/python-template-server/ci.yml?branch=main&style=flat-square&label=CI&logo=github)](https://github.com/javidahmed64592/python-template-server/actions/workflows/ci.yml)
[![Build](https://img.shields.io/github/actions/workflow/status/javidahmed64592/python-template-server/build.yml?branch=main&style=flat-square&label=Build&logo=github)](https://github.com/javidahmed64592/python-template-server/actions/workflows/build.yml)
[![Docs](https://img.shields.io/github/actions/workflow/status/javidahmed64592/python-template-server/docs.yml?branch=main&style=flat-square&label=Docs&logo=github)](https://github.com/javidahmed64592/python-template-server/actions/workflows/docs.yml)
[![Docker](https://img.shields.io/github/actions/workflow/status/javidahmed64592/python-template-server/docker.yml?branch=main&style=flat-square&label=Docker&logo=github)](https://github.com/javidahmed64592/python-template-server/actions/workflows/docker.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<!-- omit from toc -->
# Python Template Server

A production-ready FastAPI server template with built-in authentication, rate limiting and security headers.
This repository provides a solid foundation for building secure, observable FastAPI applications.

<!-- omit from toc -->
## Table of Contents
- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Managing the Container](#managing-the-container)
- [Using as a Template](#using-as-a-template)
- [License](#license)

## Features

- **TemplateServer Base Class**: Reusable foundation with middleware, auth, and rate limiting
- **FastAPI Framework**: Modern, fast, async-ready web framework
- **CORS Support**: Configurable cross-origin resource sharing for frontend integration
- **Static File Serving**: FastAPI's StaticFiles mounting with custom 404.html support
- **Docker Support**: Multi-stage builds with docker-compose orchestration
- **Production Patterns**: Token generation, SSL certificate handling, health checks

## Architecture

This project uses a **`TemplateServer` base class** that encapsulates cross-cutting concerns:

- **Request Logging**: All requests/responses logged with client IP tracking
- **Security Headers**: HSTS/CSP/X-Frame-Options automatically applied
- **API Key Verification**: SHA-256 hashed tokens with secure validation
- **Rate Limiting**: Configurable limits using `slowapi` (in-memory/Redis/Memcached)
- **CORS Middleware**: Optional cross-origin support for frontend applications
- **Static File Serving**: Serve SPAs or static assets using FastAPI's StaticFiles mounting

**Application-specific servers** (like `ExampleServer` in `main.py`) extend `TemplateServer` to implement domain-specific endpoints and business logic.
The base class handles all infrastructure concerns, letting you focus on your API functionality.

## Quick Start

### Installation

Download the latest release from [GitHub Releases](https://github.com/javidahmed64592/python-template-server/releases).

### Configuration

Rename `.env.example` to `.env` and edit it to configure the server.

- `HOST`: Server host address (default: localhost)
- `PORT`: Server port (default: 443)
- `API_TOKEN_HASH`: Leave blank to auto-generate on first run, or provide your own token hash

### Managing the Container

```sh
# Start the container
docker compose up -d

# Stop the container
docker compose down

# Update to the latest version
docker compose pull && docker compose up -d

# View the logs
docker compose logs -f python-template-server
```

**Note:** You may need to add your user to the Docker group and log out/in for permission changes to take effect:
```sh
sudo usermod -aG docker ${USER}
```

## Using as a Template

To create your own server:

1. **Create a subclass of `TemplateServer`** (see `python_template_server/main.py:ExampleServer` as reference)
2. **Implement required methods**:
   - `validate_config()`: Validate your config model
   - `setup_routes()`: Define your API endpoints
3. **Add custom routes** to the `setup_routes()` method
4. **Configure** via `configuration/config.json`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
