import fitz  # PyMuPDF for working with PDFs
import os

def redact_text(input_path: str, output_path: str, keywords: list[str],
                pages: list[int] = None, placeholder: str = "[---REDACTED---]",
                remove_images: bool = False, manual_boxes: list[dict] = None):
    """
    Redacts keywords and/or specific rectangular areas from a PDF file.
    Also allows removing images from selected pages.
    """

    # Make sure input file exists
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Try opening the PDF
    try:
        doc = fitz.open(input_path)
    except Exception as e:
        raise ValueError(f"Failed to open PDF: {e}")

    try:
        for i, page in enumerate(doc):
            # If pages are specified, skip everything else
            if pages is not None and i not in pages:
                continue

            # Search for each keyword and mark it for redaction
            for keyword in keywords:
                if not keyword.strip():
                    continue  # Skip empty strings
                try:
                    matches = page.search_for(keyword)
                    for inst in matches:
                        page.add_redact_annot(inst, fill=(1, 1, 0), text=placeholder)
                except Exception as e:
                    print(f"Error searching keyword '{keyword}' on page {i}: {e}")

            # Handle manual redaction boxes, if provided
            if manual_boxes:
                for box in manual_boxes:
                    if box.get("page") != i:
                        continue
                    try:
                        # Validate and create rectangle
                        rect = fitz.Rect(
                            max(0, box["x0"]),
                            max(0, box["y0"]),
                            max(0, box["x1"]),
                            max(0, box["y1"]),
                        )
                        page.add_redact_annot(rect, fill=(1, 1, 0), text=placeholder)
                    except Exception as e:
                        print(f"Invalid box format on page {i}: {e}")

            # If images should be removed, go for it
            if remove_images:
                try:
                    for img in page.get_images(full=True):
                        xref = img[0]
                        page.delete_image(xref)
                except Exception as e:
                    print(f"Failed to remove image on page {i}: {e}")

            # Finally, apply all the redactions made above
            try:
                page.apply_redactions()
            except Exception as e:
                print(f"Failed to apply redactions on page {i}: {e}")

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Save and close the document
        doc.save(output_path)
        doc.close()

        return output_path

    except Exception as e:
        doc.close()
        raise RuntimeError(f"Redaction process failed: {e}")
