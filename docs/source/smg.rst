Software Maintenance Guide
===========================

This document outlines how to configure and setup a development environment to work on |project_name|.

Backend (Python)
----------------

.. image:: https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=ffd343
   :target: https://docs.python.org/3.13/
   :alt: Python

.. image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json&style=flat-square
   :target: https://github.com/astral-sh/uv
   :alt: uv

.. image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json&style=flat-square
   :target: https://github.com/astral-sh/ruff
   :alt: Ruff

.. image:: https://img.shields.io/badge/mypy-Latest-2A6DB2?style=flat-square
   :target: https://mypy.readthedocs.io/
   :alt: Mypy

.. image:: https://img.shields.io/badge/Sphinx-Latest-000000?style=flat-square&logo=sphinx&logoColor=white
   :target: https://www.sphinx-doc.org/
   :alt: Sphinx

.. image:: https://img.shields.io/badge/FastAPI-Latest-009688?style=flat-square&logo=fastapi&logoColor=white
   :target: https://fastapi.tiangolo.com
   :alt: FastAPI

Installing Dependencies
~~~~~~~~~~~~~~~~~~~~~~~

This repository is managed using the ``uv`` Python project manager: https://docs.astral.sh/uv/

Install the required dependencies:

.. code-block:: sh

   uv sync

To include extra dependencies:

.. code-block:: sh

   uv sync --extra dev
   uv sync --extra docs
   uv sync --all-extras

Architecture Overview
~~~~~~~~~~~~~~~~~~~~~

This module uses a ``TemplateServer`` base class that provides reusable infrastructure for building FastAPI applications.

**TemplateServer Responsibilities:**

- **Middleware Setup:** Request logging, security headers, and optional CORS
- **Authentication:** API key verification with SHA-256 hashing
- **Rate Limiting:** Configurable request throttling per endpoint
- **Static File Serving:** FastAPI's StaticFiles mounting with custom 404.html support
- **Configuration:** JSON-based config loading and validation

**Application-Specific Servers:**

- Define custom API endpoints via ``setup_routes()``
- Implement domain-specific business logic
- Validate custom configuration models via ``validate_config()``

This separation ensures that cross-cutting concerns (security, logging etc.) are handled by the base class, while application developers focus on building their API functionality.

Setting Up Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~

Before running the server, you need to generate an API authentication token.

.. code-block:: sh

   cp .env.example .env       # Set HOST and PORT to override defaults
   uv run generate-new-token  # Set API_TOKEN_HASH variable

This command:

- Creates a cryptographically secure token using Python's ``secrets`` module
- Hashes the token with SHA-256 for safe storage
- Stores the hash in ``.env`` file
- Displays the plain token (save it securely - it won't be shown again)

Running the Backend
~~~~~~~~~~~~~~~~~~~

Start the server with:

.. code-block:: sh

   uv run |repo_name|

The backend will be available at ``https://localhost:443/api`` by default.

**Available Endpoints:**

- **Health Check:** ``https://localhost:443/api/health``
- **Login:** ``https://localhost:443/api/login`` (requires authentication)

**Testing the API:**

.. code-block:: sh

   curl -k https://localhost:443/api/health
   curl -k -H "X-API-Key: your-token-here" https://localhost:443/api/login

Testing, Linting, and Type Checking
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: sh

   # Lint code
   uv run ruff check .

   # Format code
   uv run ruff format .

   # Type check
   uv run mypy .

   # Run tests
   uv run pytest

   # Security scan
   uv run bandit -r |package_name|/

   # Audit dependencies
   uv run pip-audit

Building Documentation
~~~~~~~~~~~~~~~~~~~~~~

This project uses Sphinx for documentation. To build the documentation:

.. code-block:: sh

   uv run sphinx-build -M clean docs/source/ docs/build/
   uv run sphinx-build -M html docs/source/ docs/build/

The built documentation will be available at ``docs/build/html/index.html``.
