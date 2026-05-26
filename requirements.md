# System & Application Requirements Guide

This document outlines the technical requirements, software dependencies, and runtime configurations necessary to run both the **FastAPI Backend** and the new **React (TypeScript) Frontend** in a monorepo setup.

---

## 📋 1. Core Prerequisites

Before installing the application dependencies, ensure you have the following software installed on your system:

| Prerequisite | Minimum Version | Description |
| :--- | :--- | :--- |
| **Python** | `3.11+` | Backend runtime & document processing services. |
| **Node.js** | `18.0.0+` (LTS recommended) | Frontend build environment (Vite, React, npm). |
| **Tesseract OCR** | `5.0.0+` | Offline Optical Character Recognition engine. |
| **Gemini / Groq API Key** | - | External LLM provider for hybrid document extraction. |

---

## 🐍 2. Backend Requirements (Python FastAPI)

The backend is built using FastAPI and orchestrates the worker queue, caching system, and processing adapters.

### Python Dependencies (`requirements.txt`)
* **FastAPI** (`0.136.1`) — High-performance web framework for APIs.
* **Uvicorn** (`0.46.0`) — ASGI web server implementation.
* **Pydantic** (`2.13.3`) — Data validation and settings management.
* **pytesseract** (`0.3.13`) — Python wrapper for Tesseract OCR.
* **pdfplumber** (`0.11.9`) & **pypdfium2** (`5.7.1`) — PDF text and layout extraction.
* **Pillow** (`12.2.0`) — Image processing library.
* **python-dotenv** (`1.2.2`) — Configuration loading from `.env` files.
* **opencv-python** (`>=4.13.0`) & **numpy** (`>=2.4.4`) — Advanced OCR preprocessing.
* **pytest** (`>=8.0.0`) & **pytest-asyncio** (`>=0.23.0`) — Testing frameworks for the backend.

### Installation Command
From the project root:
```bash
# 1. Create a virtual environment (highly recommended)
python -m venv venv

# 2. Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# 3. Install all requirements
pip install -r requirements.txt
```

---

## ⚛️ 3. Frontend Requirements (React TypeScript)

The new premium web dashboard is located in `./web` and compiles to highly optimized static assets.

### Frontend Package Dependencies (`package.json`)
* **React** & **React DOM** (`^19.0.0`) — Modern component framework.
* **Vite** (`^6.0.0`) — Ultra-fast next-gen build tool.
* **React Router DOM** (`^7.0.0`) — Multiplying page routing engine.
* **Framer Motion** (`^11.0.0`) — High-fidelity layouts and state transitions.
* **Lucide React** (`^0.470.0`) — Premium svg icons.
* **React Hot Toast** (`^2.5.0`) — Micro-animated push notifications.
* **TanStack React Query** (`^5.0.0`) — Server state cache manager.

### Installation Command
Navigate to the `web` folder and install packages:
```bash
cd web
npm install
```

---

## 🚀 4. Running the Local Development Servers

To run the full monorepo stack, you must start **both** the backend and the frontend servers concurrently:

### Terminal 1: Launch Python FastAPI Backend
From the root directory:
```bash
# Activate virtual environment if configured
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
*Runs backend API on `http://localhost:8000` with automated hot-reloading.*

### Terminal 2: Launch Vite React Frontend
Open a new terminal window, navigate to the `web` directory, and run:
```bash
cd web
npm run dev
```
*Runs modern frontend dashboard on `http://localhost:3000` with active proxy targeting the backend on port 8000.*

---

## 🛡️ 5. External Engines Installation Guide

### Tesseract OCR Installation
* **Windows**:
  1. Download the installer from the [UB-Mannheim Tesseract Wiki](https://github.com/UB-Mannheim/tesseract/wiki).
  2. Run the installer and remember the installation directory (usually `C:\Program Files\Tesseract-OCR`).
  3. Add the installation directory to your system **PATH** environment variable.
* **Ubuntu/Linux**:
  ```bash
  sudo apt-get update
  sudo apt-get install tesseract-ocr tesseract-ocr-hin
  ```
* **macOS**:
  ```bash
  brew install tesseract tesseract-lang
  ```
