import fitz 
import os

def redact_text(input_path: str, output_path: str, keywords: list[str],
                pages: list[int] = None, placeholder: str = "[---REDACTED---],",
                remove_images: bool = False, manual_boxes: list[dict] = None ):
    doc = fitz.open(input_path)
    for i, page in enumerate(doc):
        if pages and i not in pages:
            continue

        for keyword in keywords:
            text_instances = page.search_for(keyword)
            for inst in text_instances:
                page.add_redact_annot(inst, fill=(1, 1, 0), text=placeholder)
                
        if manual_boxes:
            for box in manual_boxes:
                if box["page"] == i:
                    rect = fitz.Rect(box["x0"], box["y0"], box["x1"], box["y1"])#remove -ve values if using streamlit #teja
                    page.add_redact_annot(rect, fill=(1, 1, 0), text=placeholder)
                
        if remove_images:
            image_list = page.get_images(full=True)
            for img in image_list:
                xref = img[0]
                page.delete_image(xref)        
        page.apply_redactions()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    doc.close()
    return output_path
