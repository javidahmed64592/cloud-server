## Cloud Server v{{VERSION}}

**A FastAPI-based local cloud server.**

### Quick Start

```bash
# Download and extract
wget https://github.com/{{REPOSITORY}}/releases/download/v{{VERSION}}/{{PACKAGE_NAME}}_{{VERSION}}.tar.gz
tar -xzf {{PACKAGE_NAME}}_{{VERSION}}.tar.gz
cd {{PACKAGE_NAME}}_{{VERSION}}

# Set up environment variables
cp .env.example .env

# Run the container using Docker Compose
docker compose up -d
```

### Access Points

- **API Server**: http://localhost:8000/api
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
