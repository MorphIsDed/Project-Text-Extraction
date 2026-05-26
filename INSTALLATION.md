# Installation Guide

Requirements: Python 3.11+, Tesseract OCR, Google Gemini API Key

## 1. Extract and Navigate

```bash
cd path/to/extracted/folder
```

## 2. Setup Virtual Environment

```bash
python -m venv venv
```

Windows:
```bash
venv\Scripts\activate
```

Linux/Mac:
```bash
source venv/bin/activate
```

```bash
pip install -r requirements.txt
```

## 3. Install Tesseract OCR

Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki and add to PATH

Linux:
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-hin
```

Mac:
```bash
brew install tesseract tesseract-lang
```

Verify:
```bash
tesseract --version
```

## 4. Get API Keys

Gemini: https://makersuite.google.com/app/apikey
Groq (optional): https://console.groq.com/keys

## 5. Configure Environment

```bash
cp .env.example .env
```

Edit .env and add your API keys:

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
OCR_ENGINE=tesseract
OCR_LANG=eng+hin
MAX_WORKERS=8
```

## 6. Start Server

```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 7. Access

Web: http://localhost:8000
API Docs: http://localhost:8000/docs
Health: http://localhost:8000/health

Test:
```bash
curl http://localhost:8000/health
```

## Troubleshooting

API key error: Check .env file exists with valid keys
Tesseract not found: Add to PATH or reinstall
Module error: Activate venv and run pip install -r requirements.txt
Port in use: Change port with --port 8001
Slow processing: Check internet connection or reduce MAX_WORKERS

## Supported Documents

Aadhaar, PAN, Voter ID, Driving License, Passport

## System Requirements

Minimum: 2 CPU cores, 4GB RAM, 2GB storage, internet connection
Recommended: 4+ cores, 8GB RAM, 5GB storage
