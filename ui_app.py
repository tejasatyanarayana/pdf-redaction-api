import streamlit as st
import requests
from PIL import Image
import fitz  # PyMuPDF
import os
from streamlit_drawable_canvas import st_canvas
import zipfile
import tempfile
from pathlib import Path
import json

st.set_page_config(page_title="PDF Redaction PoC", layout="wide")
st.title("🔒 PDF Redaction Proof of Concept")

# Initialize session state
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = {}
if "current_file_index" not in st.session_state:
    st.session_state.current_file_index = 0
if "selected_page" not in st.session_state:
    st.session_state.selected_page = 0
if "manual_boxes" not in st.session_state:
    st.session_state.manual_boxes = {}
if "last_canvas_state" not in st.session_state:
    st.session_state.last_canvas_state = {}
# New: Track canvas version to force re-render
if "canvas_version" not in st.session_state:
    st.session_state.canvas_version = 0

# Upload mode selection
upload_mode = st.radio("Upload Mode", ["Single File", "Batch Upload"], horizontal=True)

# File upload
if upload_mode == "Single File":
    uploaded_files = st.file_uploader("Upload a PDF", type=["pdf"], accept_multiple_files=False)
    if uploaded_files:
        uploaded_files = [uploaded_files]  # Convert to list for uniform handling
else:
    uploaded_files = st.file_uploader("Upload PDF files", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    # Process uploaded files
    for idx, uploaded_file in enumerate(uploaded_files):
        if uploaded_file.name not in st.session_state.uploaded_files:
            filename = uploaded_file.name
            upload_path = f"uploads/{filename}"
            
            # Create uploads directory if it doesn't exist
            os.makedirs("uploads", exist_ok=True)
            
            with open(upload_path, "wb") as f:
                f.write(uploaded_file.read())
            
            # Store file info
            st.session_state.uploaded_files[filename] = {
                "path": upload_path,
                "index": len(st.session_state.uploaded_files)
            }
    
    st.success(f"✅ {len(uploaded_files)} file(s) uploaded successfully!")
    
    # File navigation for batch uploads
    if len(st.session_state.uploaded_files) > 1:
        st.subheader("📁 File Navigation")
        file_names = list(st.session_state.uploaded_files.keys())
        
        # File selection
        file_nav_col1, file_nav_col2, file_nav_col3 = st.columns([1, 3, 1])
        with file_nav_col1:
            if st.button("⬅️ Previous File", key="prev_file") and st.session_state.current_file_index > 0:
                st.session_state.current_file_index -= 1
                st.session_state.selected_page = 0
                st.session_state.canvas_version += 1  # Increment to force canvas refresh
                st.rerun()
        with file_nav_col3:
            if st.button("Next File ➡️", key="next_file") and st.session_state.current_file_index < len(file_names) - 1:
                st.session_state.current_file_index += 1
                st.session_state.selected_page = 0
                st.session_state.canvas_version += 1  # Increment to force canvas refresh
                st.rerun()
        with file_nav_col2:
            current_file = file_names[st.session_state.current_file_index]
            st.markdown(f"<div style='text-align:center;'>**File {st.session_state.current_file_index + 1} of {len(file_names)}**: {current_file}</div>", unsafe_allow_html=True)
    else:
        st.session_state.current_file_index = 0
        current_file = list(st.session_state.uploaded_files.keys())[0]
    
    # Get current file
    current_file = list(st.session_state.uploaded_files.keys())[st.session_state.current_file_index]
    current_file_path = st.session_state.uploaded_files[current_file]["path"]
    
    # Load current PDF
    doc = fitz.open(current_file_path)
    num_pages = len(doc)

    # Reset page if it's out of bounds for the current file
    if st.session_state.selected_page >= num_pages:
        st.session_state.selected_page = 0

    selected_page = st.session_state.selected_page
    page = doc[selected_page]

    # Render selected page as image
    pix = page.get_pixmap(dpi=72)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # Page navigation
    st.subheader("📄 Page Navigation")
    page_nav_col1, page_nav_col2, page_nav_col3 = st.columns([1, 3, 1])
    with page_nav_col1:
        if st.button("⬅️", key="prev_page") and selected_page > 0:
            st.session_state.selected_page -= 1
            st.session_state.canvas_version += 1  # Increment to force canvas refresh
            st.rerun()
    with page_nav_col3:
        if st.button("➡️", key="next_page") and selected_page < num_pages - 1:
            st.session_state.selected_page += 1
            st.session_state.canvas_version += 1  # Increment to force canvas refresh
            st.rerun()
    with page_nav_col2:
        st.markdown(f"<div style='text-align:center;'>**Page {selected_page + 1} of {num_pages}**</div>", unsafe_allow_html=True)

    # Calculate display dimensions
    max_width = 800
    scale_factor = min(max_width / img.width, max_width / img.height)
    display_width = int(img.width * scale_factor)
    display_height = int(img.height * scale_factor)
    
    # Resize image for consistent display
    display_img = img.resize((display_width, display_height), Image.Resampling.LANCZOS)

    # Side by side layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 Page Preview")
        st.image(display_img, caption=f"Page {selected_page + 1}", use_container_width=False)
    
    with col2:
        st.subheader(f"✍️ Draw Redaction Boxes")
        
        # Create unique canvas key with version
        canvas_key = f"canvas_{current_file}_{selected_page}_{st.session_state.canvas_version}"
        
        # Get existing boxes for this file-page combination
        file_page_key = f"{current_file}_{selected_page}"
        existing_boxes = st.session_state.manual_boxes.get(file_page_key, [])
        
        # Create initial drawing state
        initial_drawing = {
            "version": "4.4.0",
            "objects": []
        }
        
        # Pre-populate canvas with existing boxes
        if existing_boxes:
            for box in existing_boxes:
                canvas_obj = {
                    "type": "rect",
                    "left": box["x0"] * scale_factor,
                    "top": box["y0"] * scale_factor,
                    "width": (box["x1"] - box["x0"]) * scale_factor,
                    "height": (box["y1"] - box["y0"]) * scale_factor,
                    "fill": "rgba(255, 0, 0, 0.3)",
                    "stroke": "red",
                    "strokeWidth": 2
                }
                initial_drawing["objects"].append(canvas_obj)
        
        try:
            canvas_result = st_canvas(
                fill_color="rgba(255, 0, 0, 0.3)",
                stroke_width=2,
                stroke_color="red",
                background_image=display_img,
                update_streamlit=True,
                height=display_height,
                width=display_width,
                drawing_mode="rect",
                initial_drawing=initial_drawing,
                key=canvas_key
            )
            
            # Process canvas result and update session state
            if canvas_result and canvas_result.json_data is not None:
                current_page_boxes = []
                
                # Extract boxes from canvas
                if "objects" in canvas_result.json_data:
                    for obj in canvas_result.json_data["objects"]:
                        if obj["type"] == "rect":
                            x0 = obj["left"] / scale_factor
                            y0 = obj["top"] / scale_factor
                            x1 = (obj["left"] + obj["width"]) / scale_factor
                            y1 = (obj["top"] + obj["height"]) / scale_factor
                            current_page_boxes.append({
                                "filename": current_file,
                                "page": selected_page,
                                "x0": x0,
                                "y0": y0,
                                "x1": x1,
                                "y1": y1
                            })
                
                # Update session state only if boxes have changed
                if current_page_boxes != st.session_state.manual_boxes.get(file_page_key, []):
                    st.session_state.manual_boxes[file_page_key] = current_page_boxes
                    st.session_state.last_canvas_state[canvas_key] = json.dumps(current_page_boxes)
                    
        except Exception as e:
            st.error(f"Error rendering canvas on Page {selected_page + 1}: {e}")
            canvas_result = None

    doc.close()

    # Show current page boxes count
    file_page_key = f"{current_file}_{selected_page}"
    current_boxes = st.session_state.manual_boxes.get(file_page_key, [])
    if current_boxes:
        st.info(f"Current page has {len(current_boxes)} redaction boxes")

    # Show summary of all redaction boxes
    if st.session_state.manual_boxes:
        st.subheader("📋 Redaction Summary")
        total_boxes = sum(len(boxes) for boxes in st.session_state.manual_boxes.values())
        files_with_boxes = len(set(key.split('_')[0] for key in st.session_state.manual_boxes.keys() if st.session_state.manual_boxes[key]))
        st.info(f"Total redaction boxes: {total_boxes} across {files_with_boxes} files")
        
        # Show detailed breakdown
        if st.expander("View detailed breakdown"):
            for file_page_key, boxes in st.session_state.manual_boxes.items():
                if boxes:
                    file_name, page_num = file_page_key.rsplit('_', 1)
                    st.write(f"**{file_name}** - Page {int(page_num) + 1}: {len(boxes)} boxes")

    # Redaction config
    st.subheader("🛠️ Redaction Settings")
    keywords = st.text_input("Redaction Keywords (comma-separated)", value="")
    page_range = st.text_input("Page Range (e.g., 1-3,5) - Leave empty for all pages", value="")
    remove_graphics = st.checkbox("Remove Images / Logos")

    # Batch processing options
    st.subheader("🔄 Processing Options")
    process_mode = st.radio("Processing Mode", ["Current File Only", "All Uploaded Files"], horizontal=True)

    # Debug section
    with st.expander("Debug Info"):
        st.write(f"Current file: {current_file}")
        st.write(f"Current page: {selected_page}")
        st.write(f"Canvas key: {canvas_key}")
        st.write(f"File-page key: {file_page_key}")
        st.write(f"Boxes for current page: {len(current_boxes)}")

    # Submit redaction request
    if st.button("🔴 Redact"):
        if process_mode == "Current File Only":
            file_boxes = []
            for key, boxes in st.session_state.manual_boxes.items():
                if key.startswith(current_file + "_"):
                    file_boxes.extend(boxes)
            
            data = {
                "filename": current_file,
                "keywords": keywords,
                "page_range": page_range,
                "remove_graphics": remove_graphics,
                "manual_boxes": file_boxes
            }

            with st.spinner(f"Redacting {current_file}..."):
                response = requests.post("http://localhost:8000/redact/manual", json=data)

            if response.status_code == 200:
                st.success("✅ Redaction complete")
                output_file = response.json()["redacted_file"]
                with open(output_file, "rb") as f:
                    st.download_button("⬇️ Download Redacted PDF", f, file_name=f"{current_file}_redacted.pdf")
            else:
                st.error("❌ Redaction failed. Please check backend logs.")
        
        else:
            redacted_files = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for idx, filename in enumerate(st.session_state.uploaded_files.keys()):
                status_text.text(f"Processing {filename}...")
                
                file_boxes = []
                for key, boxes in st.session_state.manual_boxes.items():
                    if key.startswith(filename + "_"):
                        file_boxes.extend(boxes)
                
                data = {
                    "filename": filename,
                    "keywords": keywords,
                    "page_range": page_range,
                    "remove_graphics": remove_graphics,
                    "manual_boxes": file_boxes
                }

                response = requests.post("http://localhost:8000/redact/manual", json=data)
                
                if response.status_code == 200:
                    output_file = response.json()["redacted_file"]
                    redacted_files.append(output_file)
                else:
                    st.error(f"❌ Failed to redact {filename}")
                
                progress_bar.progress((idx + 1) / len(st.session_state.uploaded_files))
            
            status_text.text("Processing complete!")
            
            if redacted_files:
                if len(redacted_files) == 1:
                    with open(redacted_files[0], "rb") as f:
                        st.download_button("⬇️ Download Redacted PDF", f, file_name=f"{redacted_files[0].split('/')[-1]}")
                else:
                    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
                        with zipfile.ZipFile(tmp_zip.name, 'w') as zipf:
                            for file_path in redacted_files:
                                zipf.write(file_path, os.path.basename(file_path))
                        
                        with open(tmp_zip.name, "rb") as f:
                            st.download_button("⬇️ Download All Redacted PDFs (ZIP)", f, file_name="redacted_pdfs.zip", mime="application/zip")
                
                st.success(f"✅ Successfully processed {len(redacted_files)} files")

    # Clear all data button
    if st.button("🗑️ Clear All Data"):
        st.session_state.uploaded_files = {}
        st.session_state.current_file_index = 0
        st.session_state.selected_page = 0
        st.session_state.manual_boxes = {}
        st.session_state.last_canvas_state = {}
        st.session_state.canvas_version = 0
        st.rerun()

    # Clear current page boxes
    if st.button("🗑️ Clear Current Page Boxes"):
        file_page_key = f"{current_file}_{selected_page}"
        if file_page_key in st.session_state.manual_boxes:
            del st.session_state.manual_boxes[file_page_key]
        st.session_state.canvas_version += 1  # Increment to force canvas refresh
        st.rerun()