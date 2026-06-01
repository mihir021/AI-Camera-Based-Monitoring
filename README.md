# 📷 AI-Camera-Based-Monitoring Platform

An intelligent, cloud-enabled camera monitoring platform that uses Computer Vision (YOLOv8) to process video streams in real-time. This system provides automated analytics, such as person counting and confidence tracking, delivered through a modern web dashboard.

---

## 🏗️ Architecture & Tech Stack

This repository is structured as a **Monorepo** containing three distinct workspaces to separate concerns and allow independent scaling:

- **Frontend (Web Dashboard)**
  - React 19 (Plain JSX) + Vite
  - Tailwind CSS for styling
  - Hosted on **Vercel**

- **Backend (API & Video Processing)**
  - Python 3.12 + FastAPI
  - MongoDB (via Motor async driver)
  - Pytest for automated testing
  - Hosted on **Railway**

- **AI (Computer Vision & ML)**
  - Ultralytics YOLOv8 (Object Detection)
  - OpenCV (Video Stream Processing)

---

## 📂 Project Structure

```text
.
├── .github/workflows/   # CI/CD pipelines (GitHub Actions)
├── ai/                  # AI/ML Workspace
│   ├── data/            # Datasets and test videos
│   ├── models/          # YOLOv8 weight files (.pt)
│   └── src/             # Inference and CV scripts
├── backend/             # FastAPI Backend Workspace
│   ├── app/             # Application source code
│   │   ├── api/         # API routing
│   │   ├── core/        # Configurations
│   │   ├── models/      # MongoDB schemas
│   │   ├── services/    # Business logic
│   │   └── main.py      # FastAPI entry point
│   ├── tests/           # Pytest test suite
│   ├── uploads/         # Temporary video storage
│   ├── .env.example     # Environment variable template
│   └── Dockerfile       # Railway deployment container
└── frontend/            # React Frontend Workspace
    ├── src/
    │   ├── components/  # Reusable UI elements
    │   ├── hooks/       # Custom React hooks
    │   ├── pages/       # Dashboard views
    │   └── utils/       # Helper functions
    └── package.json     # Frontend dependencies
```

---

## 🚀 Local Development Setup

### 1. Prerequisites
- [Node.js](https://nodejs.org/) (v18+)
- [Python](https://www.python.org/) (v3.11+)
- [MongoDB](https://www.mongodb.com/) (Local instance or MongoDB Atlas URL)

### 2. Backend Setup
The backend requires Python and OpenCV dependencies.

```bash
cd backend
python -m venv venv
# PowerShell
.\venv\Scripts\Activate.ps1

# Command Prompt
# venv\Scripts\activate.bat

# Bash / Git Bash / WSL
# source venv/bin/activate
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your MongoDB connection string

# Run the FastAPI server
uvicorn app.main:app --reload --port 8000
```
*The API will be available at `http://localhost:8000`. You can view the auto-generated documentation at `http://localhost:8000/docs`.*

### 3. Frontend Setup
The frontend is a lightweight React Vite application.

```bash
npm install

# Run the development server from the repo root
npm run dev
```
*The dashboard will be available at `http://localhost:5173`.*

If you prefer to work directly inside the frontend workspace, you can still run `cd frontend && npm run dev` there.

---

## 🔄 CI/CD & Deployment

This project utilizes fully automated CI/CD pipelines via **GitHub Actions**:
1. **Continuous Integration**: Pushing code to any branch triggers the CI pipeline (`ci.yml`). This automatically runs the Pytest suite for the backend and verifies the Vite production build for the frontend.
2. **Continuous Deployment**: Pushing to the `main` branch automatically triggers native deployments:
   - **Vercel** automatically rebuilds and deploys the `frontend/` directory.
   - **Railway** automatically detects the `backend/Dockerfile` and deploys the API.

---

## 🤝 Contributing

1. **Branch Naming**: Please use descriptive branch names (e.g., `feature/dashboard-ui`, `fix/upload-bug`).
2. **Commit Messages**: Write clear, imperative commit messages.
3. **Pull Requests**: Ensure all GitHub Actions checks pass before requesting a review. Do not merge directly to `main` without review.