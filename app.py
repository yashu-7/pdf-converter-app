# app.py

import os
import shutil
import zipfile
from io import BytesIO
from flask import Flask, render_template, request, jsonify, send_from_directory

# ==============================================================================
# SECTION 1: CORE CONVERSION FUNCTIONS (Identical to before)
# ==============================================================================
# (Your original, pure Python conversion functions go here. They don't need Flask.)
def merge_pdfs(input_paths, output_path):
    from pypdf import PdfWriter
    merger = PdfWriter()
    for path in input_paths: merger.append(path)
    with open(output_path, "wb") as f_out: merger.write(f_out)

def split_pdf(input_path, output_folder):
    from pypdf import PdfReader, PdfWriter
    reader = PdfReader(input_path)
    if not os.path.exists(output_folder): os.makedirs(output_folder)
    for i, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)
        with open(os.path.join(output_folder, f"page_{i + 1}.pdf"), "wb") as f_out: writer.write(f_out)
    return len(reader.pages)

def convert_pdf_to_word(input_path, output_path):
    from pdf2docx import Converter
    cv = Converter(input_path)
    cv.convert(output_path, start=0, end=None)
    cv.close()

def convert_pdf_to_ppt(input_path, output_path):
    import fitz
    from pptx import Presentation
    from pptx.util import Inches
    pdf_doc = fitz.open(input_path)
    prs = Presentation()
    for page in pdf_doc:
        pix = page.get_pixmap(dpi=150)
        image_bytes = pix.tobytes("png")
        prs.slide_width = Inches(8)
        aspect_ratio = page.rect.width / page.rect.height
        prs.slide_height = int(prs.slide_width / aspect_ratio)
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        slide.shapes.add_picture(BytesIO(image_bytes), Inches(0), Inches(0), width=prs.slide_width, height=prs.slide_height)
    prs.save(output_path)


# ==============================================================================
# SECTION 2: FLASK APP SETUP
# ==============================================================================
app = Flask(__name__)

# --- Configuration ---
UPLOAD_FOLDER = 'temp_files'
OUTPUT_FOLDER = 'output_files'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# A dictionary to hold details about our tools
TOOLS = {
    "pdf-merger": {"title": "PDF Merger", "description": "Combine multiple PDFs into one document.", "icon": "🔗"},
    "split-pdf": {"title": "Split PDF", "description": "Split a single PDF into separate pages.", "icon": "✂️"},
    "pdf-to-word": {"title": "PDF to Word", "description": "Convert a PDF to an editable .docx file.", "icon": "📄"},
    "pdf-to-ppt": {"title": "PDF to PowerPoint", "description": "Convert a PDF into a .pptx presentation.", "icon": "🖼️"}
}

# --- Helper to ensure directories exist ---
def setup_dirs():
    for d in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
        if os.path.exists(d): shutil.rmtree(d)
        os.makedirs(d)

# ==============================================================================
# SECTION 3: FLASK ROUTES (The Web Logic)
# ==============================================================================
@app.route('/')
def home():
    """Renders the main homepage with the tool selection."""
    return render_template('index.html', tools=TOOLS)

@app.route('/<tool_name>')
def tool_page(tool_name):
    """Renders the page for a specific conversion tool."""
    if tool_name not in TOOLS:
        return "Tool not found!", 404
    return render_template('tool_page.html', tool=TOOLS[tool_name], tool_id=tool_name)

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handles the file upload and conversion logic."""
    setup_dirs()
    tool_id = request.form['tool_id']
    files = request.files.getlist('files[]') # Handles single or multiple files

    if not files or files[0].filename == '':
        return jsonify({'status': 'error', 'message': 'No files selected.'})

    try:
        # --- PDF MERGER LOGIC ---
        if tool_id == 'pdf-merger':
            if len(files) < 2:
                return jsonify({'status': 'error', 'message': 'Please select at least two files to merge.'})
            input_paths = []
            for file in files:
                path = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(path)
                input_paths.append(path)
            
            output_filename = "merged.pdf"
            output_path = os.path.join(OUTPUT_FOLDER, output_filename)
            merge_pdfs(input_paths, output_path)
            message = f"Successfully merged {len(files)} files."

        # --- SPLIT PDF LOGIC ---
        elif tool_id == 'split-pdf':
            file = files[0]
            path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(path)
            
            split_output_folder = os.path.join(OUTPUT_FOLDER, "split_pages")
            num_pages = split_pdf(path, split_output_folder)

            # Zip the split files for easy download
            output_filename = "split_pages.zip"
            zip_path = os.path.join(OUTPUT_FOLDER, output_filename)
            with zipfile.ZipFile(zip_path, 'w') as zf:
                for root, _, zfiles in os.walk(split_output_folder):
                    for zfile in zfiles: zf.write(os.path.join(root, zfile), arcname=zfile)
            message = f"Successfully split the PDF into {num_pages} pages."
        
        # --- GENERIC CONVERTER LOGIC ---
        else:
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

        return jsonify({'status': 'success', 'message': message, 'download_url': f'/download/{output_filename}'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': f'An error occurred: {str(e)}'})

@app.route('/download/<filename>')
def download_file(filename):
    """Provides the processed file for download."""
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True, port=5000)