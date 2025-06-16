import os
import io
import json
import zipfile
import logging
import traceback
import sys
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from pathlib import Path
import tempfile
import shutil

# Configure logging to show everything
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Configuration
UPLOAD_FOLDER = 'uploads'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
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
    """Upload and process PDF file with detailed error reporting"""
    filepath = None
    temp_dir = None
    
    try:
        logger.info("=== STARTING PDF PROCESSING ===")
        
        # Step 1: Validate request
        if 'file' not in request.files:
            error_msg = "No file found in request"
            logger.error(error_msg)
            return jsonify({'error': error_msg, 'step': 'file_validation'}), 400
        
        file = request.files['file']
        if file.filename == '':
            error_msg = "No file selected"
            logger.error(error_msg)
            return jsonify({'error': error_msg, 'step': 'file_validation'}), 400
        
        if not allowed_file(file.filename):
            error_msg = f"Invalid file type: {file.filename}. Only PDF files are allowed."
            logger.error(error_msg)
            return jsonify({'error': error_msg, 'step': 'file_validation'}), 400
        
        # Step 2: Validate API key
        api_key = request.form.get('api_key', '').strip()
        if not api_key:
            error_msg = "API key is required"
            logger.error(error_msg)
            return jsonify({'error': error_msg, 'step': 'api_key_validation'}), 400
        
        logger.info(f"File: {file.filename}, API key length: {len(api_key)}")
        
        # Step 3: Save uploaded file
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            file_size = os.path.getsize(filepath)
            logger.info(f"File saved: {filepath} ({file_size} bytes)")
        except Exception as e:
            error_msg = f"Failed to save file: {str(e)}"
            logger.error(error_msg)
            return jsonify({'error': error_msg, 'step': 'file_save'}), 500
        
        # Step 4: Validate PDF
        try:
            with open(filepath, 'rb') as f:
                header = f.read(4)
                if header != b'%PDF':
                    os.remove(filepath)
                    error_msg = "File is not a valid PDF"
                    logger.error(error_msg)
                    return jsonify({'error': error_msg, 'step': 'pdf_validation'}), 400
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            error_msg = f"Error validating PDF: {str(e)}"
            logger.error(error_msg)
            return jsonify({'error': error_msg, 'step': 'pdf_validation'}), 400
        
        # Step 5: Test imports
        try:
            logger.info("Testing imports...")
            import google.generativeai as genai
            logger.info("✓ google.generativeai imported")
            
            import pandas as pd
            logger.info("✓ pandas imported")
            
            import fitz
            logger.info("✓ PyMuPDF imported")
            
            from model1 import PDFTableExtractor
            logger.info("✓ PDFTableExtractor imported")
            
        except ImportError as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            error_msg = f"Missing dependency: {str(e)}"
            logger.error(error_msg)
            return jsonify({
                'error': error_msg, 
                'step': 'import_validation',
                'suggestion': 'Server configuration issue - missing Python packages'
            }), 500
        
        # Step 6: Test API connection
        try:
            logger.info("Testing API connection...")
            genai.configure(api_key=api_key)
            test_model = genai.GenerativeModel('gemini-2.0-flash-exp')
            test_response = test_model.generate_content("Hello")
            logger.info("✓ API connection successful")
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            error_msg = f"API connection failed: {str(e)}"
            logger.error(error_msg)
            
            if "api key" in str(e).lower() or "invalid" in str(e).lower():
                return jsonify({
                    'error': 'Invalid API key. Please check your Gemini API key.',
                    'step': 'api_test'
                }), 401
            else:
                return jsonify({
                    'error': error_msg,
                    'step': 'api_test'
                }), 500
        
        # Step 7: Create temp directory
        try:
            temp_dir = tempfile.mkdtemp()
            logger.info(f"Created temp directory: {temp_dir}")
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            error_msg = f"Failed to create temp directory: {str(e)}"
            logger.error(error_msg)
            return jsonify({'error': error_msg, 'step': 'temp_dir'}), 500
        
        # Step 8: Initialize extractor
        try:
            logger.info("Initializing PDF extractor...")
            extractor = PDFTableExtractor(api_key)
            extractor.base_output_dir = Path(temp_dir)
            extractor.base_output_dir.mkdir(exist_ok=True)
            logger.info("✓ Extractor initialized")
        except Exception as e:
            cleanup_files(filepath, temp_dir)
            error_msg = f"Failed to initialize extractor: {str(e)}"
            logger.error(error_msg)
            return jsonify({'error': error_msg, 'step': 'extractor_init'}), 500
        
        # Step 9: Process PDF
        try:
            logger.info("Processing PDF...")
            results = extractor.process_pdf(filepath)
            logger.info(f"Processing complete: {len(results.get('csv_files', []))} files generated")
        except Exception as e:
            cleanup_files(filepath, temp_dir)
            error_msg = f"PDF processing failed: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({
                'error': error_msg,
                'step': 'pdf_processing',
                'traceback': traceback.format_exc()
            }), 500
        
        # Step 10: Clean up original file
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # Step 11: Check results
        if "error" in results:
            cleanup_files(None, temp_dir)
            return jsonify({'error': results['error'], 'step': 'processing_result'}), 500
        
        csv_files = results.get('csv_files', [])
        if not csv_files:
            cleanup_files(None, temp_dir)
            return jsonify({
                'error': 'No tables found in PDF',
                'step': 'table_detection',
                'debug_info': {
                    'total_pages': results.get('total_pages', 0),
                    'pages_with_tables': results.get('pages_with_tables', 0)
                },
                'suggestions': [
                    'Ensure PDF contains clear table structures',
                    'Check if PDF is text-based (not scanned)',
                    'Try a different PDF with simpler tables'
                ]
            }), 404
        
        # Step 12: Create ZIP file
        try:
            logger.info("Creating ZIP file...")
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                files_added = 0
                for csv_file in csv_files:
                    if os.path.exists(csv_file):
                        zip_file.write(csv_file, os.path.basename(csv_file))
                        files_added += 1
                
                # Add summary if exists
                try:
                    summary_path = extractor.generate_summary_report(results)
                    if os.path.exists(summary_path):
                        zip_file.write(summary_path, os.path.basename(summary_path))
                        files_added += 1
                except:
                    pass
            
            cleanup_files(None, temp_dir)
            zip_buffer.seek(0)
            
            logger.info(f"✓ ZIP created with {files_added} files")
            
            return send_file(
                io.BytesIO(zip_buffer.read()),
                mimetype='application/zip',
                as_attachment=True,
                download_name=f"{results.get('pdf_name', 'tables')}_extracted.zip"
            )
            
        except Exception as e:
            cleanup_files(None, temp_dir)
            error_msg = f"Failed to create ZIP: {str(e)}"
            logger.error(error_msg)
            return jsonify({'error': error_msg, 'step': 'zip_creation'}), 500
        
    except Exception as e:
        cleanup_files(filepath, temp_dir)
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': error_msg,
            'step': 'unexpected_error',
            'traceback': traceback.format_exc()
        }), 500

def cleanup_files(filepath, temp_dir):
    """Clean up temporary files"""
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
    except:
        pass

@app.route('/debug', methods=['POST'])
def debug_extraction():
    """Test API connection"""
    try:
        api_key = request.form.get('api_key', '').strip()
        if not api_key:
            return jsonify({'error': 'API key required'}), 400
        
        # Test imports first
        try:
            import google.generativeai as genai
        except ImportError as e:
            return jsonify({
                'api_status': 'error',
                'error': f'Missing google-generativeai library: {str(e)}',
                'step': 'import_test'
            }), 500
        
        # Test API
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            response = model.generate_content("Hello, respond with 'API Working'")
            
            return jsonify({
                'api_status': 'working',
                'response': response.text,
                'model': 'gemini-2.0-flash-exp'
            })
            
        except Exception as e:
            error_msg = str(e).lower()
            if "api key" in error_msg or "invalid" in error_msg:
                status = "Invalid API key"
            elif "quota" in error_msg:
                status = "Quota exceeded"
            else:
                status = f"API error: {str(e)}"
            
            return jsonify({
                'api_status': 'error',
                'error': status,
                'details': str(e)
            }), 400
            
    except Exception as e:
        return jsonify({
            'api_status': 'error',
            'error': f'Debug error: {str(e)}'
        }), 500

@app.route('/health')
def health_check():
    """Health check with dependency status"""
    dependencies = {}
    
    try:
        import google.generativeai
        dependencies['google-generativeai'] = 'OK'
    except ImportError as e:
        dependencies['google-generativeai'] = f'ERROR: {str(e)}'
    
    try:
        import pandas
        dependencies['pandas'] = 'OK'
    except ImportError as e:
        dependencies['pandas'] = f'ERROR: {str(e)}'
    
    try:
        import fitz
        dependencies['PyMuPDF'] = 'OK'
    except ImportError as e:
        dependencies['PyMuPDF'] = f'ERROR: {str(e)}'
    
    try:
        from model1 import PDFTableExtractor
        dependencies['model1'] = 'OK'
    except ImportError as e:
        dependencies['model1'] = f'ERROR: {str(e)}'
    
    return jsonify({
        'status': 'healthy',
        'dependencies': dependencies,
        'upload_folder': os.path.exists(UPLOAD_FOLDER),
        'python_version': sys.version
    })

@app.errorhandler(413)
def file_too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
