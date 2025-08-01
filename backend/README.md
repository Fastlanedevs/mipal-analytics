# MIPAL Analytics Backend

A modern analytics platform built with FastAPI, providing conversational AI-powered data analysis and visualization capabilities.

## 🚀 Features

- **Conversational Analytics**: Chat-based interface for data analysis using LLM integration
- **Multi-Database Support**: Connect to PostgreSQL, upload Excel/CSV files, or use existing databases
- **Real-time Chat**: WebSocket-based real-time communication
- **Chart Generation**: AI-powered chart creation and visualization
- **User Management**: Complete authentication system with JWT tokens
- **Organization Support**: Multi-tenant architecture with organization management
- **File Processing**: Upload and analyze Excel/CSV files
- **Integration Framework**: Extensible integration system for external data sources

## 🏗️ Architecture

This project follows clean architecture principles with Domain-Driven Design (DDD):

```
├── app/                    # Application layer
│   ├── auth/              # Authentication domain
│   ├── analytics/         # Analytics and data processing
│   ├── chat/              # Conversational interface
│   ├── user/              # User management
│   ├── integrations/      # External integrations
│   └── pal/               # Program-Aided Language model workflows
├── cmd_server/            # Application entry points
├── pkg/                   # Shared packages and utilities
└── conf/                  # Configuration files
```

## 📋 Prerequisites

- Python 3.11+
- PostgreSQL database
- Redis server
- Neo4j database
- AWS account (for S3, SES, KMS services)

## 🔧 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd mipal-analytics/backend
   ```

2. **Install dependencies using uv**
   ```bash
   make install
   ```
   
   Or manually:
   ```bash
   uv pip install -r pyproject.toml --all-extras
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the backend directory with the following variables:
   
   ```bash
   # API Keys - LLM Providers
   OPENAI_API_KEY=your_openai_api_key
   DEEPSEEK_API_KEY=your_deepseek_api_key
   GROQ_API_KEY=your_groq_api_key
   GEMINI_API_KEY=your_gemini_api_key
   
   # Database Connections
   POSTGRES_HOST=your_postgres_host
   POSTGRES_PORT=5432
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=your_postgres_password
   POSTGRES_DATABASE=mipal
   
   NEO4J_URI=your_neo4j_host
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_neo4j_password
   
   REDIS_HOST=your_redis_host
   REDIS_PORT=6379
   REDIS_PASSWORD=your_redis_password
   
   # Authentication
   JWT_SUPER_SECRET=your_jwt_secret
   JWT_REFRESH_SECRET=your_jwt_refresh_secret
   
   # AWS Services (Required for full functionality)
   AWS_ACCESS_KEY_ID=your_aws_access_key
   AWS_SECRET_ACCESS_KEY=your_aws_secret_key
   AWS_REGION=your_aws_region
   AWS_KMS_KEY_ID=your_kms_key_id
   AWS_S3_BUCKET_NAME=your_s3_bucket
   
   # Email (AWS SES)
   SMTP_SERVER=email-smtp.your-region.amazonaws.com
   SMTP_PORT=587
   SMTP_USER_NAME=your_ses_username
   SMTP_PASSWORD=your_ses_password
   
   # Code Execution Service
   CODE_EXECUTION_SERVICE_URL=https://your-code-execution-service.com
   
   # Queue
   SYNC_DOCUMENTS_QUEUE=mipal-local
   ```

4. **Database Setup**
   
   The application will automatically:
   - Create required PostgreSQL tables
   - Install necessary extensions (pg_trgm, vector)
   - Set up Neo4j connections
   
## 🚀 Running the Application

### Development Mode

1. **Start the main API server**
   ```bash
   make run
   ```
   
   The server will start on `http://localhost:8000`

2. **Start the background worker** (optional)
   ```bash
   make run-worker
   ```

3. **Start the code execution server** (for advanced analytics)
   ```bash
   make run-codex
   ```

### Production Mode

Build and run with Docker:
```bash
make container
make run-container
```

## 📡 API Documentation

Once the server is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🧪 Testing the API

### Health Check
```bash
curl http://localhost:8000/health
```

### User Registration
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123",
    "name": "John Doe"
  }'
```

### Login
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

## 🛠️ Development

### Code Quality
The project uses Ruff for linting and formatting:
```bash
ruff check      # Check for issues
ruff format     # Format code
```

### Project Structure
- **Clean Architecture**: Separation of concerns with clear boundaries
- **Dependency Injection**: Using `dependency-injector` for IoC
- **Domain-Driven Design**: Each domain has its own models, services, and repositories
- **Configuration Management**: Centralized config using Hydra/OmegaConf

## 🔌 Integrations

The platform supports various integrations:
- **Database Connections**: PostgreSQL, Excel, CSV files
- **LLM Providers**: OpenAI, Groq, Gemini, DeepSeek
- **Cloud Services**: AWS S3, SES, KMS
- **External APIs**: Extensible integration framework

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow the existing code structure
- Add tests for new features
- Update documentation as needed
- Use conventional commit messages

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

If you encounter any issues:

1. Check the [Issues](https://github.com/your-org/mipal-analytics/issues) page
2. Review the API documentation at `/docs`
3. Ensure all environment variables are correctly set
4. Verify database connections are working

## 🗺️ Roadmap

- [ ] Alternative cloud providers (Azure, GCP)
- [ ] Self-hosted code execution environment
- [ ] Additional database connectors
- [ ] Enhanced visualization options
- [ ] Real-time collaboration features
- [ ] Advanced analytics workflows

## 🏷️ Version

Current version: 0.1.0

## 📞 Contact

For questions and support, please open an issue in the GitHub repository.

---

**Note**: This project currently requires AWS services for full functionality. Alternative implementations for cloud services are planned for future releases to make the platform fully self-hostable.