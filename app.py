import os
import shutil
import zipfile
from io import BytesIO
from flask import Flask, render_template, request, jsonify, send_from_directory
import pdf2docx
import fitz
from pypdf import PdfWriter, PdfReader
from pptx import Presentation
from pptx.util import Inches
# --- NEW IMPORTS for Logging ---
import csv
from datetime import datetime

app = Flask(__name__)

# --- Configuration ---
UPLOAD_FOLDER = 'temp_files'
OUTPUT_FOLDER = 'output_files'
LOG_FILE = 'conversion_log.csv' # File to store logs
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# A dictionary to hold details about our tools
TOOLS = {
    "pdf-merger": {"title": "PDF Merger", "description": "Combine multiple PDFs into one document.", "icon": "🔗"},
    "split-pdf": {"title": "Split PDF", "description": "Split a single PDF into separate pages or at a specific page.", "icon": "✂️"},
    "pdf-to-word": {"title": "PDF to Word", "description": "Convert a PDF to an editable .docx file.", "icon": "📄"},
    "pdf-to-ppt": {"title": "PDF to PowerPoint", "description": "Convert a PDF into a .pptx presentation.", "icon": "🖼️"}
}

# --- Helper to ensure directories exist ---
def setup_dirs():
    for d in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d)

# --- NEW: Logging Function ---
def log_conversion(tool_id, status, details):
    """Logs a conversion event to the CSV file."""
    # Create file and write header if it doesn't exist
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'tool', 'status', 'details'])
            
    # Append the new log entry
    with open(LOG_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        writer.writerow([timestamp, tool_id, status, details])

# ==============================================================================
# SECTION 1: CORE CONVERSION FUNCTIONS (No changes here)
# ==============================================================================
def merge_pdfs(input_paths, output_path):
    merger = PdfWriter()
    for path in input_paths:
        merger.append(path)
    with open(output_path, "wb") as f_out:
        merger.write(f_out)

def split_pdf_all_pages(input_path, output_folder):
    reader = PdfReader(input_path)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    for i, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)
        with open(os.path.join(output_folder, f"page_{i + 1}.pdf"), "wb") as f_out:
            writer.write(f_out)
    return len(reader.pages)

def split_pdf_at_page(input_path, output_folder, split_page):
    reader = PdfReader(input_path)
    total_pages = len(reader.pages)
    if not (1 <= split_page < total_pages):
        raise ValueError(f"Invalid split page. Must be between 1 and {total_pages - 1}.")
    os.makedirs(output_folder, exist_ok=True)
    writer1 = PdfWriter()
    for i in range(split_page):
        writer1.add_page(reader.pages[i])
    part1_path = os.path.join(output_folder, f"Part1_Pages_1-{split_page}.pdf")
    with open(part1_path, "wb") as f_out:
        writer1.write(f_out)
    writer2 = PdfWriter()
    for i in range(split_page, total_pages):
        writer2.add_page(reader.pages[i])
    part2_path = os.path.join(output_folder, f"Part2_Pages_{split_page + 1}-{total_pages}.pdf")
    with open(part2_path, "wb") as f_out:
        writer2.write(f_out)
    return [part1_path, part2_path]

def convert_pdf_to_word(input_path, output_path):
    cv = pdf2docx.Converter(input_path)
    cv.convert(output_path, start=0, end=None)
    cv.close()

def convert_pdf_to_ppt(input_path, output_path):
    pdf_doc = fitz.open(input_path)
    prs = Presentation()
    for page in pdf_doc:
        pix = page.get_pixmap(dpi=150)
        image_bytes = pix.tobytes("png")
        prs.slide_width = Inches(8)
        aspect_ratio = page.rect.width / page.rect.height if page.rect.height > 0 else 1.33
        prs.slide_height = int(prs.slide_width / aspect_ratio)
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        slide.shapes.add_picture(BytesIO(image_bytes), Inches(0), Inches(0), width=prs.slide_width, height=prs.slide_height)
    prs.save(output_path)

# ==============================================================================
# SECTION 2: FLASK ROUTES
# ==============================================================================
@app.route('/')
def home():
    return render_template('index.html', tools=TOOLS)

@app.route('/<tool_name>')
def tool_page(tool_name):
    if tool_name not in TOOLS:
        return "Tool not found!", 404
    return render_template('tool_page.html', tool=TOOLS[tool_name], tool_id=tool_name)

@app.route('/upload', methods=['POST'])
def upload_files():
    setup_dirs()
    tool_id = request.form.get('tool_id')
    files = request.files.getlist('files[]')

    if not files or files[0].filename == '':
        return jsonify({'status': 'error', 'message': 'No files selected.'})

    try:
        if tool_id == 'pdf-merger':
            if len(files) < 2:
                raise ValueError('Please select at least two files to merge.')
            input_paths = [os.path.join(UPLOAD_FOLDER, f.filename) for f in files]
            for file, path in zip(files, input_paths):
                file.save(path)
            output_filename = "merged.pdf"
            merge_pdfs(input_paths, os.path.join(OUTPUT_FOLDER, output_filename))
            message = f"Successfully merged {len(files)} files."

        elif tool_id == 'split-pdf':
            file = files[0]
            path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(path)
            split_output_folder = os.path.join(OUTPUT_FOLDER, "split_pages")
            split_option = request.form.get('split-option')
            output_filename = "split_pages.zip"

            if split_option == 'range':
                split_page = request.form.get('split_page', type=int)
                if not split_page:
                    raise ValueError('Split page not provided for range split.')
                parts = split_pdf_at_page(path, split_output_folder, split_page)
                message = f"PDF successfully split at page {split_page}."
            else:
                num_pages = split_pdf_all_pages(path, split_output_folder)
                message = f"Successfully split the PDF into {num_pages} individual pages."
            
            with zipfile.ZipFile(os.path.join(OUTPUT_FOLDER, output_filename), 'w') as zf:
                for root, _, zfiles in os.walk(split_output_folder):
                    for zfile in zfiles:
                        zf.write(os.path.join(root, zfile), arcname=zfile)

        else: # Generic Converters
            file = files[0]
            path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(path)
            base_filename = os.path.splitext(file.filename)[0]
            
            if tool_id == 'pdf-to-word':
                output_filename = f"{base_filename}.docx"
                convert_pdf_to_word(path, os.path.join(OUTPUT_FOLDER, output_filename))
                message = "Successfully converted PDF to Word."
            elif tool_id == 'pdf-to-ppt':
                output_filename = f"{base_filename}.pptx"
                convert_pdf_to_ppt(path, os.path.join(OUTPUT_FOLDER, output_filename))
                message = "Successfully converted PDF to PowerPoint."
            else:
                raise ValueError("Invalid tool specified.")

        # --- On success, log and send result ---
        log_conversion(tool_id, 'success', message)
        return jsonify({'status': 'success', 'message': message, 'download_url': f'/download/{output_filename}'})

    except Exception as e:
        error_message = str(e)
        app.logger.error(f"An error occurred during {tool_id}: {error_message}", exc_info=True)
        # --- On failure, log and send error ---
        log_conversion(tool_id, 'error', error_message)
        return jsonify({'status': 'error', 'message': f'An error occurred: {error_message}'})

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=False)
