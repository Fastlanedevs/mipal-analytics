# MIPAL Analytics Platform

An advanced, open-source analytics platform that combines conversational AI with powerful data visualization and analysis capabilities. Built with FastAPI backend and Next.js frontend for a modern, scalable architecture.

![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Next.js](https://img.shields.io/badge/next.js-14.2+-black.svg)
![TypeScript](https://img.shields.io/badge/typescript-5.0+-blue.svg)

## 🚀 Features

### 🤖 Conversational Analytics
- **AI-Powered Chat Interface**: Natural language queries for data analysis
- **Multi-LLM Support**: OpenAI, Groq, Gemini, DeepSeek integration
- **Real-time Streaming**: WebSocket-based live responses

### 📊 Data Visualization & Analysis
- **AI Chart Generation**: Automatically create charts from conversation context
- **Interactive Dashboards**: Drag-and-drop dashboard builder
- **Multi-format Data Support**: PostgreSQL, Excel, CSV file processing
- **Real-time Collaboration**: Share and collaborate on dashboards

### 🔐 Enterprise-Ready
- **Multi-tenant Architecture**: Organization-based access control
- **JWT Authentication**: Secure token-based authentication
- **Role-based Permissions**: Fine-grained access control
- **SSO Integration**: NextAuth.js with multiple providers

### 🔌 Extensible Platform
- **Integration Framework**: Connect external data sources
- **Code Execution**: Secure sandboxed code execution environment
- **Plugin Architecture**: Extensible agent and workflow system

## 🏗️ Architecture

```
mipal-analytics/
├── 🎨 frontend/                 # Next.js 14 + TypeScript Frontend
│   ├── src/app/                # App Router pages and layouts
│   ├── src/components/         # Reusable React components
│   ├── src/store/             # Redux Toolkit state management
│   ├── src/lib/               # Utilities and configurations
│   └── public/                # Static assets
│
├── 🚀 backend/                 # FastAPI Python Backend
│   ├── app/                   # Domain-driven application modules
│   │   ├── auth/              # Authentication & authorization
│   │   ├── analytics/         # Data analysis & visualization
│   │   ├── chat/              # Conversational interface
│   │   ├── user/              # User & organization management
│   │   └── pal/               # Program-Aided Language workflows
│   ├── cmd_server/            # Server entry points
│   ├── pkg/                   # Shared utilities & clients
│   └── conf/                  # Configuration management
│
└── 📚 docs/                   # Documentation & guides
```

## 🛠️ Technology Stack

### Frontend
- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript 5+
- **UI Components**: Radix UI + Tailwind CSS
- **State Management**: Redux Toolkit + RTK Query
- **Charts**: Recharts, Vega-Lite
- **Rich Text**: TipTap Editor
- **Authentication**: NextAuth.js

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Architecture**: Clean Architecture + DDD
- **Databases**: PostgreSQL, Neo4j, Redis
- **LLM Integration**: OpenAI, Groq, Gemini, DeepSeek
- **Authentication**: JWT with bcrypt
- **Code Execution**: Docker/ECS sandboxed environment
- **Configuration**: Hydra + OmegaConf

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Cloud Services**: AWS (S3, SES, KMS)
- **Package Management**: uv (Python), npm (Node.js)
- **Code Quality**: Ruff (Python), ESLint + Prettier (TypeScript)

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 13+
- Redis 6+
- Neo4j 5+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### Option 1: One-Command Setup (Recommended)
```bash
# Clone the repository
git clone https://github.com/your-org/mipal-analytics.git
cd mipal-analytics

# Configure environment files
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
# Edit the .env files with your database credentials and API keys

# Start all services at once
./start-dev.sh
```

The `start-dev.sh` script automatically starts all required services concurrently:

#### 🚀 **Backend API Server** (`http://localhost:8000`)
- **Purpose**: Main FastAPI application handling REST API endpoints
- **Handles**: Authentication, analytics, chat, user management, file uploads
- **Dependencies**: PostgreSQL, Redis, Neo4j databases
- **Individual Command**: `cd backend && make run`

#### 🎨 **Frontend Development Server** (`http://localhost:3000`)
- **Purpose**: Next.js development server with hot reload
- **Handles**: React UI, dashboard, chat interface, authentication pages
- **Dependencies**: Backend API server
- **Individual Command**: `cd frontend && npm run dev`

#### ⚡ **Background Worker Service**
- **Purpose**: Processes async tasks like document processing, email sending
- **Handles**: Queue processing, background jobs, data synchronization
- **Dependencies**: Same as API server (PostgreSQL, Redis, Neo4j)
- **Individual Command**: `cd backend && make run-worker`

#### 🔧 **Code Execution Server** (`http://localhost:8002`)
- **Purpose**: Secure sandboxed environment for executing user-generated code
- **Handles**: Python/SQL code execution, data analysis, chart generation
- **Security**: Isolated Docker containers for safe code execution
- **Individual Command**: `cd backend && make run-codex`

#### 📊 **Service Health Monitoring**
The script includes automatic health checks and will restart failed services. Press `Ctrl+C` to gracefully shutdown all services.

### Option 2: Manual Setup

#### 1. Clone the Repository
```bash
git clone https://github.com/your-org/mipal-analytics.git
cd mipal-analytics
```

#### 2. Backend Setup
```bash
cd backend

# Install dependencies
make install
# or: uv pip install -r pyproject.toml --all-extras

# Configure environment
cp .env.example .env
# Edit .env with your database credentials and API keys

# Start the API server
make run
```

The backend will be available at `http://localhost:8000`

#### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.local.example .env.local
# Edit .env.local with your backend URL and auth settings

# Start the development server
npm run dev
```

The frontend will be available at `http://localhost:3000`

## 📋 Environment Configuration

### 📁 File Locations
- **Backend**: Create `backend/.env` file in the backend directory
- **Frontend**: Create `frontend/.env.local` file in the frontend directory

### 🔧 Backend Environment Variables (`backend/.env`)

#### 🗄️ **Database Connections** (Required)
```bash
# PostgreSQL - Primary database for user data, analytics, and application state
POSTGRES_HOST=localhost              # Database host (use prod-db.mipal.ai for production)
POSTGRES_PORT=5432                   # Database port
POSTGRES_USER=postgres               # Database username
POSTGRES_PASSWORD=your_password      # Database password
POSTGRES_DATABASE=mipal              # Database name

# Neo4j - Graph database for knowledge relationships and entity mapping
NEO4J_URI=bolt://localhost:7687      # Neo4j connection URI
NEO4J_USER=neo4j                     # Neo4j username
NEO4J_PASSWORD=your_neo4j_password   # Neo4j password

# Redis - Caching and session storage
REDIS_HOST=localhost                 # Redis host
REDIS_PORT=6379                      # Redis port
REDIS_PASSWORD=your_redis_password   # Redis password (if required)
```

#### 🤖 **LLM API Keys** (At least one required)
```bash
# OpenAI - GPT models for conversational AI
OPENAI_API_KEY=sk-your_openai_key

# Groq - Fast inference for Llama models
GROQ_API_KEY=gsk_your_groq_key

# Google Gemini - Google's multimodal AI
GEMINI_API_KEY=your_gemini_key

# DeepSeek - Code-focused AI models
DEEPSEEK_API_KEY=your_deepseek_key
```

#### 🔐 **Authentication & Security** (Required)
```bash
# JWT tokens for user authentication
JWT_SUPER_SECRET=your_super_secure_jwt_secret_key_min_32_chars
JWT_REFRESH_SECRET=your_refresh_secret_key_min_32_chars

# Generate secrets with: openssl rand -base64 32
```

#### ☁️ **AWS Services** (Optional - Required for full functionality)
```bash
# AWS credentials for cloud services
AWS_ACCESS_KEY_ID=AKIA...            # AWS access key
AWS_SECRET_ACCESS_KEY=your_secret    # AWS secret key
AWS_REGION=us-east-1                 # AWS region

# S3 for file storage
AWS_S3_BUCKET_NAME=mipal-files       # S3 bucket for file uploads

# KMS for encryption
AWS_KMS_KEY_ID=your_kms_key_id       # KMS key for data encryption

# SES for email sending
SMTP_SERVER=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USER_NAME=your_ses_username
SMTP_PASSWORD=your_ses_password
```

#### 🔧 **Optional Services**
```bash
# Code execution service URL (for advanced analytics)
CODE_EXECUTION_SERVICE_URL=http://localhost:8002

# Background job queue
SYNC_DOCUMENTS_QUEUE=mipal-local

# Application settings
LOG_LEVEL=INFO                       # Logging level (DEBUG, INFO, WARN, ERROR)
ENVIRONMENT=development              # Environment (development, staging, production)
```

### 🎨 Frontend Environment Variables (`frontend/.env.local`)

#### 🌐 **API Configuration** (Required)
```bash
# Backend API connection
NEXT_PUBLIC_APP_URL=http://localhost:3000          # Frontend URL
NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8000      # Backend API URL (use 127.0.0.1 for local dev)
NEXT_PUBLIC_API_URL=http://localhost:8000           # Alternative API URL format
```

#### 🔐 **Authentication** (Required)
```bash
# NextAuth.js configuration
NEXTAUTH_URL=http://localhost:3000                  # Frontend URL for auth callbacks
NEXTAUTH_SECRET="WgQ/cl+/qj8p11dlJOqAuNv7MpLTGPRLkJKfXEg1c6w="  # Secret for JWT signing

# Generate secret with: openssl rand -base64 32
```

#### 📊 **Optional Analytics & Monitoring**
```bash
# PostHog analytics (optional)
NEXT_PUBLIC_POSTHOG_KEY=phc_your_posthog_key
NEXT_PUBLIC_POSTHOG_HOST=https://app.posthog.com

# Sentry error tracking (optional)
SENTRY_DSN=https://your_sentry_dsn

# Environment indicator
NEXT_PUBLIC_ENVIRONMENT=development
```

### 🔐 **Security Notes**
- **Never commit `.env` files** to version control
- **Use strong, unique secrets** for JWT and NextAuth
- **Rotate API keys regularly** in production
- **Use environment-specific values** for different deployments

## 🧪 Testing the Application

### Health Check
```bash
curl http://localhost:8000/health
```

### API Documentation
Visit `http://localhost:8000/docs` for interactive API documentation

### User Registration
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword",
    "name": "John Doe"
  }'
```

## 🔧 Development

### Code Quality

**Backend:**
```bash
cd backend
ruff check          # Lint Python code
ruff format          # Format Python code
```

**Frontend:**
```bash
cd frontend
npm run lint         # Lint TypeScript/React code
npm run format       # Format code with Prettier
```

### Running Services Individually

When you need to run services separately instead of using `./start-dev.sh`:

#### 🚀 **Backend Services** (Run from `backend/` directory)
```bash
cd backend

# Main API Server (Port 8000) - Always start this first
make run
# Equivalent to: uv run --env-file .env python3 cmd_server/server/main.py
# Handles: REST API, WebSocket connections, authentication, file uploads

# Background Worker - Start in a separate terminal
make run-worker  
# Equivalent to: uv run --env-file .env python3 cmd_server/worker/main.py
# Handles: Async tasks, email sending, document processing, queue jobs

# Code Execution Server (Port 8002) - Optional for advanced features
make run-codex
# Equivalent to: uv run --env-file .env python3 cmd_server/code_execution_server/main.py
# Handles: Secure Python/SQL code execution, data analysis, chart generation
```

#### 🎨 **Frontend Development** (Run from `frontend/` directory)
```bash
cd frontend

# Development Server (Port 3000) - Hot reload enabled
npm run dev
# Starts Next.js dev server with automatic file watching and hot reload

# Production Build & Start
npm run build       # Build optimized production bundle
npm run start       # Start production server (requires build first)

# Code Quality
npm run lint        # ESLint for code quality checks
npm run format      # Prettier for code formatting
```

#### 📊 **Service Dependencies**
- **Frontend** → Requires Backend API Server (port 8000)
- **Backend API** → Requires PostgreSQL, Redis, Neo4j databases
- **Worker Service** → Requires same databases as API Server
- **Code Execution** → Independent service, communicates via HTTP

## 🐳 Docker Deployment

### Backend
```bash
cd backend
make container      # Build Docker image
make run-container  # Run containerized backend
```

### Full Stack (Docker Compose)
```bash
docker-compose up -d
```

## 📖 API Examples

### Authentication Flow
```bash
# 1. Register
curl -X POST localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123","name":"User"}'

# 2. Verify email (if required)
curl -X POST localhost:8000/auth/verify-email \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","otp":"123456"}'

# 3. Login
curl -X POST localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'
```

### Analytics API
```bash
# List databases
curl -H "Authorization: Bearer YOUR_TOKEN" localhost:8000/analytics/databases

# Create chart
curl -X POST localhost:8000/analytics/charts \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message_id":"msg_123","chart_type":"bar"}'
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for:

- 📋 Code of conduct
- 🛠️ Development setup
- 🔄 Pull request process
- 📏 Coding standards
- 🧪 Testing guidelines

### Development Workflow
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests and ensure they pass
5. Commit with conventional commits
6. Push and create a Pull Request

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🆘 Support & Documentation

### 📚 Documentation
- **Backend API**: `http://localhost:8000/docs`
- **Architecture Docs**: [docs/architecture.md](docs/architecture.md)
- **Deployment Guide**: [docs/deployment.md](docs/deployment.md)

### 🐛 Issues & Support
- Report bugs: [GitHub Issues](https://github.com/your-org/mipal-analytics/issues)
- Feature requests: [GitHub Discussions](https://github.com/your-org/mipal-analytics/discussions)
- Security issues: See [SECURITY.md](SECURITY.md)

### 💬 Community
- Discord: [Join our community](https://discord.gg/mipal)
- Twitter: [@MipalAnalytics](https://twitter.com/MipalAnalytics)

## 🗺️ Roadmap

### 🎯 Current (v0.1.0)
- [x] Core analytics engine
- [x] Conversational interface
- [x] Multi-LLM support
- [x] Dashboard creation
- [x] User authentication

### 🚀 Next Release (v0.2.0)
- [ ] Self-hosted alternatives to AWS services
- [ ] Enhanced collaboration features
- [ ] Advanced chart customization
- [ ] Mobile-responsive interface
- [ ] Plugin marketplace

### 🔮 Future
- [ ] Multi-language support
- [ ] Advanced ML workflows
- [ ] Custom agent creation
- [ ] Enterprise SSO integration
- [ ] API marketplace

## 📊 Project Stats

![GitHub stars](https://img.shields.io/github/stars/your-org/mipal-analytics)
![GitHub forks](https://img.shields.io/github/forks/your-org/mipal-analytics)
![GitHub issues](https://img.shields.io/github/issues/your-org/mipal-analytics)
![GitHub license](https://img.shields.io/github/license/your-org/mipal-analytics)

---

**Made with ❤️ by the MIPAL Team**

*Empowering data-driven decision making through conversational AI*