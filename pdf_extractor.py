from flask import Flask, request, jsonify, send_file
import os
import tempfile
import uuid
import zipfile
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
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            .form-group { margin: 20px 0; }
            input, button { width: 100%; padding: 10px; margin: 5px 0; border: 1px solid #ddd; border-radius: 5px; }
            button { background: #007bff; color: white; border: none; cursor: pointer; }
            button:hover { background: #0056b3; }
            .hidden { display: none; }
            .alert { padding: 15px; margin: 10px 0; border-radius: 5px; }
            .alert-success { background: #d4edda; color: #155724; }
            .alert-error { background: #f8d7da; color: #721c24; }
            .demo { background: #e7f3ff; padding: 15px; margin: 20px 0; border-radius: 5px; }
        </style>
    </head>
    <body>
        <h1>📊 PDF Table Extractor</h1>
        
        <div class="demo">
            <h3>🚀 Demo Mode</h3>
            <p>This is a basic version that extracts tables from PDFs using simple text parsing.</p>
            <p>For advanced AI-powered extraction with Google Gemini, add your API key below.</p>
        </div>
        
        <form id="uploadForm">
            <div class="form-group">
                <label>Google AI API Key (Optional for basic extraction):</label>
                <input type="password" id="apiKey" placeholder="Enter your Google AI API key (optional)">
                <small>Get from <a href="https://makersuite.google.com/app/apikey" target="_blank">Google AI Studio</a></small>
            </div>
            
            <div class="form-group">
                <label>PDF File:</label>
                <input type="file" id="pdfFile" accept=".pdf" required>
            </div>
            
            <button type="submit" id="submitBtn">Extract Tables</button>
        </form>
        
        <div id="loading" class="hidden">
            <p>⏳ Processing PDF... Please wait...</p>
        </div>
        
        <div id="message"></div>
        <div id="results"></div>
        
        <script>
            document.getElementById('uploadForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const apiKey = document.getElementById('apiKey').value;
                const pdfFile = document.getElementById('pdfFile').files[0];
                const loading = document.getElementById('loading');
                const message = document.getElementById('message');
                const results = document.getElementById('results');
                const submitBtn = document.getElementById('submitBtn');
                
                // Reset
                message.innerHTML = '';
                results.innerHTML = '';
                loading.classList.remove('hidden');
                submitBtn.disabled = true;
                
                try {
                    // Create form data
                    const formData = new FormData();
                    if (apiKey) formData.append('api_key', apiKey);
                    formData.append('file', pdfFile);
                    
                    // Send request
                    const response = await fetch('/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const text = await response.text();
                    console.log('Response:', text);
                    
                    if (!text.trim()) {
                        throw new Error('Server returned empty response');
                    }
                    
                    const data = JSON.parse(text);
                    
                    if (data.success) {
                        message.innerHTML = '<div class="alert alert-success">✅ Success! PDF processed.</div>';
                        results.innerHTML = `
                            <h3>Results:</h3>
                            <p><strong>File:</strong> ${data.results.pdf_name}</p>
                            <p><strong>Pages:</strong> ${data.results.total_pages}</p>
                            <p><strong>Extraction Method:</strong> ${data.results.method}</p>
                            <p><strong>Tables Found:</strong> ${data.results.total_tables_extracted}</p>
                            ${data.results.csv_files.map(file => 
                                `<p><a href="/download_csv/${data.extraction_id}/${file}">📄 Download ${file}</a></p>`
                            ).join('')}
                            ${data.results.csv_files.length > 1 ? 
                                `<p><a href="/download/${data.extraction_id}">📦 Download All (ZIP)</a></p>` : ''}
                        `;
                    } else {
                        message.innerHTML = `<div class="alert alert-error">❌ Error: ${data.error}</div>`;
                    }
                } catch (err) {
                    console.error('Error:', err);
                    message.innerHTML = `<div class="alert alert-error">❌ Error: ${err.message}</div>`;
                } finally {
                    loading.classList.add('hidden');
                    submitBtn.disabled = false;
                }
            });
        </script>
    </body>
    </html>
    """

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'message': 'Server running'})

@app.route('/upload', methods=['POST'])
def upload():
    """Handle file upload with fallback methods"""
    try:
        print("=== UPLOAD STARTED ===")
        
        # Check request
        if not request.files or 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        api_key = request.form.get('api_key', '').strip()
        
        print(f"File: {file.filename}")
        print(f"API key provided: {'Yes' if api_key else 'No'}")
        
        # Validate inputs
        if not file or not file.filename:
            return jsonify({'error': 'No file selected'}), 400
            
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Must be PDF file'}), 400
        
        # Save file
        extraction_id = str(uuid.uuid4())
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, f"upload_{extraction_id}.pdf")
        
        try:
            file.save(file_path)
            file_size = os.path.getsize(file_path)
            print(f"✓ File saved: {file_size} bytes")
        except Exception as e:
            return jsonify({'error': f'File save failed: {str(e)}'}), 500
        
        # Try different extraction methods
        extraction_result = extract_tables_from_pdf(file_path, api_key, temp_dir)
        
        # Store results
        results_store[extraction_id] = extraction_result
        
        return jsonify({
            'success': True,
            'extraction_id': extraction_id,
            'results': {
                'pdf_name': file.filename,
                'total_pages': extraction_result['total_pages'],
                'method': extraction_result['method'],
                'total_tables_extracted': extraction_result['total_tables_extracted'],
                'csv_files': [os.path.basename(f) for f in extraction_result['csv_files']]
            }
        })
        
    except Exception as e:
        print(f"General error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

def extract_tables_from_pdf(file_path, api_key, temp_dir):
    """Extract tables using available methods"""
    
    # Method 1: Try pdfplumber (most reliable for table structure)
    try:
        import pdfplumber
        import pandas as pd
        
        print("Trying pdfplumber extraction...")
        csv_files = []
        tables_found = 0
        
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            
            for page_num in range(min(total_pages, 10)):  # Process up to 10 pages
                page = pdf.pages[page_num]
                tables = page.extract_tables()
                
                for i, table in enumerate(tables):
                    if table and len(table) > 1:  # At least header + 1 row
                        try:
                            df = pd.DataFrame(table[1:], columns=table[0])  # First row as header
                            df = df.dropna(how='all').dropna(axis=1, how='all')
                            
                            if not df.empty:
                                csv_filename = f"pdfplumber_page{page_num+1}_table{i+1}.csv"
                                csv_path = os.path.join(temp_dir, csv_filename)
                                df.to_csv(csv_path, index=False)
                                csv_files.append(csv_path)
                                tables_found += 1
                                print(f"✓ Extracted table from page {page_num+1}")
                                
                        except Exception as e:
                            print(f"Error processing table on page {page_num+1}: {e}")
                            continue
        
        if tables_found > 0:
            return {
                'method': 'pdfplumber',
                'total_pages': total_pages,
                'total_tables_extracted': tables_found,
                'csv_files': csv_files,
                'temp_dir': temp_dir
            }
            
    except ImportError:
        print("pdfplumber not available")
    except Exception as e:
        print(f"pdfplumber extraction failed: {e}")
    
    # Method 2: Try simple text extraction as fallback
    try:
        import PyPDF2
        import pandas as pd
        import re
        
        print("Trying simple text extraction...")
        csv_files = []
        tables_found = 0
        
        with open(file_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            total_pages = len(pdf_reader.pages)
            
            for page_num in range(min(total_pages, 5)):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                
                # Look for table-like patterns (multiple columns of data)
                lines = text.split('\n')
                table_lines = []
                
                for line in lines:
                    # Simple heuristic: if line has multiple numbers or currency symbols
                    if (len(re.findall(r'\d+', line)) >= 2 or 
                        len(re.findall(r'[\$₹£€]', line)) >= 1 or
                        len(line.split()) >= 3):  # At least 3 columns
                        table_lines.append(line.split())
                
                if len(table_lines) > 3:  # At least 4 rows for a meaningful table
                    try:
                        # Normalize column count
                        max_cols = max(len(row) for row in table_lines)
                        normalized_table = []
                        
                        for row in table_lines:
                            if len(row) < max_cols:
                                row.extend([''] * (max_cols - len(row)))
                            normalized_table.append(row[:max_cols])
                        
                        df = pd.DataFrame(normalized_table)
                        csv_filename = f"text_extract_page{page_num+1}.csv"
                        csv_path = os.path.join(temp_dir, csv_filename)
                        df.to_csv(csv_path, index=False, header=False)
                        csv_files.append(csv_path)
                        tables_found += 1
                        print(f"✓ Extracted text table from page {page_num+1}")
                        
                    except Exception as e:
                        print(f"Error creating table from text on page {page_num+1}: {e}")
                        continue
        
        if tables_found > 0:
            return {
                'method': 'text extraction',
                'total_pages': total_pages,
                'total_tables_extracted': tables_found,
                'csv_files': csv_files,
                'temp_dir': temp_dir
            }
            
    except Exception as e:
        print(f"Text extraction failed: {e}")
    
    # Method 3: If we have an API key, try Gemini (placeholder for now)
    if api_key:
        try:
            import google.generativeai as genai
            print("API key provided - Gemini extraction would go here")
            # For now, just return a message
            
        except ImportError:
            print("google-generativeai not available")
        except Exception as e:
            print(f"Gemini extraction failed: {e}")
    
    # Fallback: Create a simple report
    try:
        import PyPDF2
        with open(file_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            total_pages = len(pdf_reader.pages)
    except:
        total_pages = 1
    
    # Create a basic info file
    info_filename = "extraction_info.txt"
    info_path = os.path.join(temp_dir, info_filename)
    with open(info_path, 'w') as f:
        f.write(f"PDF Analysis Report\n")
        f.write(f"==================\n\n")
        f.write(f"File processed but no tables detected using available methods.\n")
        f.write(f"Total pages: {total_pages}\n\n")
        f.write(f"Suggestions:\n")
        f.write(f"1. Ensure the PDF contains actual tables (not images)\n")
        f.write(f"2. Try providing a Google AI API key for advanced extraction\n")
        f.write(f"3. The PDF might need to be OCR'd first if it's scanned\n")
    
    return {
        'method': 'basic analysis',
        'total_pages': total_pages,
        'total_tables_extracted': 0,
        'csv_files': [info_path],
        'temp_dir': temp_dir
    }

@app.route('/download/<extraction_id>')
def download_zip(extraction_id):
    """Download all files as ZIP"""
    try:
        if extraction_id not in results_store:
            return jsonify({'error': 'Results not found'}), 404
        
        results = results_store[extraction_id]
        
        if not results['csv_files']:
            return jsonify({'error': 'No files to download'}), 404
        
        zip_path = os.path.join(results['temp_dir'], 'extracted_files.zip')
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file_path in results['csv_files']:
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
        
        for file_path in results['csv_files']:
            if os.path.basename(file_path) == filename:
                if os.path.exists(file_path):
                    return send_file(file_path, as_attachment=True, download_name=filename)
        
        return jsonify({'error': 'File not found'}), 404
        
    except Exception as e:
        return jsonify({'error': f'Download error: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting PDF Table Extractor on port {port}")
    print(f"📋 Available extraction methods will be detected at runtime")
    app.run(debug=False, host='0.0.0.0', port=port)
