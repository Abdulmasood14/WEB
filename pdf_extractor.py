from flask import Flask, request, jsonify, send_file
import os
import tempfile
import uuid
import re
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
            <h3>🚀 Basic PDF Text Extraction</h3>
            <p>This version extracts text from PDFs and identifies table-like content.</p>
            <p>Upload a PDF to extract structured data as CSV files.</p>
        </div>
        
        <form id="uploadForm">
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
                            <p><strong>Tables Found:</strong> ${data.results.total_tables_extracted}</p>
                            ${data.results.files.map(file => 
                                `<p><a href="/download_file/${data.extraction_id}/${file.name}">📄 Download ${file.name}</a> - ${file.description}</p>`
                            ).join('')}
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
    return jsonify({'status': 'ok', 'message': 'PDF Table Extractor running'})

@app.route('/upload', methods=['POST'])
def upload():
    """Handle file upload with basic text extraction"""
    try:
        print("=== UPLOAD STARTED ===")
        
        # Check request
        if not request.files or 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        
        print(f"File: {file.filename}")
        
        # Validate inputs
        if not file or not file.filename:
            return jsonify({'error': 'No file selected'}), 400
            
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Must be PDF file'}), 400
        
        # Test PyPDF2 import
        try:
            import PyPDF2
            print("✓ PyPDF2 imported successfully")
        except ImportError as e:
            print(f"Import error: {e}")
            return jsonify({'error': 'PyPDF2 not available'}), 500
        
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
        
        # Extract text and find tables
        extraction_result = extract_tables_basic(file_path, temp_dir)
        
        # Store results
        results_store[extraction_id] = extraction_result
        
        return jsonify({
            'success': True,
            'extraction_id': extraction_id,
            'results': {
                'pdf_name': file.filename,
                'total_pages': extraction_result['total_pages'],
                'total_tables_extracted': extraction_result['total_tables_extracted'],
                'files': extraction_result['files']
            }
        })
        
    except Exception as e:
        print(f"General error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

def extract_tables_basic(file_path, temp_dir):
    """Basic PDF text extraction and table detection"""
    
    try:
        import PyPDF2
        
        print("Starting basic PDF extraction...")
        files_created = []
        tables_found = 0
        
        with open(file_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            total_pages = len(pdf_reader.pages)
            print(f"PDF has {total_pages} pages")
            
            all_text = ""
            page_texts = []
            
            # Extract text from each page
            for page_num in range(min(total_pages, 10)):  # Limit to 10 pages
                try:
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    page_texts.append(f"=== PAGE {page_num + 1} ===\n{text}\n\n")
                    all_text += text + "\n"
                    print(f"✓ Extracted text from page {page_num + 1}")
                except Exception as e:
                    print(f"Error extracting page {page_num + 1}: {e}")
                    continue
            
            # Save full text
            text_file = os.path.join(temp_dir, "full_text.txt")
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write("PDF TEXT EXTRACTION\n")
                f.write("=" * 50 + "\n\n")
                for page_text in page_texts:
                    f.write(page_text)
            
            files_created.append({
                'name': 'full_text.txt',
                'path': text_file,
                'description': 'Complete text from PDF'
            })
            
            # Look for table-like patterns
            tables = find_table_patterns(all_text)
            
            for i, table_data in enumerate(tables):
                csv_file = os.path.join(temp_dir, f"table_{i+1}.csv")
                with open(csv_file, 'w', encoding='utf-8') as f:
                    f.write("# Detected Table Data\n")
                    for row in table_data:
                        f.write(','.join(f'"{cell}"' for cell in row) + '\n')
                
                files_created.append({
                    'name': f'table_{i+1}.csv',
                    'path': csv_file,
                    'description': f'Table {i+1} ({len(table_data)} rows)'
                })
                tables_found += 1
            
            # Create summary
            summary_file = os.path.join(temp_dir, "extraction_summary.txt")
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(f"PDF EXTRACTION SUMMARY\n")
                f.write(f"=" * 50 + "\n\n")
                f.write(f"Total Pages: {total_pages}\n")
                f.write(f"Tables Found: {tables_found}\n")
                f.write(f"Text Length: {len(all_text)} characters\n\n")
                f.write(f"Files Generated:\n")
                for file_info in files_created:
                    f.write(f"- {file_info['name']}: {file_info['description']}\n")
            
            files_created.append({
                'name': 'extraction_summary.txt',
                'path': summary_file,
                'description': 'Processing summary'
            })
            
            return {
                'total_pages': total_pages,
                'total_tables_extracted': tables_found,
                'files': files_created,
                'temp_dir': temp_dir
            }
            
    except Exception as e:
        print(f"Extraction error: {e}")
        # Create error report
        error_file = os.path.join(temp_dir, "error_report.txt")
        with open(error_file, 'w') as f:
            f.write(f"PDF EXTRACTION ERROR\n")
            f.write(f"=" * 50 + "\n\n")
            f.write(f"Error: {str(e)}\n")
            f.write(f"The PDF could not be processed successfully.\n")
            f.write(f"This might be due to:\n")
            f.write(f"- Encrypted/password-protected PDF\n")
            f.write(f"- Corrupted file\n")
            f.write(f"- Scanned images without text layer\n")
        
        return {
            'total_pages': 1,
            'total_tables_extracted': 0,
            'files': [{
                'name': 'error_report.txt',
                'path': error_file,
                'description': 'Error details'
            }],
            'temp_dir': temp_dir
        }

def find_table_patterns(text):
    """Find table-like patterns in text"""
    
    tables = []
    lines = text.split('\n')
    
    current_table = []
    in_table = False
    
    for line in lines:
        line = line.strip()
        if not line:
            if in_table and len(current_table) > 2:  # At least 3 rows
                tables.append(current_table)
                current_table = []
            in_table = False
            continue
        
        # Look for table indicators
        # Pattern 1: Multiple numbers or currency
        if (len(re.findall(r'\d+[\.,]?\d*', line)) >= 2 or
            len(re.findall(r'[\$₹£€¥]', line)) >= 1):
            
            # Split by multiple spaces or tabs
            parts = re.split(r'\s{2,}|\t+', line)
            if len(parts) >= 2:  # At least 2 columns
                current_table.append(parts)
                in_table = True
                continue
        
        # Pattern 2: Lines with consistent delimiters
        if '|' in line and line.count('|') >= 2:
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if len(parts) >= 2:
                current_table.append(parts)
                in_table = True
                continue
        
        # Pattern 3: Multiple words that could be column headers
        words = line.split()
        if (len(words) >= 3 and 
            any(keyword in line.lower() for keyword in 
                ['total', 'amount', 'date', 'name', 'description', 'item', 'quantity', 'price'])):
            current_table.append(words)
            in_table = True
            continue
        
        # If we were in a table but this line doesn't match, end the table
        if in_table and len(current_table) > 2:
            tables.append(current_table)
            current_table = []
            in_table = False
    
    # Don't forget the last table
    if in_table and len(current_table) > 2:
        tables.append(current_table)
    
    return tables

@app.route('/download_file/<extraction_id>/<filename>')
def download_file(extraction_id, filename):
    """Download a specific file"""
    try:
        if extraction_id not in results_store:
            return jsonify({'error': 'Results not found'}), 404
        
        results = results_store[extraction_id]
        
        for file_info in results['files']:
            if file_info['name'] == filename:
                file_path = file_info['path']
                if os.path.exists(file_path):
                    return send_file(file_path, as_attachment=True, download_name=filename)
        
        return jsonify({'error': 'File not found'}), 404
        
    except Exception as e:
        return jsonify({'error': f'Download error: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting Ultra Simple PDF Table Extractor on port {port}")
    print(f"📋 Using basic text extraction with PyPDF2")
    app.run(debug=False, host='0.0.0.0', port=port)
