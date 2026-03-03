#!/usr/bin/env python3
"""
Texas Gaushala Newsletter PDF Editor
Uses PyMuPDF to directly edit the PDF - text replacement, image swaps, deletions.
No overlays, no page images, no font mismatches.
"""

import pymupdf
import sys
import os
import json

ORIGINAL_PDF = "/home/ubuntu/.openclaw/media/inbound/file_326---aa7db583-5d46-4a23-ac1e-f658f6ca027c.pdf"
OUTPUT_DIR = "/home/ubuntu/newsletter-editor"

def load_pdf(path=None):
    """Load the PDF document."""
    return pymupdf.open(path or ORIGINAL_PDF)

def list_images(doc, page_num=None):
    """List all images in the PDF with their xref, size, and bounding box."""
    pages = [page_num - 1] if page_num else range(len(doc))
    for i in pages:
        page = doc[i]
        print(f"\n=== PAGE {i+1} ===")
        imgs = page.get_images(full=True)
        for j, img in enumerate(imgs):
            xref = img[0]
            w, h = img[2], img[3]
            # Try to get bbox
            try:
                rects = page.get_image_rects(xref)
                for r in rects:
                    print(f"  [{j}] xref={xref} size={w}x{h} bbox=({r.x0:.0f},{r.y0:.0f},{r.x1:.0f},{r.y1:.0f})")
            except:
                print(f"  [{j}] xref={xref} size={w}x{h}")

def list_text(doc, page_num=None):
    """List all text blocks with positions."""
    pages = [page_num - 1] if page_num else range(len(doc))
    for i in pages:
        page = doc[i]
        print(f"\n=== PAGE {i+1} ===")
        blocks = page.get_text("blocks")
        for j, b in enumerate(blocks):
            text = b[4].strip().replace('\n', ' ')[:100]
            print(f"  [{j}] ({b[0]:.0f},{b[1]:.0f},{b[2]:.0f},{b[3]:.0f}) \"{text}\"")

def replace_text(doc, page_num, search, replacement, fontsize=None, fontname="helv"):
    """Search and replace text on a specific page."""
    page = doc[page_num - 1]
    hits = page.search_for(search)
    if not hits:
        print(f"  NOT FOUND on page {page_num}: '{search}'")
        return 0
    
    for rect in hits:
        # Get original text properties
        blocks = page.get_text("dict", clip=rect)["blocks"]
        orig_size = fontsize
        if not orig_size and blocks:
            for block in blocks:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        orig_size = span["size"]
                        break
        
        page.add_redact_annot(rect, replacement, 
                              fontname=fontname, 
                              fontsize=orig_size or 10,
                              align=pymupdf.TEXT_ALIGN_LEFT)
    
    page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)
    print(f"  REPLACED {len(hits)} occurrence(s) of '{search}' -> '{replacement}' on page {page_num}")
    return len(hits)

def delete_text(doc, page_num, search):
    """Delete text by redacting it (replaces with nothing)."""
    page = doc[page_num - 1]
    hits = page.search_for(search)
    if not hits:
        print(f"  NOT FOUND on page {page_num}: '{search}'")
        return 0
    
    for rect in hits:
        page.add_redact_annot(rect, "")
    
    page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)
    print(f"  DELETED {len(hits)} occurrence(s) of '{search}' on page {page_num}")
    return len(hits)

def replace_image(doc, page_num, img_index, new_image_path):
    """Replace an image on a specific page by its index."""
    page = doc[page_num - 1]
    imgs = page.get_images(full=True)
    
    if img_index >= len(imgs):
        print(f"  ERROR: Page {page_num} only has {len(imgs)} images (index {img_index} out of range)")
        return False
    
    xref = imgs[img_index][0]
    page.replace_image(xref, filename=new_image_path)
    print(f"  REPLACED image [{img_index}] xref={xref} on page {page_num} with {os.path.basename(new_image_path)}")
    return True

def delete_image(doc, page_num, img_index):
    """Delete an image from a page by redacting its area."""
    page = doc[page_num - 1]
    imgs = page.get_images(full=True)
    
    if img_index >= len(imgs):
        print(f"  ERROR: Page {page_num} only has {len(imgs)} images")
        return False
    
    xref = imgs[img_index][0]
    rects = page.get_image_rects(xref)
    for rect in rects:
        # Get background color from page
        page.add_redact_annot(rect, "")
    page.apply_redactions()
    print(f"  DELETED image [{img_index}] xref={xref} on page {page_num}")
    return True

def add_image(doc, page_num, image_path, rect_coords):
    """Add a new image at specified coordinates (x0, y0, x1, y1) in points."""
    page = doc[page_num - 1]
    rect = pymupdf.Rect(*rect_coords)
    page.insert_image(rect, filename=image_path)
    print(f"  ADDED image {os.path.basename(image_path)} at ({rect_coords}) on page {page_num}")
    return True

def add_text(doc, page_num, text, position, fontsize=10, fontname="helv", color=(0, 0, 0)):
    """Add new text at specified position (x, y) in points."""
    page = doc[page_num - 1]
    point = pymupdf.Point(*position)
    page.insert_text(point, text, fontsize=fontsize, fontname=fontname, color=color)
    print(f"  ADDED text at ({position}) on page {page_num}")

def save_pdf(doc, output_name="newsletter_edited.pdf"):
    """Save the modified PDF."""
    output_path = os.path.join(OUTPUT_DIR, output_name)
    doc.save(output_path, garbage=3, deflate=True)
    print(f"\nSaved to: {output_path}")
    return output_path

def render_pages(doc, output_dir=None, dpi=150):
    """Render all pages as JPGs for preview."""
    output_dir = output_dir or os.path.join(OUTPUT_DIR, "preview")
    os.makedirs(output_dir, exist_ok=True)
    for i in range(len(doc)):
        page = doc[i]
        pix = page.get_pixmap(dpi=dpi)
        path = os.path.join(output_dir, f"page-{i+1}.jpg")
        pix.save(path)
        print(f"  Rendered page {i+1} -> {path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 pdf_editor.py info [page]        - List all text and images")
        print("  python3 pdf_editor.py images [page]      - List images only")
        print("  python3 pdf_editor.py text [page]        - List text blocks only")
        print("  python3 pdf_editor.py preview [dpi]      - Render pages as JPGs")
        print("")
        print("Edit operations are done via the apply_edits() function")
        print("or by importing this module in Python.")
        sys.exit(0)
    
    cmd = sys.argv[1]
    doc = load_pdf()
    page = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    if cmd == "info":
        list_images(doc, page)
        list_text(doc, page)
    elif cmd == "images":
        list_images(doc, page)
    elif cmd == "text":
        list_text(doc, page)
    elif cmd == "preview":
        dpi = int(sys.argv[2]) if len(sys.argv) > 2 else 150
        render_pages(doc, dpi=dpi)
    
    doc.close()
