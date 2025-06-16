from flask import Flask, request, jsonify, send_file
import os
import tempfile
import uuid
import json
import traceback
from datetime import datetime
import zipfile

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
            print("No file in request")
            return jsonify({'success': False, 'error': 'No file provided'})
            
        file = request.files['file']
        api_key = request.form.get('api_key', '').strip()
        
        print(f"File: {file.filename}")
        print(f"API key provided: {bool(api_key)}")
        
        # Validate inputs
        if not file or not file.filename:
            print("No file selected")
            return jsonify({'success': False, 'error': 'No file selected'})
            
        if not api_key:
            print("No API key provided")
            return jsonify({'success': False, 'error': 'Google AI API key required'})
            
        if not file.filename.lower().endswith('.pdf'):
            print("Invalid file type")
            return jsonify({'success': False, 'error': 'Must be PDF file'})
        
        # Save file safely
        extraction_id = str(uuid.uuid4())
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, f"upload_{extraction_id}.pdf")
        
        try:
            file.save(file_path)
            file_size = os.path.getsize(file_path)
            print(f"✓ File saved: {file_size} bytes")
        except Exception as e:
            print(f"File save error: {e}")
            return jsonify({'success': False, 'error': f'File save failed: {str(e)}'})
        
        # Try extraction with multiple fallbacks
        try:
            print("🚀 Starting extraction process...")
            results = extract_tables_safe(file_path, temp_dir, file.filename, api_key)
            
            # Store results
            results_store[extraction_id] = results
            
            print(f"🎉 Extraction completed successfully!")
            print(f"📊 Tables extracted: {results.get('total_tables_extracted', 0)}")
            print(f"📁 Files created: {len(results.get('csv_files', []))}")
            
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
                    'method': results.get('method', 'Basic extraction')
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

def extract_tables_safe(file_path, temp_dir, filename, api_key):
    """Safe extraction with multiple fallback methods and comprehensive logging"""
    print("🔍 Starting comprehensive table extraction...")
    print(f"📄 File: {filename}")
    print(f"📂 Temp directory: {temp_dir}")
    print(f"🔑 API key provided: {bool(api_key and len(api_key.strip()) > 10)}")
    
    results = {
        'pdf_name': filename,
        'total_pages': 1,
        'total_tables_extracted': 0,
        'csv_files': [],
        'extracted_titles': [],
        'pdf_title': filename,
        'method': 'Unknown'
    }
    
    # Method 1: Advanced AI Extraction
    print("\n🤖 === ATTEMPTING ADVANCED AI EXTRACTION ===")
    try:
        print("Checking AI dependencies...")
        import google.generativeai as genai
        import fitz  # PyMuPDF
        from PIL import Image
        import pandas as pd
        
        print("✅ All AI dependencies available!")
        print("🚀 Starting AI extraction...")
        
        ai_results = extract_with_ai_safe(file_path, temp_dir, api_key)
        if ai_results and ai_results.get('total_tables_extracted', 0) > 0:
            results.update(ai_results)
            results['method'] = 'Advanced AI (Gemini 2.0 Flash)'
            print(f"🎉 AI EXTRACTION SUCCESSFUL!")
            print(f"📊 Extracted {results['total_tables_extracted']} tables")
            print(f"📁 Created {len(results['csv_files'])} files")
            return results
        else:
            print("⚠️ AI extraction returned no tables")
    except ImportError as e:
        print(f"❌ AI dependencies missing: {e}")
        print("📝 Note: Install google-generativeai, PyMuPDF, and Pillow for AI extraction")
    except Exception as e:
        print(f"❌ AI extraction failed: {e}")
        print("🔄 Falling back to basic methods...")
    
    # Method 2: Basic PDF Extraction
    print("\n📋 === ATTEMPTING BASIC PDF EXTRACTION ===")
    try:
        print("🔍 Trying pdfplumber, PyMuPDF, and PyPDF2...")
        basic_results = extract_basic_safe(file_path, temp_dir, filename)
        if basic_results and basic_results.get('total_tables_extracted', 0) > 0:
            results.update(basic_results)
            results['method'] = 'Basic PDF extraction'
            print(f"🎉 BASIC EXTRACTION SUCCESSFUL!")
            print(f"📊 Extracted {results['total_tables_extracted']} tables/content")
            print(f"📁 Created {len(results['csv_files'])} files")
            return results
        else:
            print("⚠️ Basic extraction found no tables")
    except Exception as e:
        print(f"❌ Basic extraction failed: {e}")
        print("🔄 Creating fallback report...")
    
    # Method 3: Comprehensive Fallback
    print("\n📋 === CREATING COMPREHENSIVE ANALYSIS ===")
    try:
        print("📝 Generating detailed extraction report...")
        fallback_results = create_fallback_result(file_path, temp_dir, filename)
        if fallback_results:
            results.update(fallback_results)
            results['method'] = 'Comprehensive analysis report'
            print(f"✅ FALLBACK REPORT CREATED!")
            print(f"📄 Generated analysis report")
            return results
    except Exception as e:
        print(f"❌ Fallback creation failed: {e}")
    
    # Final fallback
    print("\n⚠️ === ALL METHODS FAILED ===")
    print("❌ Could not extract any tables or create reports")
    print("💡 Suggestions:")
    print("   • Check if PDF contains searchable text")
    print("   • Verify API key is correct")
    print("   • Try a different PDF file")
    
    return results

def extract_with_ai_safe(file_path, temp_dir, api_key):
    """Safe AI extraction with comprehensive error handling"""
    try:
        # Import required modules safely
        import google.generativeai as genai
        import fitz
        from PIL import Image
        import pandas as pd
        import io
        import re
        import base64
        
        print("✓ All AI dependencies imported successfully")
        
        # Test API key first
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            
            # Quick test to validate API key
            test_response = model.generate_content("Hello")
            print("✓ Gemini API key validated successfully")
        except Exception as e:
            print(f"API key validation failed: {e}")
            return None
        
        # Convert PDF to images safely
        try:
            doc = fitz.open(file_path)
            images = []
            
            max_pages = min(len(doc), 5)  # Process up to 5 pages
            print(f"Processing {max_pages} pages from PDF...")
            
            for page_num in range(max_pages):
                try:
                    page = doc.load_page(page_num)
                    # Use reasonable resolution for better AI recognition
                    mat = fitz.Matrix(2.5, 2.5)  # 2.5x zoom for good quality
                    pix = page.get_pixmap(matrix=mat, alpha=False)
                    img_data = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_data))
                    
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    images.append(img)
                    print(f"✓ Converted page {page_num + 1} to image")
                except Exception as e:
                    print(f"Error converting page {page_num + 1}: {e}")
                    continue
            
            doc.close()
            
            if not images:
                print("❌ No images converted successfully")
                return None
                
            print(f"✓ Successfully converted {len(images)} pages")
            
        except Exception as e:
            print(f"PDF to image conversion failed: {e}")
            return None
        
        # Extract tables with AI
        csv_files = []
        total_tables = 0
        extracted_titles = []
        pdf_title = extract_pdf_title_safe(file_path)
        
        for page_num, image in enumerate(images):
            try:
                print(f"🤖 Processing page {page_num + 1} with Gemini AI...")
                
                # Use comprehensive prompt for table extraction
                prompt = """You are an expert PDF table extraction specialist. Analyze this image and extract ALL tables with extreme precision.

INSTRUCTIONS:
1. Look for ANY tabular data structure (rows and columns)
2. Extract complete table titles including currency information like "(Rs. In Lakhs)"
3. Preserve ALL text exactly as shown:
   - Text starting with "-" like "- Deferred Tax Expenses / (Income)"
   - Roman numerals: I, II, III, IV, V, VI, VII, VIII, IX
   - Negative values in parentheses: (123.45)
   - Quarter/Nine Months format in headers
4. Extract every cell exactly as it appears

Return JSON format:
{
    "has_tables": true/false,
    "tables": [
        {
            "title": "Complete table title with all text",
            "headers": ["Column 1", "Column 2", "Column 3", "..."],
            "data": [
                ["Row 1 Col 1", "Row 1 Col 2", "Row 1 Col 3", "..."],
                ["Row 2 Col 1", "Row 2 Col 2", "Row 2 Col 3", "..."]
            ]
        }
    ]
}

CRITICAL: Extract EVERY table you see, even if small. Include ALL text exactly as written."""
                
                generation_config = {
                    'temperature': 0.05,  # Very low for consistency
                    'top_p': 0.9,
                    'max_output_tokens': 8192,
                }
                
                try:
                    response = model.generate_content([prompt, image], generation_config=generation_config)
                    response_text = response.text.strip()
                    print(f"✓ Got AI response for page {page_num + 1}")
                except Exception as e:
                    print(f"AI generation failed for page {page_num + 1}: {e}")
                    continue
                
                # Clean and parse response
                try:
                    # Clean JSON response
                    if response_text.startswith('```json'):
                        response_text = response_text[7:].rstrip('```').strip()
                    elif response_text.startswith('```'):
                        response_text = response_text[3:].rstrip('```').strip()
                    
                    # Additional cleaning
                    response_text = response_text.replace('```json', '').replace('```', '').strip()
                    
                    # Parse JSON
                    result = json.loads(response_text)
                    print(f"✓ Successfully parsed JSON for page {page_num + 1}")
                    
                except json.JSONDecodeError as e:
                    print(f"JSON parse error on page {page_num + 1}: {e}")
                    print(f"Raw response: {response_text[:200]}...")
                    continue
                except Exception as e:
                    print(f"Response processing error on page {page_num + 1}: {e}")
                    continue
                
                # Process tables
                if result.get("has_tables") and result.get("tables"):
                    page_tables = result.get("tables", [])
                    print(f"📊 Found {len(page_tables)} table(s) on page {page_num + 1}")
                    
                    for table_idx, table_data in enumerate(page_tables):
                        try:
                            title = table_data.get('title', f'Table_Page_{page_num+1}_{table_idx+1}')
                            headers = table_data.get('headers', [])
                            data = table_data.get('data', [])
                            
                            print(f"  📋 Table: {title[:50]}...")
                            print(f"  📊 Dimensions: {len(data)} rows x {len(headers)} columns")
                            
                            if title and title not in extracted_titles:
                                extracted_titles.append(title)
                            
                            if data and len(data) > 0:
                                # Save table with comprehensive error handling
                                csv_path = save_table_comprehensive(title, headers, data, page_num + 1, table_idx + 1, temp_dir, pdf_title)
                                if csv_path:
                                    csv_files.append(csv_path)
                                    total_tables += 1
                                    print(f"  ✅ Saved: {os.path.basename(csv_path)}")
                                else:
                                    print(f"  ❌ Failed to save table")
                            else:
                                print(f"  ⚠️ Table has no data")
                                
                        except Exception as e:
                            print(f"Error processing table {table_idx+1} on page {page_num+1}: {e}")
                            continue
                else:
                    print(f"❌ No tables detected on page {page_num + 1}")
                
            except Exception as e:
                print(f"Error processing page {page_num + 1}: {e}")
                continue
        
        if total_tables > 0:
            print(f"🎉 Successfully extracted {total_tables} tables total")
            return {
                'total_pages': len(images),
                'total_tables_extracted': total_tables,
                'csv_files': csv_files,
                'extracted_titles': extracted_titles,
                'pdf_title': pdf_title
            }
        else:
            print("❌ No tables extracted with AI")
            return None
        
    except ImportError as e:
        print(f"Import error in AI extraction: {e}")
        return None
    except Exception as e:
        print(f"AI extraction error: {e}")
        import traceback
        traceback.print_exc()
        return None

def save_table_comprehensive(title, headers, data, page_num, table_num, temp_dir, pdf_title):
    """Comprehensive table saving with all model1.py features"""
    try:
        import pandas as pd
        import re
        
        print(f"    💾 Saving table: {title[:30]}...")
        
        # Create safe filename
        if title and title.strip() and title != f'Table_Page_{page_num}_{table_num}':
            # Use actual title for filename
            safe_title = sanitize_filename(title)
            # Remove currency info for cleaner filename
            safe_title = re.sub(r'\(Rs\.?\s*[Ii]n\s*[Ll]akhs?\)', '', safe_title).strip()
            safe_title = re.sub(r'\(Rs\.?\s*[Ii]n\s*[Cc]rores?\)', '', safe_title).strip()
            filename = f"{safe_title}.csv"
        else:
            filename = f"page_{page_num}_table_{table_num}.csv"
        
        filepath = os.path.join(temp_dir, filename)
        
        # Validate data
        if not data or len(data) == 0:
            print(f"    ❌ No data to save")
            return None
        
        print(f"    📊 Processing {len(data)} rows of data...")
        
        # Fix Excel formula issues (model1.py method)
        def fix_excel_formula_issues(cell_value):
            if isinstance(cell_value, str):
                # Prevent Excel from interpreting as formulas
                if cell_value.startswith('-') and any(c.isalpha() for c in cell_value):
                    return f"'{cell_value}"  # Add quote for descriptive text like "- Deferred Tax"
                elif cell_value.startswith(('=', '+')):
                    return f"'{cell_value}"
            return cell_value
        
        # Apply fixes to all data
        fixed_data = []
        for row_idx, row in enumerate(data):
            if isinstance(row, list):
                fixed_row = [fix_excel_formula_issues(cell) for cell in row]
                fixed_data.append(fixed_row)
            else:
                print(f"    ⚠️ Row {row_idx} is not a list: {type(row)}")
                continue
        
        if not fixed_data:
            print(f"    ❌ No valid data after processing")
            return None
        
        # Handle headers and data alignment
        try:
            if headers and len(headers) > 0:
                print(f"    📋 Using {len(headers)} headers")
                
                # Find max columns in data
                max_data_cols = max(len(row) for row in fixed_data) if fixed_data else 0
                
                # Adjust headers to match data
                if len(headers) > max_data_cols:
                    headers = headers[:max_data_cols]
                    print(f"    ⚠️ Truncated headers to {len(headers)} columns")
                elif len(headers) < max_data_cols:
                    for i in range(len(headers), max_data_cols):
                        headers.append(f"Column_{i+1}")
                    print(f"    ⚠️ Extended headers to {len(headers)} columns")
                
                # Ensure all rows have same number of columns as headers
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
                print(f"    📋 No headers, using generic column names")
                # No headers - create generic ones
                max_cols = max(len(row) for row in fixed_data) if fixed_data else 0
                
                # Ensure all rows have same number of columns
                adjusted_data = []
                for row in fixed_data:
                    if len(row) < max_cols:
                        adjusted_row = row + [''] * (max_cols - len(row))
                    else:
                        adjusted_row = row[:max_cols]
                    adjusted_data.append(adjusted_row)
                
                df = pd.DataFrame(adjusted_data)
            
            print(f"    📊 Created DataFrame: {len(df)} rows x {len(df.columns)} columns")
            
        except Exception as e:
            print(f"    ❌ DataFrame creation error: {e}")
            return None
        
        # Save with title and metadata (model1.py style)
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                # Add title at top
                if title and title.strip():
                    csvfile.write(f'"{title}"\n')
                    csvfile.write('\n')
                    print(f"    📝 Added title to CSV")
                
                # Add page info
                csvfile.write(f'"Extracted from page {page_num}"\n')
                csvfile.write('\n')
                
                # Write DataFrame
                df.to_csv(csvfile, index=False)
            
            print(f"    ✅ Successfully saved: {filename}")
            return filepath
            
        except Exception as e:
            print(f"    ❌ File save error: {e}")
            return None
            
    except Exception as e:
        print(f"    ❌ Table save error: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_pdf_title_safe(pdf_path):
    """Safely extract PDF title"""
    try:
        import fitz
        import re
        from pathlib import Path
        
        doc = fitz.open(pdf_path)
        
        # Try metadata first
        try:
            metadata = doc.metadata
            if metadata and metadata.get('title'):
                title = metadata['title'].strip()
                if title and len(title) > 3:
                    doc.close()
                    return sanitize_filename(title)
        except:
            pass
        
        # Try first page content
        try:
            if len(doc) > 0:
                first_page = doc[0]
                text_dict = first_page.get_text("dict")
                
                # Look for large text at top of page
                candidates = []
                page_height = first_page.rect.height
                
                for block in text_dict.get("blocks", []):
                    if "lines" in block:
                        for line in block["lines"]:
                            bbox = line["bbox"]
                            y_pos = bbox[1]
                            
                            if y_pos < page_height * 0.3:  # Top 30% of page
                                for span in line.get("spans", []):
                                    text = span.get("text", "").strip()
                                    font_size = span.get("size", 0)
                                    
                                    if (text and len(text) > 10 and font_size >= 12):
                                        candidates.append((text, font_size))
                
                if candidates:
                    # Get largest font text
                    candidates.sort(key=lambda x: -x[1])
                    title = candidates[0][0]
                    title = re.sub(r'\s+', ' ', title.strip())
                    
                    if len(title) > 5:
                        doc.close()
                        return sanitize_filename(title)
        except:
            pass
        
        doc.close()
        
    except Exception as e:
        print(f"Title extraction error: {e}")
    
    # Fallback to filename
    try:
        from pathlib import Path
        return sanitize_filename(Path(pdf_path).stem)
    except:
        return "Unknown_PDF"

def sanitize_filename(name):
    """Safely sanitize filename"""
    try:
        import re
        
        if not name:
            return "Unknown_File"
        
        # Remove invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '', str(name))
        sanitized = re.sub(r'\s+', ' ', sanitized)
        sanitized = sanitized.strip(' .')
        
        if len(sanitized) > 80:
            sanitized = sanitized[:80].strip()
        
        if not sanitized:
            sanitized = "Unknown_File"
        
        return sanitized
    except:
        return "Unknown_File"

def save_table_safe(title, headers, data, page_num, table_num, temp_dir):
    """Safely save table to CSV"""
    try:
        import pandas as pd
        import re
        
        # Create safe filename
        if title and title.strip():
            safe_title = sanitize_filename(title)
            filename = f"{safe_title}.csv"
        else:
            filename = f"page_{page_num}_table_{table_num}.csv"
        
        filepath = os.path.join(temp_dir, filename)
        
        # Prepare data safely
        if not data:
            return None
        
        # Fix Excel formula issues
        def fix_cell(cell_value):
            if isinstance(cell_value, str) and cell_value.startswith(('-', '=', '+')):
                if any(c.isalpha() for c in cell_value):
                    return f"'{cell_value}"  # Add quote to prevent formula interpretation
            return cell_value
        
        # Apply fixes
        fixed_data = []
        for row in data:
            fixed_row = [fix_cell(cell) for cell in row]
            fixed_data.append(fixed_row)
        
        # Create DataFrame safely
        try:
            if headers and len(headers) > 0:
                # Ensure data rows match header count
                max_cols = len(headers)
                adjusted_data = []
                for row in fixed_data:
                    if len(row) > max_cols:
                        adjusted_row = row[:max_cols]
                    elif len(row) < max_cols:
                        adjusted_row = row + [''] * (max_cols - len(row))
                    else:
                        adjusted_row = row
                    adjusted_data.append(adjusted_row)
                
                df = pd.DataFrame(adjusted_data, columns=headers)
            else:
                # No headers - use data as is
                df = pd.DataFrame(fixed_data)
        except Exception as e:
            print(f"DataFrame creation error: {e}")
            return None
        
        # Save with title
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                if title and title.strip():
                    csvfile.write(f'"{title}"\n')
                    csvfile.write('\n')
                
                df.to_csv(csvfile, index=False)
            
            return filepath
        except Exception as e:
            print(f"File save error: {e}")
            return None
            
    except Exception as e:
        print(f"Table save error: {e}")
        return None

def extract_basic_safe(file_path, temp_dir, filename):
    """Enhanced basic PDF extraction with multiple methods"""
    try:
        import pandas as pd
        csv_files = []
        extracted_titles = []
        
        print("🔍 Trying basic PDF extraction methods...")
        
        # Method 1: Try pdfplumber (best for tables)
        try:
            import pdfplumber
            print("✓ Using pdfplumber for table extraction...")
            
            with pdfplumber.open(file_path) as pdf:
                print(f"📄 PDF has {len(pdf.pages)} pages")
                
                for page_num, page in enumerate(pdf.pages[:5]):  # Process up to 5 pages
                    try:
                        print(f"  🔍 Scanning page {page_num + 1} for tables...")
                        
                        # Extract tables using pdfplumber
                        tables = page.extract_tables()
                        
                        if tables:
                            print(f"  📊 Found {len(tables)} table(s) on page {page_num + 1}")
                            
                            for table_num, table in enumerate(tables):
                                if table and len(table) > 0:
                                    try:
                                        print(f"    📋 Processing table {table_num + 1}: {len(table)} rows")
                                        
                                        # Clean the table data
                                        cleaned_table = []
                                        for row in table:
                                            if row and any(cell and str(cell).strip() for cell in row):
                                                cleaned_row = [str(cell).strip() if cell else '' for cell in row]
                                                cleaned_table.append(cleaned_row)
                                        
                                        if len(cleaned_table) > 1:  # Must have at least header + 1 data row
                                            # Use first row as headers
                                            headers = cleaned_table[0]
                                            data_rows = cleaned_table[1:]
                                            
                                            # Create DataFrame
                                            df = pd.DataFrame(data_rows, columns=headers)
                                            
                                            # Remove completely empty rows and columns
                                            df = df.dropna(how='all').dropna(axis=1, how='all')
                                            
                                            if not df.empty and len(df.columns) > 1:
                                                # Generate title and filename
                                                table_title = f"Table from page {page_num + 1}"
                                                csv_filename = f"pdfplumber_page_{page_num+1}_table_{table_num+1}.csv"
                                                csv_path = os.path.join(temp_dir, csv_filename)
                                                
                                                # Save with title
                                                with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                                                    csvfile.write(f'"{table_title}"\n')
                                                    csvfile.write(f'"Extracted using pdfplumber from {filename}"\n')
                                                    csvfile.write('\n')
                                                    df.to_csv(csvfile, index=False)
                                                
                                                csv_files.append(csv_path)
                                                extracted_titles.append(table_title)
                                                print(f"    ✅ Saved: {csv_filename}")
                                            else:
                                                print(f"    ⚠️ Table {table_num + 1} is empty after cleaning")
                                        else:
                                            print(f"    ⚠️ Table {table_num + 1} has insufficient data")
                                            
                                    except Exception as e:
                                        print(f"    ❌ Error processing table {table_num + 1}: {e}")
                                        continue
                        else:
                            print(f"  ❌ No tables found on page {page_num + 1}")
                            
                    except Exception as e:
                        print(f"  ❌ Error processing page {page_num + 1}: {e}")
                        continue
            
            if csv_files:
                print(f"✅ pdfplumber extracted {len(csv_files)} tables")
                return {
                    'total_tables_extracted': len(csv_files),
                    'csv_files': csv_files,
                    'extracted_titles': extracted_titles
                }
        
        except ImportError:
            print("⚠️ pdfplumber not available")
        except Exception as e:
            print(f"❌ pdfplumber extraction failed: {e}")
        
        # Method 2: Try PyMuPDF table detection
        try:
            import fitz
            print("✓ Using PyMuPDF for table extraction...")
            
            doc = fitz.open(file_path)
            
            for page_num in range(min(len(doc), 5)):
                try:
                    page = doc.load_page(page_num)
                    print(f"  🔍 Scanning page {page_num + 1} with PyMuPDF...")
                    
                    # Try to find tables
                    tables = page.find_tables()
                    
                    if tables:
                        print(f"  📊 Found {len(tables)} table(s) on page {page_num + 1}")
                        
                        for table_num, table in enumerate(tables):
                            try:
                                # Extract table data
                                table_data = table.extract()
                                
                                if table_data and len(table_data) > 1:
                                    # Convert to DataFrame
                                    df = pd.DataFrame(table_data[1:], columns=table_data[0])
                                    df = df.dropna(how='all').dropna(axis=1, how='all')
                                    
                                    if not df.empty:
                                        table_title = f"PyMuPDF Table from page {page_num + 1}"
                                        csv_filename = f"pymupdf_page_{page_num+1}_table_{table_num+1}.csv"
                                        csv_path = os.path.join(temp_dir, csv_filename)
                                        
                                        # Save with title
                                        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                                            csvfile.write(f'"{table_title}"\n')
                                            csvfile.write(f'"Extracted using PyMuPDF from {filename}"\n')
                                            csvfile.write('\n')
                                            df.to_csv(csvfile, index=False)
                                        
                                        csv_files.append(csv_path)
                                        extracted_titles.append(table_title)
                                        print(f"    ✅ Saved: {csv_filename}")
                                        
                            except Exception as e:
                                print(f"    ❌ Error processing PyMuPDF table {table_num + 1}: {e}")
                                continue
                    else:
                        print(f"  ❌ No tables found on page {page_num + 1}")
                        
                except Exception as e:
                    print(f"  ❌ Error processing page {page_num + 1} with PyMuPDF: {e}")
                    continue
            
            doc.close()
            
            if csv_files:
                print(f"✅ PyMuPDF extracted {len(csv_files)} tables")
                return {
                    'total_tables_extracted': len(csv_files),
                    'csv_files': csv_files,
                    'extracted_titles': extracted_titles
                }
        
        except ImportError:
            print("⚠️ PyMuPDF not available")
        except Exception as e:
            print(f"❌ PyMuPDF extraction failed: {e}")
        
        # Method 3: Text-based extraction using PyPDF2
        try:
            import PyPDF2
            print("✓ Using PyPDF2 for text extraction...")
            
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                all_text = ""
                
                for page_num, page in enumerate(reader.pages[:3]):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():
                            all_text += f"=== Page {page_num + 1} ===\n"
                            all_text += page_text + "\n\n"
                    except Exception as e:
                        print(f"Error extracting text from page {page_num + 1}: {e}")
                        continue
                
                if all_text.strip():
                    txt_filename = f"text_content_{sanitize_filename(filename)}.txt"
                    txt_path = os.path.join(temp_dir, txt_filename)
                    
                    with open(txt_path, 'w', encoding='utf-8') as f:
                        f.write(f"Text Content Extracted from {filename}\n")
                        f.write("=" * 60 + "\n\n")
                        f.write("This file contains the raw text content from the PDF.\n")
                        f.write("You may need to manually format this data into tables.\n\n")
                        f.write(all_text)
                    
                    csv_files.append(txt_path)
                    extracted_titles.append(f"Text content from {filename}")
                    print(f"✅ Saved text content: {txt_filename}")
                    
                    return {
                        'total_tables_extracted': 1,
                        'csv_files': csv_files,
                        'extracted_titles': extracted_titles
                    }
        
        except ImportError:
            print("⚠️ PyPDF2 not available")
        except Exception as e:
            print(f"❌ PyPDF2 extraction failed: {e}")
        
        print("❌ All basic extraction methods failed")
        return None
        
    except Exception as e:
        print(f"❌ Basic extraction error: {e}")
        import traceback
        traceback.print_exc()
        return Nonetables()
                        
                        for table_num, table in enumerate(tables):
                            if table and len(table) > 1:
                                try:
                                    df = pd.DataFrame(table[1:], columns=table[0])
                                    df = df.dropna(how='all').dropna(axis=1, how='all')
                                    
                                    if not df.empty:
                                        csv_filename = f"basic_page_{page_num+1}_table_{table_num+1}.csv"
                                        csv_path = os.path.join(temp_dir, csv_filename)
                                        df.to_csv(csv_path, index=False)
                                        csv_files.append(csv_path)
                                        print(f"✓ Basic extraction: {csv_filename}")
                                except Exception as e:
                                    print(f"Error processing basic table: {e}")
                                    continue
                    except Exception as e:
                        print(f"Error processing page {page_num+1}: {e}")
                        continue
            
            if csv_files:
                return {
                    'total_tables_extracted': len(csv_files),
                    'csv_files': csv_files,
                    'extracted_titles': [f'Basic table {i+1}' for i in range(len(csv_files))]
                }
        
        except ImportError:
            print("pdfplumber not available")
        except Exception as e:
            print(f"pdfplumber error: {e}")
        
        return None
        
    except Exception as e:
        print(f"Basic extraction error: {e}")
        return None

def create_fallback_result(file_path, temp_dir, filename):
    """Create comprehensive fallback result with PDF analysis"""
    try:
        import os
        
        print("📋 Creating comprehensive fallback analysis...")
        
        # Get basic PDF info
        try:
            import fitz
            doc = fitz.open(file_path)
            total_pages = len(doc)
            
            # Analyze first few pages for content
            content_analysis = []
            for page_num in range(min(total_pages, 3)):
                try:
                    page = doc.load_page(page_num)
                    text = page.get_text()
                    
                    # Basic analysis
                    word_count = len(text.split()) if text else 0
                    line_count = len(text.split('\n')) if text else 0
                    
                    # Look for table-like patterns
                    has_numbers = any(c.isdigit() for c in text)
                    has_currency = any(symbol in text for symbol in ['₹', 'Rs', '
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
    app.run(debug=False, host='0.0.0.0', port=port), '€', '£'])
                    has_parentheses = '(' in text and ')' in text
                    
                    content_analysis.append({
                        'page': page_num + 1,
                        'words': word_count,
                        'lines': line_count,
                        'has_numbers': has_numbers,
                        'has_currency': has_currency,
                        'has_parentheses': has_parentheses
                    })
                    
                except Exception as e:
                    print(f"Error analyzing page {page_num + 1}: {e}")
                    continue
            
            doc.close()
            
        except Exception as e:
            print(f"Error getting PDF info: {e}")
            total_pages = "Unknown"
            content_analysis = []
        
        # Create comprehensive report
        txt_filename = f"extraction_report_{sanitize_filename(filename)}.txt"
        txt_path = os.path.join(temp_dir, txt_filename)
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"PDF Table Extraction Report\n")
            f.write(f"=" * 50 + "\n\n")
            f.write(f"File: {filename}\n")
            f.write(f"Total Pages: {total_pages}\n")
            f.write(f"Processing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write(f"EXTRACTION RESULTS:\n")
            f.write(f"-" * 30 + "\n")
            f.write(f"✅ Advanced AI Extraction: Attempted\n")
            f.write(f"✅ Basic PDF Extraction: Attempted\n")
            f.write(f"❌ Result: No extractable tables found\n\n")
            
            f.write(f"POSSIBLE REASONS:\n")
            f.write(f"-" * 20 + "\n")
            f.write(f"• Tables may be embedded as images\n")
            f.write(f"• PDF may be scanned/non-searchable\n")
            f.write(f"• Tables may have complex formatting\n")
            f.write(f"• Content may not be in standard table format\n\n")
            
            if content_analysis:
                f.write(f"CONTENT ANALYSIS:\n")
                f.write(f"-" * 20 + "\n")
                for analysis in content_analysis:
                    f.write(f"Page {analysis['page']}:\n")
                    f.write(f"  Words: {analysis['words']}\n")
                    f.write(f"  Lines: {analysis['lines']}\n")
                    f.write(f"  Contains Numbers: {'Yes' if analysis['has_numbers'] else 'No'}\n")
                    f.write(f"  Contains Currency: {'Yes' if analysis['has_currency'] else 'No'}\n")
                    f.write(f"  Contains Parentheses: {'Yes' if analysis['has_parentheses'] else 'No'}\n\n")
            
            f.write(f"RECOMMENDATIONS:\n")
            f.write(f"-" * 20 + "\n")
            f.write(f"1. Ensure PDF contains searchable text (not just images)\n")
            f.write(f"2. Try converting PDF to a different format\n")
            f.write(f"3. Check if tables have clear borders and structure\n")
            f.write(f"4. For scanned PDFs, try OCR preprocessing\n")
            f.write(f"5. Verify the Google AI API key is working correctly\n\n")
            
            f.write(f"NEXT STEPS:\n")
            f.write(f"-" * 20 + "\n")
            f.write(f"• Try a different PDF with clearer table structure\n")
            f.write(f"• Check if the PDF opens correctly in other applications\n")
            f.write(f"• Consider manual data entry for complex layouts\n")
        
        print(f"✅ Created comprehensive report: {txt_filename}")
        
        return {
            'total_tables_extracted': 1,
            'csv_files': [txt_path],
            'extracted_titles': [f'Extraction Report for {filename}']
        }
        
    except Exception as e:
        print(f"❌ Fallback creation error: {e}")
        
        # Ultra-simple fallback
        try:
            simple_txt_filename = f"simple_report.txt"
            simple_txt_path = os.path.join(temp_dir, simple_txt_filename)
            
            with open(simple_txt_path, 'w', encoding='utf-8') as f:
                f.write(f"PDF Processing Report\n")
                f.write(f"File: {filename}\n")
                f.write(f"Status: No tables could be extracted\n")
                f.write(f"This may indicate the PDF contains non-standard table formats\n")
            
            return {
                'total_tables_extracted': 1,
                'csv_files': [simple_txt_path],
                'extracted_titles': ['Processing Report']
            }
        except:
            return {
                'total_tables_extracted': 0,
                'csv_files': [],
                'extracted_titles': []
            }
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
