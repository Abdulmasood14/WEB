import os
import io
import json
import zipfile
from flask import Flask, render_template, request, jsonify, send_file, flash
from werkzeug.utils import secure_filename
from pathlib import Path
import tempfile
import shutil
from model1 import PDFTableExtractor

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Configuration
UPLOAD_FOLDER = 'uploads'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create upload directory
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Please upload a PDF file.'}), 400
        
        # Get API key from form
        api_key = request.form.get('api_key', '').strip()
        if not api_key:
            return jsonify({'error': 'Please provide your Gemini API key'}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Create temporary directory for this processing session
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize extractor with temporary directory
            extractor = PDFTableExtractor(api_key)
            
            # Override the base output directory to use temp directory
            extractor.base_output_dir = Path(temp_dir)
            extractor.base_output_dir.mkdir(exist_ok=True)
            
            # Process PDF
            results = extractor.process_pdf(filepath)
            
            # Clean up uploaded file
            os.remove(filepath)
            
            # Check for errors
            if "error" in results:
                return jsonify({'error': results['error']}), 500
            
            # Generate summary report
            summary_path = extractor.generate_summary_report(results)
            
            # Create zip file with all results
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add CSV files
                for csv_file in results.get('csv_files', []):
                    if os.path.exists(csv_file):
                        zip_file.write(csv_file, os.path.basename(csv_file))
                
                # Add summary report
                if os.path.exists(summary_path):
                    zip_file.write(summary_path, os.path.basename(summary_path))
            
            zip_buffer.seek(0)
            
            # Prepare response data
            response_data = {
                'success': True,
                'pdf_name': results['pdf_name'],
                'total_pages': results['total_pages'],
                'pages_with_tables': results['pages_with_tables'],
                'total_tables_extracted': results['total_tables_extracted'],
                'csv_files_count': len(results['csv_files']),
                'extracted_titles': results.get('extracted_titles', []),
                'has_results': len(results['csv_files']) > 0
            }
            
            # Store zip in session (or return download link)
            # For simplicity, we'll return the zip file directly
            if len(results['csv_files']) > 0:
                return send_file(
                    io.BytesIO(zip_buffer.read()),
                    mimetype='application/zip',
                    as_attachment=True,
                    download_name=f"{results['pdf_name']}_extracted_tables.zip"
                )
            else:
                return jsonify({
                    'success': False,
                    'error': 'No tables were found in the PDF.'
                }), 404
                
    except Exception as e:
        # Clean up uploaded file if it exists
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)
        
        return jsonify({'error': f'Processing error: {str(e)}'}), 500

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
