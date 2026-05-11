## Python Template Server v{{VERSION}}

**A template FastAPI server with production-ready configuration.**

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

- **API Server**: https://localhost:443/api
- **Swagger UI**: https://localhost:443/api/docs
- **ReDoc**: https://localhost:443/api/redoc
