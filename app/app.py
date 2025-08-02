from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
from pathlib import Path

from app.redaction import redact_text

app = FastAPI()

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production use
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Pydantic model for manual redaction input
class RedactionRequest(BaseModel):
    filename: str
    keywords: Optional[str] = ""
    page_range: Optional[str] = ""
    remove_graphics: Optional[bool] = False
    manual_boxes: Optional[list[dict]] = None

# Utility to sanitize file names
def sanitize_filename(filename: str) -> str:
    """Return a safe file name to prevent path traversal."""
    return os.path.basename(filename)

# --- Endpoint: Upload PDF File ---
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF files are allowed.")

    filename = sanitize_filename(file.filename)
    upload_path = UPLOAD_DIR / filename

    try:
        contents = await file.read()
        with open(upload_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    return {"filename": filename, "message": "File uploaded successfully."}

# --- Endpoint: Redact file with manual inputs and keyword search ---
@app.post("/redact/")
async def redact_with_manual(request: RedactionRequest):
    filename = sanitize_filename(request.filename)
    input_path = UPLOAD_DIR / filename
    output_path = OUTPUT_DIR / f"redacted_{filename}"

    # Check file existence
    if not input_path.exists():
        raise HTTPException(status_code=404, detail="File not found in uploads directory.")

    # Validate and parse keywords
    keywords = []
    if request.keywords:
        if not isinstance(request.keywords, str):
            raise HTTPException(status_code=422, detail="Keywords must be a comma-separated string.")
        keywords = [k.strip() + ' ' for k in request.keywords.split(",") if k.strip()]

    # Validate manual boxes
    if request.manual_boxes:
        for box in request.manual_boxes:
            required_keys = {"page", "x0", "y0", "x1", "y1"}
            if not required_keys.issubset(box):
                raise HTTPException(status_code=422, detail="Each manual box must include page, x0, y0, x1, y1.")

    # Parse page range (e.g., "1-3,5")
    try:
        pages = parse_page_range(request.page_range)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid page range: {str(e)}")

    # Perform redaction
    try:
        redact_text(
            input_path=str(input_path),
            output_path=str(output_path),
            keywords=keywords,
            pages=pages,
            remove_images=request.remove_graphics,
            manual_boxes=request.manual_boxes
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redaction failed: {str(e)}")

    return {
        "message": "Manual redaction complete",
        "redacted_file": str(output_path.name),
        "boxes": request.manual_boxes
    }

# --- Endpoint: Download redacted PDF ---
@app.get("/download/{filename}")
async def download_file(filename: str):
    safe_filename = sanitize_filename(filename)
    file_path = OUTPUT_DIR / f"redacted_{safe_filename}"

    # Verify file existence
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Redacted file not found.")

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/pdf"
    )

# --- Helper: Parse page range like "1-3,5" into [0, 1, 2, 4] (0-indexed) ---
def parse_page_range(range_str: str) -> list[int]:
    if not range_str:
        return []

    pages = set()
    parts = range_str.split(',')

    for part in parts:
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                if start > end:
                    raise ValueError("Start of range cannot be greater than end.")
                pages.update(range(start - 1, end))  # 0-indexed
            except:
                raise ValueError(f"Invalid range segment: '{part}'")
        else:
            try:
                pages.add(int(part) - 1)
            except:
                raise ValueError(f"Invalid page number: '{part}'")

    return sorted(pages)