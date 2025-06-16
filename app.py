import os
import io
import json
import zipfile
import logging
from flask import Flask, render_template, request, jsonify, send_file, flash
from werkzeug.utils import secure_filename
from pathlib import Path
import tempfile
import shutil
from model1 import PDFTableExtractor

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
        logger.info("=== Starting PDF upload and processing ===")
        
        # Check if file was uploaded
        if 'file' not in request.files:
            logger.error("No file in request")
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            logger.error("Empty filename")
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            logger.error(f"Invalid file type: {file.filename}")
            return jsonify({'error': 'Invalid file type. Please upload a PDF file.'}), 400
        
        # Get API key from form
        api_key = request.form.get('api_key', '').strip()
        if not api_key:
            logger.error("No API key provided")
            return jsonify({'error': 'Please provide your Gemini API key'}), 400
        
        # Log API key format (first and last 4 chars only for security)
        logger.info(f"API key format: {api_key[:4]}...{api_key[-4:]}")
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        logger.info(f"File saved: {filepath}, Size: {os.path.getsize(filepath)} bytes")
        
        # Create temporary directory for this processing session
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"Created temp directory: {temp_dir}")
            
            try:
                # Initialize extractor with temporary directory
                logger.info("Initializing PDFTableExtractor...")
                extractor = PDFTableExtractor(api_key)
                
                # Override the base output directory to use temp directory
                extractor.base_output_dir = Path(temp_dir)
                extractor.base_output_dir.mkdir(exist_ok=True)
                
                logger.info("Starting PDF processing...")
                
                # Process PDF with detailed logging
                results = extractor.process_pdf(filepath)
                
                logger.info(f"Processing complete. Results: {json.dumps(results, indent=2, default=str)}")
                
            except Exception as api_error:
                logger.error(f"API/Processing error: {str(api_error)}")
                logger.error(f"Error type: {type(api_error).__name__}")
                
                # Clean up uploaded file
                if os.path.exists(filepath):
                    os.remove(filepath)
                
                # Check for specific API errors
                if "api key" in str(api_error).lower():
                    return jsonify({'error': 'Invalid Gemini API key. Please check your API key and try again.'}), 401
                elif "quota" in str(api_error).lower() or "rate limit" in str(api_error).lower():
                    return jsonify({'error': 'API quota exceeded or rate limited. Please try again later.'}), 429
                elif "permission" in str(api_error).lower():
                    return jsonify({'error': 'API permission denied. Please check your Gemini API key permissions.'}), 403
                else:
                    return jsonify({'error': f'Processing error: {str(api_error)}'}), 500
        
        # Clean up uploaded file
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info("Cleaned up uploaded file")
        
        # Check for errors
        if "error" in results:
            logger.error(f"Processing error: {results['error']}")
            return jsonify({'error': results['error']}), 500
        
        # Generate summary report
        try:
            summary_path = extractor.generate_summary_report(results)
            logger.info(f"Generated summary report: {summary_path}")
        except Exception as e:
            logger.warning(f"Failed to generate summary: {e}")
            summary_path = None
        
        # Check if any tables were found
        if not results.get('csv_files') or len(results['csv_files']) == 0:
            logger.warning("No tables found in PDF")
            
            # Provide detailed feedback
            feedback = {
                'success': False,
                'error': 'No tables were found in the PDF.',
                'debug_info': {
                    'total_pages': results.get('total_pages', 0),
                    'pages_processed': len(results.get('page_results', [])),
                    'api_calls_made': True,
                    'pdf_converted': results.get('total_pages', 0) > 0
                },
                'suggestions': [
                    'Ensure the PDF contains clear, well-formatted tables',
                    'Tables should have visible borders or clear column structure',
                    'Try a different page or section of the PDF',
                    'Check if the PDF is text-based (not scanned images)',
                    'Verify the table has headers and data rows'
                ]
            }
            
            return jsonify(feedback), 404
        
        # Create zip file with all results
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add CSV files
            files_added = 0
            for csv_file in results.get('csv_files', []):
                if os.path.exists(csv_file):
                    zip_file.write(csv_file, os.path.basename(csv_file))
                    files_added += 1
                    logger.info(f"Added to zip: {os.path.basename(csv_file)}")
            
            # Add summary report
            if summary_path and os.path.exists(summary_path):
                zip_file.write(summary_path, os.path.basename(summary_path))
                files_added += 1
                logger.info(f"Added summary to zip: {os.path.basename(summary_path)}")
        
        zip_buffer.seek(0)
        
        logger.info(f"Created zip file with {files_added} files")
        
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
        
        logger.info("Sending successful response with zip file")
        
        # Return zip file
        return send_file(
            io.BytesIO(zip_buffer.read()),
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{results['pdf_name']}_extracted_tables.zip"
        )
                
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        
        # Clean up uploaded file if it exists
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)
            logger.info("Cleaned up uploaded file after error")
        
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/debug', methods=['POST'])
def debug_extraction():
    """Debug endpoint to test extraction without file processing"""
    try:
        api_key = request.form.get('api_key', '').strip()
        if not api_key:
            return jsonify({'error': 'API key required for debug'}), 400
        
        # Test API key with a simple request
        import google.generativeai as genai
        
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            
            # Simple test
            response = model.generate_content("Hello, can you respond with 'API Working'?")
            
            return jsonify({
                'api_status': 'working',
                'response': response.text,
                'model': 'gemini-2.0-flash-exp'
            })
            
        except Exception as api_error:
            return jsonify({
                'api_status': 'error',
                'error': str(api_error),
                'error_type': type(api_error).__name__
            }), 400
    
    except Exception as e:
        return jsonify({'error': f'Debug error: {str(e)}'}), 500

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
