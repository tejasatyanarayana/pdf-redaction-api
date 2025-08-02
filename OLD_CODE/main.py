#OLD CODE
from fastapi import FastAPI, UploadFile, File,Form
from fastapi.responses import HTMLResponse, FileResponse
from OLD_CODE.redactor import redact_text
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
import os
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_methods=["*"],
    allow_headers=["*"],
)
class RedactionRequest(BaseModel):
    filename: str
    keywords: Optional[str] = ""
    page_range: Optional[str] = ""
    remove_graphics: Optional[bool] = False
    manual_boxes: Optional[list[dict]] = None  

@app.post("/redact/manual")
async def redact_with_manual(request: RedactionRequest):
    input_path = f"uploads/{request.filename}"
    output_path = f"outputs/redacted_{request.filename}"
    keywords = [k+' ' for k in request.keywords.split(",")] if request.keywords else []
    pages = parse_page_range(request.page_range)

    redact_text(
        input_path=input_path,
        output_path=output_path,
        keywords=keywords,
        pages=pages,
        remove_images=request.remove_graphics,
        manual_boxes=request.manual_boxes
    )

    return {
        "message": "Manual redaction complete",
        "redacted_file": output_path,
        "boxes": request.manual_boxes
    }
    
    
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    with open(f"uploads/{file.filename}", "wb") as f:
        f.write(contents)
    return {"filename": file.filename, "message": "File uploaded!"}    

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = f"outputs/redacted_{filename}"
    if os.path.exists(file_path):
        return FileResponse(
            path=file_path,
            filename=f"redacted_{filename}",
            media_type='application/pdf'
        )
    return {"error": "File not found"}

def parse_page_range(range_str: str) -> list[int]:
    if not range_str:
        return [] 
    
    pages = set()
    for part in range_str.split(','):
        if '-' in part:
            start, end = part.split('-')
            pages.update(range(int(start)-1, int(end)))  # 0-indexed
        else:
            pages.add(int(part)-1)
    print(pages)
    return sorted(pages)



# @app.get("/", response_class=HTMLResponse)
# def root():
#     return """
#     <h2>PDF Redaction PoC</h2>
#     <form action="/redact" enctype="multipart/form-data" method="post">
#         <input name="file" type="file" required><br><br>
#         <label>Page Range (e.g., 1-3,5):</label><br>
#         <input name="page_range" type="text" placeholder="Leave empty for all pages"><br><br>
#         <label>Redaction Keywords (comma-separated):</label><br>
#          <input name="keywords" type="text" placeholder="e.g., CONFIDENTIAL, John Doe"><br><br>
#          <label>
#             <input type="checkbox" name="remove_graphics" value="true">
#             Remove Logos / Graphics (optional)
#         </label><br><br>
#         <input type="submit" value="Redact PDF">
        
#     </form>
#     """




# @app.post("/redact")
# async def redact_pdf(file: UploadFile = File(...), keywords: str = Form(...),
#                      page_range: str = Form(""),remove_graphics: str = Form("false")):
#     input_path = f"uploads/{file.filename}"
#     output_path = f"outputs/redacted_{file.filename}"
    

#     contents = await file.read()
#     with open(input_path, "wb") as f:
#         f.write(contents)
#     keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
#     final_keyword_list = keyword_list + [k.upper() for k in keyword_list] + [k.casefold() for k in keyword_list] + [k.capitalize() for k in keyword_list]
#     final_keyword_list=list(set(final_keyword_list))
#     page_numbers = parse_page_range(page_range)
#     remove_images = remove_graphics.lower() == "true"
    
#     redact_text(input_path, output_path, keywords=final_keyword_list,pages=page_numbers,remove_images=remove_images)
#     return {"message": "Redacted successfully", "output_file": output_path, "keywords_used": final_keyword_list,"images_removed": remove_images}








