# HireView

**AI-Powered Resume Analysis & Mock Interview Assistant**

An intelligent platform that helps job seekers optimize their resumes and practice interviews with AI-powered feedback. Built for the Qualcomm Hackathon, HireView combines advanced AI capabilities with an intuitive user interface to provide comprehensive career preparation tools.

## 🎯 Features

### 📄 Resume Analysis
- **Smart Text Extraction** - Supports PDF, TXT, DOC, DOCX formats
- **Skill Assessment** - AI analyzes skill matching and provides improvement suggestions
- **Experience Evaluation** - Evaluates work experience alignment with target positions
- **Optimization Recommendations** - Provides specific resume enhancement suggestions
- **Comprehensive Scoring** - Generates overall ratings with detailed feedback

### 🎤 AI Mock Interviews
- **Personalized Questions** - Generates targeted questions based on resume and job description
- **Multiple Interview Types** - Technical, behavioral, and mixed interview formats
- **Difficulty Levels** - Beginner, intermediate, and advanced levels
- **Real-time AI Assessment** - Detailed scoring and feedback for each answer
- **Complete Session Recording** - Saves entire interview process for later review

### 🖥️ Dual Interface Options
- **Desktop Application** - Electron-based standalone app with embedded Python backend
- **Web Interface** - Gradio-powered web application for browser-based access

## 🚀 Quick Start

### Option 1: Desktop Application (Recommended)
```bash
# Navigate to electron app directory
cd electron-app

# Install dependencies
npm install

# Start the desktop application
npm start
```

### Option 2: Web Application
```bash
# Navigate to python backend directory
cd python-backend

# Install Python dependencies
pip install -r requirements.txt

# Start the integrated web application
python integrated_app.py
```

### Option 3: Development Mode (Separate Services)
```bash
# Terminal 1: Start FastAPI model service
cd python-backend
python model_service.py

# Terminal 2: Start Gradio frontend
cd python-backend
python app.py
```

## 🌐 Access URLs

- **Desktop App**: Launches automatically
- **Web Interface**: http://127.0.0.1:7862
- **API Documentation**: http://localhost:8000/docs
- **Alternative Web Interface**: http://127.0.0.1:7860 (if running separately)

## 📖 How to Use

### 1. Resume Upload & Analysis
1. Upload your resume (PDF, TXT, DOC, DOCX supported)
2. Optionally provide target job description
3. Click "Start Analysis" to receive AI-powered feedback
4. Review detailed analysis including:
   - Skill matching assessment
   - Experience evaluation
   - Improvement recommendations
   - Overall scoring with explanations

### 2. Resume Review Mode
Switch to "Resume Review" mode and ask specific questions:
- "Analyze my skills" - Get skill assessment
- "Provide improvement suggestions" - Get optimization recommendations
- "Evaluate my experience" - Get experience matching analysis
- "Overall evaluation" - Get comprehensive scoring

### 3. Mock Interview Mode
1. Switch to "Mock Interview" mode
2. Configure interview parameters:
   - **Job Title**: Target position
   - **Company**: Target company
   - **Difficulty**: beginner/intermediate/advanced
   - **Type**: technical/behavioral/mixed
   - **Duration**: 10-60 minutes
3. Click "Start Interview"
4. Answer AI-generated questions
5. Receive real-time scoring and feedback
6. Review complete interview summary

## 🏗️ Architecture

```
HireView Architecture
├── Electron Desktop App (main.js)
│   ├── UI Management
│   ├── Python Process Integration
│   └── File System Access
├── Python Backend Services
│   ├── FastAPI Model Service (port 8000)
│   │   ├── Interview Session Management
│   │   ├── LLaMA Model Integration
│   │   ├── Conversation History Storage
│   │   └── RESTful API Endpoints
│   └── Gradio Frontend (port 7862)
│       ├── File Upload Processing
│       ├── Resume Analysis Interface
│       ├── Interview Configuration UI
│       └── Real-time Chat Interface
└── Data Storage
    ├── Session Management (JSON)
    ├── Conversation History
    └── Temporary File Handling
```

## 📁 Project Structure

```
qualcomm_hack/
├── electron-app/                   # Desktop application
│   ├── main.js                   # Electron main process
│   ├── preload.js                # Preload scripts
│   ├── package.json              # Node.js dependencies
│   └── dist/                     # Built application
├── python-backend/               # Backend services
│   ├── integrated_app.py         # Integrated web application
│   ├── model_service.py          # FastAPI model service
│   ├── Llama-3.1-8B.py          # LLaMA model integration
│   ├── requirements.txt          # Python dependencies
│   ├── sessions.json            # Session data (runtime)
│   └── conversations/           # Conversation history
├── api.md                       # API documentation
├── requirements.txt             # Root Python dependencies
└── README.md                   # This file
```

## 🛠️ Technology Stack

- **Frontend**: Electron + Gradio
- **Backend**: FastAPI + Python
- **AI Model**: LLaMA 3.1 8B via Imagine SDK
- **File Processing**: pdfplumber, python-docx
- **API**: RESTful with automatic documentation
- **Data Storage**: JSON-based session management

## 🔧 Configuration

### Interview Types
- **Technical**: Focus on technical knowledge and problem-solving
- **Behavioral**: Emphasis on soft skills and work experience
- **Mixed**: Combination of technical and behavioral questions

### Difficulty Levels
- **Beginner**: Suitable for new graduates and entry-level positions
- **Intermediate**: Designed for 1-3 years of experience
- **Advanced**: Tailored for senior engineers and technical experts

### API Configuration
- FastAPI Service: Port 8000 (configurable in model_service.py)
- Gradio Interface: Port 7862 (configurable in integrated_app.py)

## 📊 Data Management

### Session Storage
- **Desktop App**: Temporary session storage
- **Web App**: Persistent JSON file storage
- **Location**: `sessions.json` and `conversations/` directory

### Privacy & Security
- Resume files are processed locally
- Conversation history stored locally only
- No data uploaded to external servers (except AI API calls)
- API keys securely managed

## 🔍 API Reference

Comprehensive API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Detailed API guide: [api.md](api.md)

Key endpoints:
- `POST /api/resume/upload` - Upload and analyze resume
- `POST /api/resume/chat` - Resume review conversation
- `POST /api/interview/create` - Create mock interview session
- `POST /api/interview/answer` - Submit interview answers
- `GET /api/interview/summary/{session_id}` - Get interview summary

## 🚨 Troubleshooting

### Port Conflicts
```bash
# Check port usage
netstat -ano | findstr ":8000"
netstat -ano | findstr ":7862"

# Modify ports in configuration files if needed
```

### Installation Issues
```bash
# Ensure Python 3.8+ is installed
python --version

# Install dependencies with specific package manager
pip install -r requirements.txt

# For Electron app
cd electron-app && npm install
```

### Model Service Issues
- Verify internet connection for AI model access
- Check API key configuration in Llama-3.1-8B.py
- Ensure imagine-sdk is properly installed

### File Processing Issues
- Confirm file format is supported (PDF, DOC, DOCX, TXT)
- Check file size limits
- Verify pdfplumber and python-docx installation

## 🏃‍♀️ Development

### Building the Desktop App
```bash
cd electron-app
npm run build
```

### Running in Development Mode
```bash
# Backend with hot reload
cd python-backend
uvicorn model_service:app --reload

# Frontend development
python integrated_app.py

# Electron development
cd electron-app
npm run dev
```

### Testing
```bash
# Test API endpoints
cd python-backend
python test_app.py

# Manual testing via API docs
# Visit http://localhost:8000/docs
```

## 🤝 Contributing

This project was developed for the Qualcomm Hackathon. For issues or feature requests, please create an issue in the project repository.

## 📄 License

Developed by the HireView Team for Qualcomm Hackathon 2025.

## 🏆 Team

**HireView AI Team** - Qualcomm Hackathon Participants

---

**Last Updated**: September 28, 2025
**Version**: 1.0.0
