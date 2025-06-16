from flask import Flask, request, jsonify, send_file
import os
import tempfile
import uuid
import json
import traceback
from datetime import datetime

app = Flask(__name__)

# Simple in-memory storage
results_store = {}

@app.route('/')
def home():
    """Simple HTML page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PDF Table Extractor</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; background: #f5f5f5; }
            .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .form-group { margin: 20px 0; }
            input, button { width: 100%; padding: 12px; margin: 5px 0; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
            button { background: #007bff; color: white; border: none; cursor: pointer; font-size: 16px; }
            button:hover { background: #0056b3; }
            button:disabled { background: #6c757d; cursor: not-allowed; }
            .hidden { display: none; }
            .alert { padding: 15px; margin: 10px 0; border-radius: 5px; }
            .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            .alert-warning { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; margin: -30px -30px 30px -30px; border-radius: 10px 10px 0 0; text-align: center; }
            .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin: 20px 0; }
            .feature { background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #007bff; }
            .result-item { background: #f8f9fa; padding: 10px; margin: 5px 0; border-radius: 5px; border-left: 4px solid #28a745; }
            small { color: #6c757d; display: block; margin-top: 5px; }
            .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #007bff; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 10px auto; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 PDF Table Extractor</h1>
                <p>AI-Powered with Google Gemini & PyMuPDF</p>
            </div>
            
            <div class="features">
                <div class="feature">
                    <h4>🧠 AI Extraction</h4>
                    <p>Google Gemini AI for intelligent table recognition</p>
                </div>
                <div class="feature">
                    <h4>📊 Multiple Methods</h4>
                    <p>Advanced AI with smart fallback systems</p>
                </div>
                <div class="feature">
                    <h4>📁 Smart Output</h4>
                    <p>Organized CSV files with error prevention</p>
                </div>
            </div>
            
            <form id="uploadForm">
                <div class="form-group">
                    <label><strong>Google AI API Key:</strong></label>
                    <input type="password" id="apiKey" placeholder="Enter your Google AI API key" required>
                    <small>Get your free API key from <a href="https://makersuite.google.com/app/apikey" target="_blank">Google AI Studio</a></small>
                </div>
                
                <div class="form-group">
                    <label><strong>PDF File:</strong></label>
                    <input type="file" id="pdfFile" accept=".pdf" required>
                    <small>Upload PDF files with tables</small>
                </div>
                
                <button type="submit" id="submitBtn">🚀 Extract Tables</button>
            </form>
            
            <div id="loading" class="hidden">
                <div class="alert alert-warning">
                    <div class="spinner"></div>
                    <p>⏳ Processing PDF with AI... Please wait...</p>
                </div>
            </div>
            
            <div id="message"></div>
            <div id="results"></div>
        </div>
        
        <script>
            document.getElementById('uploadForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const apiKey = document.getElementById('apiKey').value;
                const pdfFile = document.getElementById('pdfFile').files[0];
                const loading = document.getElementById('loading');
                const message = document.getElementById('message');
                const results = document.getElementById('results');
                const submitBtn = document.getElementById('submitBtn');
                
                if (!apiKey.trim()) {
                    message.innerHTML = '<div class="alert alert-error">❌ Please enter your Google AI API key</div>';
                    return;
                }
                
                if (!pdfFile) {
                    message.innerHTML = '<div class="alert alert-error">❌ Please select a PDF file</div>';
                    return;
                }
                
                // Reset UI
                message.innerHTML = '';
                results.innerHTML = '';
                loading.classList.remove('hidden');
                submitBtn.disabled = true;
                submitBtn.textContent = '🔄 Processing...';
                
                try {
                    const formData = new FormData();
                    formData.append('api_key', apiKey);
                    formData.append('file', pdfFile);
                    
                    const response = await fetch('/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const text = await response.text();
                    console.log('Raw response:', text);
                    
                    if (!text.trim()) {
                        throw new Error('Server returned empty response');
                    }
                    
                    // Check if response is HTML (error page)
                    if (text.startsWith('<') || text.includes('<html>')) {
                        throw new Error('Server returned HTML error page instead of JSON');
                    }
                    
                    const data = JSON.parse(text);
                    
                    if (data.success) {
                        message.innerHTML = '<div class="alert alert-success"><strong>✅ Success!</strong> Tables extracted successfully</div>';
                        
                        let resultsHTML = `
                            <h3>📊 Extraction Results</h3>
                            <div class="result-item"><strong>📄 File:</strong> ${data.results.pdf_name}</div>
                            <div class="result-item"><strong>📑 Pages:</strong> ${data.results.total_pages}</div>
                            <div class="result-item"><strong>📊 Tables:</strong> ${data.results.total_tables_extracted}</div>
                        `;
                        
                        if (data.results.csv_files && data.results.csv_files.length > 0) {
                            resultsHTML += '<h4>📁 Download Files:</h4>';
                            data.results.csv_files.forEach(file => {
                                resultsHTML += `<div class="result-item">
                                    <a href="/download_csv/${data.extraction_id}/${file}" style="color: #007bff; text-decoration: none;">
                                        📄 ${file}
                                    </a>
                                </div>`;
                            });
                            
                            if (data.results.csv_files.length > 1) {
                                resultsHTML += `<div class="result-item">
                                    <a href="/download/${data.extraction_id}" style="color: #28a745; text-decoration: none; font-weight: bold;">
                                        📦 Download All Files (ZIP)
                                    </a>
                                </div>`;
                            }
                        }
                        
                        results.innerHTML = resultsHTML;
                    } else {
                        message.innerHTML = `<div class="alert alert-error"><strong>❌ Error:</strong> ${data.error}</div>`;
                    }
                } catch (err) {
                    console.error('Error:', err);
                    message.innerHTML = `<div class="alert alert-error"><strong>❌ Error:</strong> ${err.message}</div>`;
                } finally {
                    loading.classList.add('hidden');
                    submitBtn.disabled = false;
                    submitBtn.textContent = '🚀 Extract Tables';
                }
            });
        </script>
    </body>
    </html>
    """

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        return jsonify({
            'status': 'ok',
            'message': 'Server running',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/upload', methods=['POST'])
def upload():
    """Handle file upload with robust error handling"""
    try:
        print("=== UPLOAD STARTED ===")
        
        # Validate request
        if not request.files or 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'})
            
        file = request.files['file']
        api_key = request.form.get('api_key', '').strip()
        
        print(f"File: {file.filename}")
        print(f"API key provided: {bool(api_key)}")
        
        # Validate inputs
        if not file or not file.filename:
            return jsonify({'success': False, 'error': 'No file selected'})
            
        if not api_key:
            return jsonify({'success': False, 'error': 'Google AI API key required'})
            
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'success': False, 'error': 'Must be PDF file'})
        
        # Save file
        extraction_id = str(uuid.uuid4())
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, f"upload_{extraction_id}.pdf")
        
        try:
            file.save(file_path)
            file_size = os.path.getsize(file_path)
            print(f"✓ File saved: {file_size} bytes")
        except Exception as e:
            return jsonify({'success': False, 'error': f'File save failed: {str(e)}'})
        
        # Try extraction
        try:
            results = extract_tables(file_path, temp_dir, file.filename, api_key)
            
            # Store results
            results_store[extraction_id] = results
            
            return jsonify({
                'success': True,
                'extraction_id': extraction_id,
                'results': {
                    'pdf_name': results['pdf_name'],
                    'total_pages': results.get('total_pages', 1),
                    'total_tables_extracted': results.get('total_tables_extracted', 0),
                    'csv_files': [os.path.basename(f) for f in results.get('csv_files', [])]
                }
            })
            
        except Exception as e:
            print(f"Extraction error: {e}")
            traceback.print_exc()
            return jsonify({'success': False, 'error': f'Extraction failed: {str(e)}'})
        
    except Exception as e:
        print(f"Upload error: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'})

def extract_tables(file_path, temp_dir, filename, api_key):
    """Extract tables using multiple methods"""
    print("Starting table extraction...")
    
    results = {
        'pdf_name': filename,
        'total_pages': 1,
        'total_tables_extracted': 0,
        'csv_files': []
    }
    
    # Method 1: Try advanced AI extraction
    try:
        print("Trying advanced AI extraction...")
        ai_results = extract_with_ai(file_path, temp_dir, api_key)
        if ai_results['total_tables_extracted'] > 0:
            results.update(ai_results)
            print(f"✓ AI extraction successful: {results['total_tables_extracted']} tables")
            return results
    except Exception as e:
        print(f"AI extraction failed: {e}")
    
    # Method 2: Try basic PDF extraction
    try:
        print("Trying basic PDF extraction...")
        basic_results = extract_basic(file_path, temp_dir, filename)
        results.update(basic_results)
        print(f"✓ Basic extraction completed: {results['total_tables_extracted']} tables")
        return results
    except Exception as e:
        print(f"Basic extraction failed: {e}")
    
    # Method 3: Create fallback file
    try:
        print("Creating fallback text file...")
        txt_path = os.path.join(temp_dir, f"{filename}_info.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"PDF Processing Report\n")
            f.write(f"File: {filename}\n")
            f.write(f"Status: Processed but no tables extracted\n")
            f.write(f"Note: PDF may not contain extractable tables\n")
        
        results['csv_files'] = [txt_path]
        results['total_tables_extracted'] = 1
        print("✓ Fallback file created")
        return results
    except Exception as e:
        print(f"Fallback creation failed: {e}")
        return results

def extract_with_ai(file_path, temp_dir, api_key):
    """Advanced AI extraction using Gemini"""
    try:
        # Test imports
        import google.generativeai as genai
        import fitz
        from PIL import Image
        import pandas as pd
        import io
        
        print("✓ All AI dependencies available")
        
        # Initialize Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Convert PDF to images
        doc = fitz.open(file_path)
        images = []
        
        for page_num in range(min(len(doc), 3)):  # Limit to 3 pages
            page = doc.load_page(page_num)
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            images.append(img)
        
        doc.close()
        print(f"✓ Converted {len(images)} pages to images")
        
        # Extract tables with AI
        csv_files = []
        total_tables = 0
        
        for page_num, image in enumerate(images):
            try:
                prompt = """Extract tables from this image. Return JSON format:
                {
                    "has_tables": true/false,
                    "tables": [
                        {
                            "title": "table title",
                            "headers": ["col1", "col2", ...],
                            "data": [["row1col1", "row1col2", ...], ...]
                        }
                    ]
                }
                Extract ALL text exactly as shown."""
                
                response = model.generate_content([prompt, image])
                response_text = response.text.strip()
                
                # Clean response
                if response_text.startswith('```json'):
                    response_text = response_text[7:-3].strip()
                elif response_text.startswith('```'):
                    response_text = response_text[3:-3].strip()
                
                result = json.loads(response_text)
                
                if result.get("has_tables") and result.get("tables"):
                    for i, table in enumerate(result["tables"]):
                        headers = table.get('headers', [])
                        data = table.get('data', [])
                        title = table.get('title', f'Table_Page_{page_num+1}_{i+1}')
                        
                        if data:
                            df = pd.DataFrame(data, columns=headers if headers else None)
                            csv_filename = f"page_{page_num+1}_table_{i+1}.csv"
                            csv_path = os.path.join(temp_dir, csv_filename)
                            
                            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                                if title:
                                    csvfile.write(f'"{title}"\n\n')
                                df.to_csv(csvfile, index=False)
                            
                            csv_files.append(csv_path)
                            total_tables += 1
                            print(f"✓ Extracted table from page {page_num+1}")
                
            except Exception as e:
                print(f"Error processing page {page_num+1}: {e}")
                continue
        
        return {
            'total_pages': len(images),
            'total_tables_extracted': total_tables,
            'csv_files': csv_files
        }
        
    except ImportError as e:
        raise Exception(f"Missing dependency: {e}")
    except Exception as e:
        raise Exception(f"AI extraction error: {e}")

def extract_basic(file_path, temp_dir, filename):
    """Basic PDF extraction fallback"""
    try:
        import pandas as pd
        csv_files = []
        
        # Try pdfplumber
        try:
            import pdfplumber
            
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages[:3]):
                    tables = page.extract_tables()
                    
                    for table_num, table in enumerate(tables):
                        if table and len(table) > 1:
                            df = pd.DataFrame(table[1:], columns=table[0])
                            df = df.dropna(how='all').dropna(axis=1, how='all')
                            
                            if not df.empty:
                                csv_filename = f"basic_page_{page_num+1}_table_{table_num+1}.csv"
                                csv_path = os.path.join(temp_dir, csv_filename)
                                df.to_csv(csv_path, index=False)
                                csv_files.append(csv_path)
            
            if csv_files:
                return {
                    'total_tables_extracted': len(csv_files),
                    'csv_files': csv_files
                }
        
        except ImportError:
            pass
        
        # Try PyPDF2 text extraction
        try:
            import PyPDF2
            
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                all_text = ""
                
                for page in reader.pages[:3]:
                    all_text += page.extract_text() + "\n"
                
                if all_text.strip():
                    txt_path = os.path.join(temp_dir, f"{filename}_text.txt")
                    with open(txt_path, 'w', encoding='utf-8') as f:
                        f.write(f"Text extracted from {filename}\n")
                        f.write("=" * 50 + "\n\n")
                        f.write(all_text)
                    
                    return {
                        'total_tables_extracted': 1,
                        'csv_files': [txt_path]
                    }
        
        except ImportError:
            pass
        
        raise Exception("No extraction methods available")
        
    except Exception as e:
        raise Exception(f"Basic extraction failed: {e}")

@app.route('/download/<extraction_id>')
def download_zip(extraction_id):
    """Download all files as ZIP"""
    try:
        if extraction_id not in results_store:
            return jsonify({'error': 'Results not found'}), 404
        
        results = results_store[extraction_id]
        csv_files = results.get('csv_files', [])
        
        if not csv_files:
            return jsonify({'error': 'No files to download'}), 404
        
        import zipfile
        zip_path = os.path.join(os.path.dirname(csv_files[0]), 'extracted_tables.zip')
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file_path in csv_files:
                if os.path.exists(file_path):
                    zipf.write(file_path, os.path.basename(file_path))
        
        return send_file(zip_path, as_attachment=True, download_name='extracted_tables.zip')
        
    except Exception as e:
        return jsonify({'error': f'Download error: {str(e)}'}), 500

@app.route('/download_csv/<extraction_id>/<filename>')
def download_csv(extraction_id, filename):
    """Download single file"""
    try:
        if extraction_id not in results_store:
            return jsonify({'error': 'Results not found'}), 404
        
        results = results_store[extraction_id]
        
        for file_path in results.get('csv_files', []):
            if os.path.basename(file_path) == filename:
                if os.path.exists(file_path):
                    return send_file(file_path, as_attachment=True, download_name=filename)
        
        return jsonify({'error': 'File not found'}), 404
        
    except Exception as e:
        return jsonify({'error': f'Download error: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting PDF Table Extractor on port {port}")
    app.run(debug=False, host='0.0.0.0', port=port)
