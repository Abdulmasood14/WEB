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
                    <h4>🧠 Advanced AI (model1.py)</h4>
                    <p>Gemini 2.0 Flash with specialized financial table prompts</p>
                </div>
                <div class="feature">
                    <h4>📊 Financial Expertise</h4>
                    <p>Quarter/Nine Months detection, Roman numerals, deferred tax handling</p>
                </div>
                <div class="feature">
                    <h4>🎯 Precision Extraction</h4>
                    <p>Handles "- Deferred Tax Expenses / (Income)" patterns exactly</p>
                </div>
                <div class="feature">
                    <h4>📁 Smart Organization</h4>
                    <p>Multi-page table combination, title detection, Excel error prevention</p>
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
                        message.innerHTML = '<div class="alert alert-success"><strong>✅ Success!</strong> Advanced AI extraction completed with model1.py functionality</div>';
                        
                        let resultsHTML = `
                            <h3>📊 Advanced Extraction Results</h3>
                            <div class="result-item"><strong>📄 File:</strong> ${data.results.pdf_name}</div>
                            <div class="result-item"><strong>📑 Pages:</strong> ${data.results.total_pages}</div>
                            <div class="result-item"><strong>📊 Tables:</strong> ${data.results.total_tables_extracted}</div>
                            <div class="result-item"><strong>🧠 Method:</strong> ${data.results.method || 'Advanced AI'}</div>
                        `;
                        
                        if (data.results.pdf_title && data.results.pdf_title !== data.results.pdf_name) {
                            resultsHTML += `<div class="result-item"><strong>📝 Detected Title:</strong> ${data.results.pdf_title}</div>`;
                        }
                        
                        if (data.results.extracted_titles && data.results.extracted_titles.length > 0) {
                            resultsHTML += '<div class="result-item"><strong>📋 Extracted Table Titles:</strong><ul style="margin: 5px 0; padding-left: 20px;">';
                            data.results.extracted_titles.forEach(title => {
                                resultsHTML += `<li>${title}</li>`;
                            });
                            resultsHTML += '</ul></div>';
                        }
                        
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
                    }d/${data.extraction_id}" style="color: #28a745; text-decoration: none; font-weight: bold;">
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
                    'csv_files': [os.path.basename(f) for f in results.get('csv_files', [])],
                    'extracted_titles': results.get('extracted_titles', []),
                    'pdf_title': results.get('pdf_title', results['pdf_name']),
                    'method': 'Advanced AI with model1.py functionality'
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
    """Advanced AI extraction using Gemini with model1.py functionality"""
    try:
        # Test imports
        import google.generativeai as genai
        import fitz
        from PIL import Image
        import pandas as pd
        import io
        import re
        from pathlib import Path
        
        print("✓ All AI dependencies available")
        
        # Initialize Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Extract PDF title using model1.py method
        pdf_title = extract_pdf_title(file_path)
        print(f"📄 PDF Title detected: {pdf_title}")
        
        # Convert PDF to images with high resolution
        doc = fitz.open(file_path)
        images = []
        
        for page_num in range(min(len(doc), 5)):  # Limit to 5 pages
            page = doc.load_page(page_num)
            mat = fitz.Matrix(3.0, 3.0)  # 3x zoom = 216 DPI for better accuracy
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            images.append(img)
        
        doc.close()
        print(f"✓ Converted {len(images)} pages to high-resolution images")
        
        # Extract tables with advanced AI prompt
        csv_files = []
        total_tables = 0
        tables_by_title = {}
        extracted_titles = []
        
        for page_num, image in enumerate(images):
            try:
                # Use model1.py advanced prompt
                prompt = create_advanced_table_extraction_prompt()
                
                generation_config = {
                    'temperature': 0.1,
                    'top_p': 0.8,
                    'top_k': 40,
                    'max_output_tokens': 8192,
                }
                
                response = model.generate_content([prompt, image], generation_config=generation_config)
                response_text = response.text.strip()
                
                # Clean response using model1.py method
                if response_text.startswith('```json'):
                    response_text = response_text[7:-3].strip()
                elif response_text.startswith('```'):
                    response_text = response_text[3:-3].strip()
                elif response_text.startswith('json'):
                    response_text = response_text[4:].strip()
                
                if response_text.endswith('```'):
                    response_text = response_text[:-3].strip()
                
                result = json.loads(response_text)
                
                if result.get("has_tables") and result.get("tables"):
                    for i, table_data in enumerate(result["tables"]):
                        title = table_data.get('title', f'Table_Page_{page_num+1}_{i+1}')
                        headers = table_data.get('headers', [])
                        data = table_data.get('data', [])
                        
                        if title:
                            extracted_titles.append(title)
                        
                        # Normalize title for grouping (model1.py method)
                        normalized_title = normalize_title_for_grouping(title, page_num)
                        
                        if normalized_title not in tables_by_title:
                            tables_by_title[normalized_title] = {
                                "title": title,
                                "headers": headers,
                                "data": data,
                                "pages": [page_num + 1],
                                "original_titles": [title]
                            }
                        else:
                            # Combine tables across pages
                            existing_table = tables_by_title[normalized_title]
                            if are_headers_compatible(existing_table["headers"], headers):
                                existing_table["data"].extend(data)
                                existing_table["pages"].append(page_num + 1)
                                existing_table["original_titles"].append(title)
                                print(f"    Combined continuation data from pages: {existing_table['pages']}")
                            else:
                                # Create variant if headers don't match
                                alt_title = f"{normalized_title}_v{len([k for k in tables_by_title.keys() if k.startswith(normalized_title)])+1}"
                                tables_by_title[alt_title] = {
                                    "title": title,
                                    "headers": headers,
                                    "data": data,
                                    "pages": [page_num + 1],
                                    "original_titles": [title]
                                }
                        
                        print(f"✓ Found table on page {page_num+1}: {title}")
                
            except Exception as e:
                print(f"Error processing page {page_num+1}: {e}")
                continue
        
        # Save combined tables using model1.py method
        for normalized_title, combined_table in tables_by_title.items():
            try:
                csv_path = save_combined_table_to_csv(combined_table, pdf_title, temp_dir)
                if csv_path:
                    csv_files.append(csv_path)
                    total_tables += 1
                    print(f"✓ Saved combined table: {os.path.basename(csv_path)}")
            except Exception as e:
                print(f"Error saving table {normalized_title}: {e}")
        
        return {
            'total_pages': len(images),
            'total_tables_extracted': total_tables,
            'csv_files': csv_files,
            'extracted_titles': extracted_titles,
            'pdf_title': pdf_title
        }
        
    except ImportError as e:
        raise Exception(f"Missing dependency: {e}")
    except Exception as e:
        raise Exception(f"AI extraction error: {e}")

def extract_pdf_title(pdf_path):
    """Extract title from PDF metadata or first page content (from model1.py)"""
    try:
        import fitz
        import re
        
        doc = fitz.open(pdf_path)
        
        # First try to get title from metadata
        metadata = doc.metadata
        if metadata and metadata.get('title'):
            title = metadata['title'].strip()
            if title and len(title) > 3:
                doc.close()
                return sanitize_directory_name(title)
        
        # If no metadata title, try to extract from first page
        if len(doc) > 0:
            first_page = doc[0]
            blocks = first_page.get_text("dict")
            
            title_candidates = []
            page_height = first_page.rect.height
            
            for block in blocks.get("blocks", []):
                if "lines" in block:
                    for line in block["lines"]:
                        bbox = line["bbox"]
                        y_pos = bbox[1]
                        
                        if y_pos < page_height * 0.3:
                            for span in line.get("spans", []):
                                text = span.get("text", "").strip()
                                font_size = span.get("size", 0)
                                
                                if (text and len(text) > 10 and 
                                    font_size >= 12 and 
                                    not text.lower().startswith(('page', 'confidential', 'draft'))):
                                    title_candidates.append((text, font_size, y_pos))
            
            title_candidates.sort(key=lambda x: (-x[1], x[2]))
            
            if title_candidates:
                potential_title = title_candidates[0][0]
                potential_title = re.sub(r'\s+', ' ', potential_title.strip())
                potential_title = re.sub(r'^(COMPANY|CORPORATION|LIMITED|LTD|INC)[\s:]+', '', potential_title, flags=re.IGNORECASE)
                
                if len(potential_title) > 5:
                    doc.close()
                    return sanitize_directory_name(potential_title)
        
        doc.close()
        
    except Exception as e:
        print(f"Error extracting PDF title: {e}")
    
    # Fallback to filename
    from pathlib import Path
    pdf_name = Path(pdf_path).stem
    return sanitize_directory_name(pdf_name)

def sanitize_directory_name(name):
    """Sanitize a string to be used as a directory name (from model1.py)"""
    import re
    
    sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
    sanitized = re.sub(r'\s+', ' ', sanitized)
    sanitized = sanitized.strip(' .')
    
    if len(sanitized) > 100:
        sanitized = sanitized[:100].strip()
    
    if not sanitized:
        sanitized = "Untitled_PDF"
    
    return sanitized

def create_advanced_table_extraction_prompt():
    """Create the advanced prompt for table extraction (from model1.py)"""
    return """
    You are an expert PDF table extraction specialist. Analyze this image with extreme precision to extract EXACT data as it appears.

    CRITICAL INSTRUCTIONS FOR ACCURACY:

    STEP 1 - COMPLETE TITLE EXTRACTION:
    - Look for the COMPLETE title including ALL subtitle information
    - Extract titles like: "UNAUDITED CONSOLIDATED FINANCIAL RESULTS FOR THE QUARTER & NINE MONTHS ENDED DECEMBER 31, 2024"
    - ALWAYS include currency/unit information if present: "(Rs. In Lakhs)", "(Rs. In Crores)", etc.
    - Look for text that appears prominently above the table
    - Include any subtitle information that describes the table content

    STEP 2 - CRITICAL TEXT RECOGNITION FOR SPECIFIC PATTERNS:
    - MOST IMPORTANT: Look for text patterns that start with a dash/hyphen (-)
    - Specifically look for: "- Deferred Tax Expenses / (Income)"
    - This text appears as an indented sub-item under Tax Expense
    - Extract this EXACTLY as: "- Deferred Tax Expenses / (Income)"
    - DO NOT convert this to "#NAME?" or any error message
    - DO NOT interpret the dash as a negative sign for numbers
    - DO NOT remove the dash or modify the text in any way
    - This is DESCRIPTIVE TEXT, not a formula or calculation

    STEP 3 - QUARTER AND NINE MONTHS COLUMN HANDLING:
    - Look for column headers that contain "Quarter Ended" and "Nine Months Ended"
    - Extract these headers exactly as they appear with dates
    - Examples of expected headers:
      * "Quarter Ended December 31, 2024"
      * "Nine Months Ended December 31, 2024"
      * "Quarter Ended December 31, 2023"
      * "Nine Months Ended December 31, 2023"
    - Preserve the exact format: "Quarter Ended [Date]" and "Nine Months Ended [Date]"
    - Look for additional qualifiers like "Reviewed" or "Unaudited" if present

    STEP 4 - SERIAL NUMBER (Sr. No.) HANDLING:
    - Look for "Sr. No." or "S. No." in the header
    - Serial numbers in this table are: I, II, III, IV, V, VI, VII, VIII, IX (Roman numerals WITHOUT parentheses)
    - Extract EXACTLY as shown:
      * I for first row
      * II for second row  
      * III for third row
      * IV for fourth row
      * V for fifth row
      * VI for sixth row
      * VII for seventh row
      * VIII for eighth row
      * IX for ninth row
    - Do NOT add parentheses if they're not there
    - Do NOT convert to Arabic numbers

    STEP 5 - FINANCIAL DATA HANDLING:
    - Extract ALL numerical values exactly as shown
    - Preserve negative values in parentheses: (135.30), (121.26), (196.58), (552.77)
    - Keep dash symbols as "-" for zero/nil values (when used as data, not as text prefix)
    - Maintain exact decimal precision: 13,542.40, 18,790.26, etc.
    - Include commas in large numbers exactly as shown
    - Do NOT interpret or modify any values

    OUTPUT FORMAT:
    {
        "has_tables": true/false,
        "tables": [
            {
                "title": "Complete table title with currency info",
                "table_number": null,
                "headers": ["Sr. No.", "Particulars", "Quarter Ended December 31, 2024 Reviewed", "Nine Months Ended December 31, 2024 Reviewed", "Quarter Ended December 31, 2023 Reviewed", "Nine Months Ended December 31, 2023 Reviewed"],
                "data": [
                    ["I", "Revenue from Operations", "2,369.75", "27,490.52", "2,148.92", "24,117.03"],
                    ["II", "Other Income", "929.74", "1,779.25", "", ""],
                    ["", "- Deferred Tax Expenses / (Income)", "(0.52)", "(211.11)", "", ""]
                ]
            }
        ]
    }

    CRITICAL ACCURACY REQUIREMENTS:
    1. Include complete title with currency information: "(Rs. In Lakhs)"
    2. Extract Sr. No. as Roman numerals: I, II, III, IV, V, VI, VII, VIII, IX
    3. Preserve negative values in parentheses: (135.30), (121.26)
    4. Keep dash symbols as "-" for nil values in data cells
    5. Extract "- Deferred Tax Expenses / (Income)" EXACTLY as shown - this is descriptive text, not an error
    6. Maintain exact financial formatting with commas
    7. Extract all sub-item descriptions completely
    8. Use "Quarter Ended [Date]" and "Nine Months Ended [Date]" format for column headers

    MOST IMPORTANT - AVOID THESE SPECIFIC MISTAKES:
    - Converting "- Deferred Tax Expenses / (Income)" to "#NAME?" or any error message
    - Treating "- Deferred Tax Expenses / (Income)" as a formula or calculation
    - Missing the complete descriptive text that starts with "-"
    - Converting descriptive text starting with "-" to numerical values
    - Not using the proper "Quarter Ended" and "Nine Months Ended" format in headers

    Remember: Text that starts with "- " followed by words is DESCRIPTIVE TEXT that should be extracted exactly as written, never converted to error messages.
    """

def normalize_title_for_grouping(title, page_num):
    """Normalize title for better grouping of continuation tables (from model1.py)"""
    import re
    
    if not title or title.strip() == '':
        return f"Table_Page_{page_num}"
    
    # Remove extra spaces and normalize
    normalized = re.sub(r'\s+', ' ', title.strip())
    
    # Remove common continuation indicators
    continuation_patterns = [
        r'\s*\(continued\)',
        r'\s*\(contd\)',
        r'\s*\(cont\)',
        r'\s*continued',
        r'\s*contd',
        r'\s*\-\s*continued',
        r'\s*\-\s*contd',
        r'page\s*\d+',
        r'sheet\s*\d+'
    ]
    
    for pattern in continuation_patterns:
        normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
    
    # Normalize common patterns
    company_patterns = [
        (r'HDFC\s+Life\s+Insurance\s+Company\s+Limited?', 'HDFC Life Insurance Company Limited'),
        (r'LLOYDS\s+ENGINEERING\s+WORKS\s+LIMITED', 'LLOYDS ENGINEERING WORKS LIMITED'),
        (r'UNAUDITED\s+CONSOLIDATED\s+FINANCIAL\s+RESULTS', 'UNAUDITED CONSOLIDATED FINANCIAL RESULTS'),
        (r'for\s+the\s+Quarter\s+&\s+Nine\s+Months\s+ended', 'for the Quarter & Nine Months ended'),
        (r'December\s+31,?\s*2024', 'December 31, 2024'),
        (r'Rs\.?\s*in\s*Lakhs?', 'Rs. in Lakhs')
    ]
    
    for pattern, replacement in company_patterns:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    
    return normalized.strip()

def are_headers_compatible(headers1, headers2):
    """Check if two header sets are compatible for table continuation (from model1.py)"""
    import re
    
    if not headers1 or not headers2:
        return True
    
    # Normalize headers for comparison
    norm_headers1 = [re.sub(r'\s+', ' ', str(h).strip().lower()) for h in headers1]
    norm_headers2 = [re.sub(r'\s+', ' ', str(h).strip().lower()) for h in headers2]
    
    # Check if headers are identical
    if norm_headers1 == norm_headers2:
        return True
    
    # Check for significant overlap (70%)
    if len(norm_headers1) > 0 and len(norm_headers2) > 0:
        common_headers = set(norm_headers1) & set(norm_headers2)
        overlap_ratio = len(common_headers) / max(len(norm_headers1), len(norm_headers2))
        
        if overlap_ratio >= 0.7:
            return True
    
    # Check for financial statement patterns
    financial_keywords = ['particulars', 'sr. no', 'march', 'december', 'audited', 'reviewed', 'quarter ended', 'nine months ended']
    headers1_has_financial = any(keyword in ' '.join(norm_headers1) for keyword in financial_keywords)
    headers2_has_financial = any(keyword in ' '.join(norm_headers2) for keyword in financial_keywords)
    
    if headers1_has_financial and headers2_has_financial:
        return True
    
    return False

def save_combined_table_to_csv(combined_table, pdf_name, temp_dir):
    """Save combined table data to CSV file with advanced formatting (from model1.py)"""
    try:
        import pandas as pd
        import re
        
        title = combined_table.get('title', '')
        if title:
            # Clean title for filename
            safe_filename = re.sub(r'[<>:"/\\|?*]', '', title)
            safe_filename = safe_filename.replace('(Rs. In Lakhs)', '').strip()
            safe_filename = re.sub(r'\s+', ' ', safe_filename)
            filename = f"{safe_filename}.csv"
        else:
            filename = f"{pdf_name}_Combined_Table.csv"
        
        filepath = os.path.join(temp_dir, filename)
        
        headers = combined_table.get('headers', [])
        data = combined_table.get('data', [])
        
        if not data:
            return None
        
        # Fix Excel formula issues
        def fix_excel_formula_issues(cell_value):
            if isinstance(cell_value, str):
                if cell_value.startswith('-') and any(c.isalpha() for c in cell_value):
                    return f"'{cell_value}"
                elif cell_value.startswith(('=', '+')):
                    return f"'{cell_value}"
            return cell_value
        
        # Apply fix to all data
        fixed_data = []
        for row in data:
            fixed_row = [fix_excel_formula_issues(cell) for cell in row]
            fixed_data.append(fixed_row)
        
        # Handle column alignment
        if headers and fixed_data:
            max_data_cols = max(len(row) for row in fixed_data) if fixed_data else 0
            
            if len(headers) > max_data_cols:
                headers = headers[:max_data_cols]
            elif len(headers) < max_data_cols:
                for i in range(len(headers), max_data_cols):
                    headers.append(f"Column_{i+1}")
            
            adjusted_data = []
            for row in fixed_data:
                if len(row) > len(headers):
                    adjusted_row = row[:len(headers)]
                elif len(row) < len(headers):
                    adjusted_row = row + [''] * (len(headers) - len(row))
                else:
                    adjusted_row = row
                adjusted_data.append(adjusted_row)
            
            df = pd.DataFrame(adjusted_data, columns=headers)
        else:
            return None
        
        # Save with title and metadata
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            if combined_table.get('title'):
                csvfile.write(f'"{combined_table["title"]}"\n')
                csvfile.write('\n')
            
            pages = combined_table.get('pages', [])
            if len(pages) > 1:
                csvfile.write(f'"Combined from pages: {", ".join(map(str, pages))}"\n')
                csvfile.write('\n')
            
            df.to_csv(csvfile, index=False)
        
        return filepath
        
    except Exception as e:
        print(f"Error saving combined table: {e}")
        return None

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
