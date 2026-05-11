Server Architecture
===================

This document provides an overview of the architecture of the |project_name|, a FastAPI-based backend framework.
All endpoints are mounted under the ``/api`` prefix.

.. note::

   The ``TemplateServer`` base class provides common behaviors (authentication, rate limiting, security headers, instrumentation) that are automatically applied to all endpoints.
   Application-specific servers (like ``ExampleServer``) extend ``TemplateServer`` to add custom endpoints and business logic.

----

Authentication
~~~~~~~~~~~~~~

An authentication key must be passed in via the ``X-API-Key`` header for protected API endpoints.
``401 Unauthorized`` responses indicate missing or invalid API keys.

Request Logging
~~~~~~~~~~~~~~~

All incoming requests and outgoing responses are automatically logged for monitoring and debugging purposes.

**Logged Information:**

- **Request:** HTTP method, path, client IP address
- **Response:** HTTP method, path, status code
- **Authentication:** API key validation attempts

Security Headers
~~~~~~~~~~~~~~~~

All API responses include security headers to protect against common web vulnerabilities.

**Headers Included:**

- ``Strict-Transport-Security``: Forces HTTPS connections (HSTS)
- ``X-Content-Type-Options``: Prevents MIME-type sniffing
- ``X-Frame-Options``: Prevents clickjacking attacks
- ``Content-Security-Policy``: Controls which resources can be loaded
- ``X-XSS-Protection``: Enables browser XSS filtering
- ``Referrer-Policy``: Controls referrer information sent with requests

CORS (Cross-Origin Resource Sharing)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CORS allows controlled access to the API from web applications hosted on different domains.
By default, CORS is **disabled** for security.

Rate Limiting
~~~~~~~~~~~~~

Rate limiting is implemented to prevent abuse and ensure fair usage of the API.
``429 Too Many Requests`` responses indicate that the client has exceeded the allowed request rate.

----

Static File Serving
~~~~~~~~~~~~~~~~~~~

The server can optionally serve static files (HTML, CSS, JavaScript, images) from a ``static/`` directory if it exists.
This enables you to host Single Page Applications (SPAs) alongside the API.

**Directory Structure:**

.. code-block:: text

   project-root/
   ├── static/
   │   ├── index.html
   │   ├── 404.html
   │   └── ...
   └── ...

The server uses FastAPI's built-in ``StaticFiles`` mounting for optimized static file serving:

- Mounted at root (``/``) with ``html=True`` to automatically serve ``index.html`` for directories
- Custom exception handler intercepts 404 errors to serve ``404.html``

FastAPI Documentation
~~~~~~~~~~~~~~~~~~~~~

FastAPI automatically generates interactive API documentation, providing two different interfaces for exploring and testing the API.

**Swagger UI**

- **URL**: ``https://localhost:443/api/docs``
- **Purpose**: Interactive API documentation with "Try it out" functionality

**Features**:

- Execute API calls directly from the browser
- View request/response schemas
- Test authentication with API keys
- Explore all available endpoints
- View models and their properties

**ReDoc**

- **URL**: ``https://localhost:443/api/redoc``
- **Purpose**: Alternative API documentation with a clean, three-panel layout

**Features**:

- Read-only documentation interface
- Clean, responsive design
- Search functionality
- Detailed schema information
- Markdown support in descriptions
