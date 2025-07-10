# 🛡️ PDF Redaction API (FastAPI)

This is a backend service built with FastAPI to perform redaction on uploaded PDF files. It supports:

- Manual redaction boxes
- Text-based keyword redaction
- Optional graphic removal
- File download of redacted PDFs

---

## ⚙️ Requirements

- Python 3.8+
- pip

---

## 📦 TO RUN THIS PROJECT

1. python -m venv venv
   source venv/bin/activate # on Linux/Mac
   venv\Scripts\activate

pip install -r requirements.txt

## Start the FastAPI server with:

- \*\* uvicorn app.main:app --reload
