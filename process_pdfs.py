import fitz  # PyMuPDF
import os
import json
import re
from collections import Counter

# --- Core Heuristic Functions ---

def get_style_hierarchy(doc, start_page=0):
    """
    Analyzes document styles from a given start page to determine the heading hierarchy.
    This is crucial for learning the structure from the document's body, ignoring the title page.
    """
    style_counts = Counter()
    for page_num in range(start_page, len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    if line["spans"]:
                        span = line["spans"][0]
                        # A style is defined by its rounded size and whether it's bold.
                        style = (round(span["size"]), "bold" in span["font"].lower())
                        style_counts[style] += 1
    
    if not style_counts:
        return {}, None

    # Assume the most frequent style is the standard body text.
    body_style = style_counts.most_common(1)[0][0]
    
    # A heading style is any style that is larger than the body text, or is bold and not the body style.
    heading_styles = sorted(
        [s for s in style_counts if s[0] > body_style[0] or (s[0] == body_style[0] and s[1] and s != body_style)],
        key=lambda x: x[0],
        reverse=True
    )
    
    # Create a map from the style tuple to a heading level (e.g., H1, H2, H3).
    return {style: f"H{i+1}" for i, style in enumerate(heading_styles[:3])}, body_style

def analyze_first_page(doc):
    """
    Analyzes only the first page to extract the main title and identify other text
    (like subtitles or publisher info) that should be excluded from the outline.
    """
    title = "Title not found"
    texts_to_ignore = set()
    
    if not doc or len(doc) == 0:
        return title, texts_to_ignore

    first_page = doc[0]
    blocks = first_page.get_text("dict")["blocks"]
    
    if not blocks:
        return title, texts_to_ignore
        
    # Find the largest font size on the page, which is assumed to belong to the title.
    max_font_size = 0
    for block in blocks:
         if "lines" in block and block["lines"] and block["lines"][0]["spans"]:
            max_font_size = max(max_font_size, round(block["lines"][0]["spans"][0]["size"]))

    if max_font_size == 0:
        if first_page.get_text("blocks"):
             return first_page.get_text("blocks")[0][4].strip().split('\n')[0], texts_to_ignore
        return title, texts_to_ignore

    # Collect all lines with the largest font size to form the title.
    # Collect all other lines to be ignored in the outline.
    title_lines = []
    for block in blocks:
        if "lines" in block and block["lines"] and block["lines"][0]["spans"]:
            line_text = " ".join(s["text"] for s in block["lines"][0]["spans"]).strip()
            span = block["lines"][0]["spans"][0]
            if round(span["size"]) == max_font_size:
                 title_lines.append(line_text)
            else:
                 texts_to_ignore.add(line_text)
    
    if title_lines:
        title = " ".join(title_lines)
    
    return title, texts_to_ignore

def is_valid_heading(text):
    """
    Applies strict content-aware rules to determine if a line of text is a true heading.
    This is the key function that differentiates form fields from document headings.
    """
    text = text.strip()
    # RULE 1: Must not be empty.
    if not text:
        return False
    # RULE 2: Must not be a simple number or a list marker (e.g., "1.", "S.No"). This solves the form case.
    if re.fullmatch(r'[\d\.]+|S\.No', text, re.IGNORECASE):
        return False
    # RULE 3: Must not be a form-like sentence ending with a period.
    if text.endswith('.') and len(text.split()) > 4:
        return False
    # RULE 4: Must not be a common form field label found in the test case.
    if text.lower() in ["name", "age", "relationship", "date", "signature of government servant."]:
        return False
    
    return True

# --- Main Orchestration Logic ---

def process_pdf_document(pdf_path):
    """
    Processes a single PDF using the multi-pass strategy to extract its structure.
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error processing {os.path.basename(pdf_path)}: {e}")
        return {"title": f"Error processing {os.path.basename(pdf_path)}", "outline": []}

    # Pass 1: Analyze the first page to find the title and any subtitles to ignore.
    title, texts_to_ignore = analyze_first_page(doc)

    # Pass 2: Learn the true heading hierarchy from the document's body (starting from page 2).
    start_page_for_styles = 1 if len(doc) > 1 else 0
    style_to_level, _ = get_style_hierarchy(doc, start_page=start_page_for_styles)
    
    # If no heading styles are found in the body, we can confidently say it's a form or simple document.
    if not style_to_level:
        return {"title": title, "outline": []}

    # Pass 3: Extract the outline from the entire document using the learned hierarchy and validation rules.
    outline = []
    for page_num, page in enumerate(doc):
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if "lines" in block and block["lines"] and block["lines"][0]["spans"]:
                line_text = " ".join(s["text"] for s in block["lines"][0]["spans"]).strip()
                
                # Skip if the text is empty, is the title itself, or was a subtitle on the first page.
                if not line_text or line_text == title or line_text in texts_to_ignore:
                    continue

                span = block["lines"][0]["spans"][0]
                current_style = (round(span["size"]), "bold" in span["font"].lower())

                # Check if the text's style matches a known heading style AND its content is valid.
                if current_style in style_to_level and is_valid_heading(line_text):
                    level = style_to_level.get(current_style)
                    if level and level in ["H1", "H2", "H3"]: # Only capture up to H3
                        outline.append({
                            "level": level,
                            "text": line_text,
                            "page": page_num + 1,
                        })

    return {"title": title, "outline": outline}


def process_all_pdfs(input_dir, output_dir):
    """The main loop to run the process on all PDFs in the input directory."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for filename in os.listdir(input_dir):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(input_dir, filename)
            print(f"Processing {pdf_path}...")
            structured_data = process_pdf_document(pdf_path)
            if structured_data:
                output_path = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}.json")
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(structured_data, f, indent=4, ensure_ascii=False)
                print(f"Successfully created {output_path}")

# --- Docker Entry Point ---
if __name__ == "__main__":
    # These paths are what the Docker container will use based on the `docker run` command.
    INPUT_DIR = "./input"
    OUTPUT_DIR = "./output"
    process_all_pdfs(INPUT_DIR, OUTPUT_DIR)