from flask import Flask, request, jsonify, send_file
import os
import tempfile
import uuid
import json
import base64
import io
import zipfile
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

app = Flask(__name__)

# Simple in-memory storage
results_store = {}

@app.route('/')
def home():
    """Advanced HTML page with full Gemini AI integration"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Advanced PDF Table Extractor</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 900px; margin: 50px auto; padding: 20px; background: #f5f5f5; }
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
            .progress { background: #e9ecef; border-radius: 5px; overflow: hidden; margin: 10px 0; }
            .progress-bar { background: #007bff; height: 8px; transition: width 0.3s ease; }
            .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #007bff; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 10px auto; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            small { color: #6c757d; display: block; margin-top: 5px; }
            .status { font-weight: bold; margin: 10px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Advanced PDF Table Extractor</h1>
                <p>AI-Powered with Google Gemini 2.0 Flash & PyMuPDF</p>
            </div>
            
            <div class="features">
                <div class="feature">
                    <h4>🧠 Gemini 2.0 Flash AI</h4>
                    <p>Advanced AI for intelligent table recognition with specialized financial prompts</p>
                </div>
                <div class="feature">
                    <h4>📊 Financial Expertise</h4>
                    <p>Quarter/Nine Months handling, deferred tax extraction, Roman numerals</p>
                </div>
                <div class="feature">
                    <h4>🎯 Precision Extraction</h4>
                    <p>Maintains exact formatting, handles "- Deferred Tax Expenses / (Income)"</p>
                </div>
                <div class="feature">
                    <h4>📁 Smart Organization</h4>
                    <p>Auto-detects PDF titles, combines multi-page tables, prevents Excel errors</p>
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
                    <small>Upload PDF files with tables (financial statements work best)</small>
                </div>
                
                <button type="submit" id="submitBtn">🚀 Extract Tables with Advanced AI</button>
            </form>
            
            <div id="loading" class="hidden">
                <div class="alert alert-warning">
                    <div class="spinner"></div>
                    <div class="status" id="statusText">Initializing advanced AI extraction...</div>
                    <div class="progress">
                        <div class="progress-bar" id="progressBar"></div>
                    </div>
                    <p id="progressText">Preparing advanced PDF processing...</p>
                </div>
            </div>
            
            <div id="message"></div>
            <div id="results"></div>
        </div>
        
        <script>
            let statusMessages = [
                'Installing PyMuPDF and dependencies...',
                'Initializing Gemini 2.0 Flash model...',
                'Converting PDF to high-resolution images...',
                'Detecting table structures with AI...',
                'Extracting Quarter/Nine Months data...',
                'Processing "- Deferred Tax Expenses / (Income)"...',
                'Combining multi-page tables...',
                'Generating organized CSV files...',
                'Creating summary reports...'
            ];
            let currentStatus = 0;
            let statusInterval;
            let progressInterval;
            
            function updateStatus() {
                const statusText = document.getElementById('statusText');
                const progressText = document.getElementById('progressText');
                
                if (currentStatus < statusMessages.length) {
                    statusText.textContent = statusMessages[currentStatus];
                    progressText.textContent = `Advanced processing step ${currentStatus + 1} of ${statusMessages.length}`;
                    currentStatus++;
                } else {
                    statusText.textContent = 'Finalizing advanced extraction...';
                    progressText.textContent = 'Preparing comprehensive results...';
                }
            }
            
            function updateProgress() {
                const progressBar = document.getElementById('progressBar');
                let progress = 0;
                
                progressInterval = setInterval(() => {
                    progress += Math.random() * 10;
                    if (progress > 95) progress = 95;
                    progressBar.style.width = progress + '%';
                }, 1000);
            }
            
            document.getElementById('uploadForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const apiKey = document.getElementById('apiKey').value;
                const pdfFile = document.getElementById('pdfFile').files[0];
                const loading = document.getElementById('loading');
                const message = document.getElementById('message');
                const results = document.getElementById('results');
                const submitBtn = document.getElementById('submitBtn');
                
                // Validation
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
                submitBtn.textContent = '🔄 Processing with Advanced AI...';
                
                currentStatus = 0;
                updateStatus();
                updateProgress();
                statusInterval = setInterval(updateStatus, 3000);
                
                try {
                    // Create form data
                    const formData = new FormData();
                    formData.append('api_key', apiKey);
                    formData.append('file', pdfFile);
                    
                    // Send request
                    const response = await fetch('/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const text = await response.text();
                    
                    if (!text.trim()) {
                        throw new Error('Server returned empty response');
                    }
                    
                    const data = JSON.parse(text);
                    
                    // Complete progress
                    clearInterval(statusInterval);
                    clearInterval(progressInterval);
                    document.getElementById('progressBar').style.width = '100%';
                    
                    setTimeout(() => {
                        loading.classList.add('hidden');
                        
                        if (data.success) {
                            message.innerHTML = '<div class="alert alert-success"><strong>✅ Success!</strong> Advanced AI extraction completed successfully</div>';
                            
                            let resultsHTML = `
                                <h3>📊 Advanced Extraction Results</h3>
                                <div class="result-item"><strong>📄 File:</strong> ${data.results.pdf_name}</div>
                                <div class="result-item"><strong>📑 Pages Processed:</strong> ${data.results.total_pages}</div>
                                <div class="result-item"><strong>🤖 AI Method:</strong> ${data.results.method}</div>
                                <div class="result-item"><strong>📊 Tables Extracted:</strong> ${data.results.total_tables_extracted}</div>
                                <div class="result-item"><strong>📁 Output Directory:</strong> ${data.results.output_directory}</div>
                            `;
                            
                            if (data.results.extracted_titles && data.results.extracted_titles.length > 0) {
                                resultsHTML += '<div class="result-item"><strong>📝 Extracted Titles:</strong><ul>';
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
                                
                                if (data.results.summary_report) {
                                    resultsHTML += `<div class="result-item">
                                        <a href="/download_csv/${data.extraction_id}/${data.results.summary_report}" style="color: #6f42c1; text-decoration: none;">
                                            📋 Download Summary Report
                                        </a>
                                    </div>`;
                                }
                            }
                            
                            results.innerHTML = resultsHTML;
                        } else {
                            message.innerHTML = `<div class="alert alert-error"><strong>❌ Error:</strong> ${data.error}</div>`;
                        }
                    }, 1500);
                    
                } catch (err) {
                    clearInterval(statusInterval);
                    clearInterval(progressInterval);
                    loading.classList.add('hidden');
                    console.error('Error:', err);
                    message.innerHTML = `<div class="alert alert-error"><strong>❌ Error:</strong> ${err.message}</div>`;
                } finally {
                    submitBtn.disabled = false;
                    submitBtn.textContent = '🚀 Extract Tables with Advanced AI';
                }
            });
        </script>
    </body>
    </html>
    """

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'message': 'Advanced PDF Table Extractor running'})

@app.route('/upload', methods=['POST'])
def upload():
    """Handle file upload with full advanced AI extraction"""
    try:
        print("=== ADVANCED UPLOAD STARTED ===")
        
        # Check request
        if not request.files or 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        api_key = request.form.get('api_key', '').strip()
        
        print(f"File: {file.filename}")
        print(f"API key length: {len(api_key)}")
        
        # Validate inputs
        if not file or not file.filename:
            return jsonify({'error': 'No file selected'}), 400
            
        if not api_key:
            return jsonify({'error': 'Google AI API key is required for advanced extraction'}), 400
            
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
        
        # Initialize advanced AI extractor
        try:
            extractor = PDFTableExtractor(api_key, temp_dir)
            print("✓ Advanced AI extractor initialized")
        except Exception as e:
            return jsonify({'error': f'AI initialization failed: {str(e)}'}), 500
        
        # Extract tables using advanced AI
        extraction_result = extractor.process_pdf(file_path)
        
        # Generate summary report
        summary_report = extractor.generate_summary_report(extraction_result)
        
        # Store results
        results_store[extraction_id] = extraction_result
        
        return jsonify({
            'success': True,
            'extraction_id': extraction_id,
            'results': {
                'pdf_name': file.filename,
                'total_pages': extraction_result['total_pages'],
                'method': 'Google Gemini 2.0 Flash with PyMuPDF',
                'total_tables_extracted': extraction_result['total_tables_extracted'],
                'csv_files': [os.path.basename(f) for f in extraction_result['csv_files']],
                'extracted_titles': extraction_result.get('extracted_titles', []),
                'output_directory': extraction_result.get('output_directory', ''),
                'summary_report': os.path.basename(summary_report) if summary_report else None
            }
        })
        
    except Exception as e:
        print(f"General error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

class PDFTableExtractor:
    """Advanced AI-powered PDF table extractor using Gemini 2.0 Flash with complete functionality"""
    
    def __init__(self, api_key: str, temp_dir: str):
        self.api_key = api_key
        self.temp_dir = temp_dir
        
        # Install and import dependencies
        self.setup_dependencies()
        
        # Initialize Gemini
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Setup output directory
        self.base_output_dir = Path(temp_dir)
        self.output_dir = None
        
        print("✓ Advanced Gemini 2.0 Flash model initialized with full functionality")
    
    def setup_dependencies(self):
        """Install required dependencies dynamically"""
        packages = [
            'google-generativeai==0.3.2',
            'PyMuPDF==1.23.8',
            'Pillow==9.5.0'
        ]
        
        for package in packages:
            try:
                # Try to import first
                if 'google-generativeai' in package:
                    import google.generativeai
                elif 'PyMuPDF' in package:
                    import fitz
                elif 'Pillow' in package:
                    from PIL import Image
                print(f"✓ {package.split('==')[0]} already available")
            except ImportError:
                self.install_package_safely(package)
    
    def install_package_safely(self, package_name):
        """Safely install a package with error handling"""
        try:
            import subprocess
            import sys
            print(f"Installing {package_name}...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", 
                "--no-cache-dir", "--disable-pip-version-check", 
                package_name
            ], timeout=120)
            print(f"✓ {package_name} installed successfully")
            return True
        except Exception as e:
            print(f"✗ Failed to install {package_name}: {e}")
            return False
    
    def extract_pdf_title(self, pdf_path: str) -> str:
        """Extract title from PDF metadata or first page content"""
        try:
            import fitz
            doc = fitz.open(pdf_path)
            
            # First try to get title from metadata
            metadata = doc.metadata
            if metadata and metadata.get('title'):
                title = metadata['title'].strip()
                if title and len(title) > 3:
                    doc.close()
                    return self.sanitize_directory_name(title)
            
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
                        return self.sanitize_directory_name(potential_title)
            
            doc.close()
            
        except Exception as e:
            print(f"Error extracting PDF title: {e}")
        
        pdf_name = Path(pdf_path).stem
        return self.sanitize_directory_name(pdf_name)
    
    def sanitize_directory_name(self, name: str) -> str:
        """Sanitize a string to be used as a directory name"""
        sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
        sanitized = re.sub(r'\s+', ' ', sanitized)
        sanitized = sanitized.strip(' .')
        
        if len(sanitized) > 100:
            sanitized = sanitized[:100].strip()
        
        if not sanitized:
            sanitized = "Untitled_PDF"
        
        return sanitized
    
    def setup_output_directory(self, pdf_path: str):
        """Setup output directory based on PDF title"""
        pdf_title = self.extract_pdf_title(pdf_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dir_name = f"{pdf_title}_{timestamp}"
        
        self.output_dir = self.base_output_dir / dir_name
        self.output_dir.mkdir(exist_ok=True)
        
        print(f"📁 Created output directory: {self.output_dir}")
        print(f"📄 PDF Title detected: {pdf_title}")
    
    def pdf_to_images(self, pdf_path: str) -> List:
        """Convert PDF pages to images using PyMuPDF"""
        try:
            import fitz
            from PIL import Image
            
            doc = fitz.open(pdf_path)
            images = []
            
            for page_num in range(min(len(doc), 20)):  # Limit to 20 pages
                page = doc.load_page(page_num)
                mat = fitz.Matrix(3.0, 3.0)  # High resolution for better AI recognition
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                images.append(img)
                print(f"✓ Converted page {page_num + 1} to high-resolution image")
            
            doc.close()
            print(f"✓ Converted {len(images)} pages using PyMuPDF")
            return images
            
        except Exception as e:
            print(f"Error converting PDF to images: {e}")
            return []
    
    def create_table_extraction_prompt(self) -> str:
        """Create the advanced prompt for table extraction"""
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
        - This is DESCRIPTIVE TEXT, not a formula or calculation

        STEP 3 - QUARTER AND NINE MONTHS COLUMN HANDLING:
        - Look for column headers that contain "Quarter Ended" and "Nine Months Ended"
        - Extract these headers exactly as they appear with dates
        - Preserve the exact format: "Quarter Ended [Date]" and "Nine Months Ended [Date]"
        - Look for additional qualifiers like "Reviewed" or "Unaudited" if present

        STEP 4 - SERIAL NUMBER (Sr. No.) HANDLING:
        - Serial numbers are: I, II, III, IV, V, VI, VII, VIII, IX (Roman numerals)
        - Extract EXACTLY as shown without parentheses
        - Do NOT convert to Arabic numbers

        STEP 5 - FINANCIAL DATA HANDLING:
        - Extract ALL numerical values exactly as shown
        - Preserve negative values in parentheses: (135.30), (121.26)
        - Keep dash symbols as "-" for zero/nil values
        - Maintain exact decimal precision and commas

        OUTPUT FORMAT:
        {
            "has_tables": true/false,
            "tables": [
                {
                    "title": "Complete table title with currency info",
                    "headers": ["Column headers exactly as shown"],
                    "data": [
                        ["Row data exactly as extracted"],
                        ["Including negative values in parentheses"],
                        ["And descriptive text with dashes"]
                    ]
                }
            ]
        }

        Remember: Extract everything EXACTLY as written. Text starting with "- " is descriptive text, not formulas.
        """
    
    def extract_tables_from_image(self, image) -> Dict:
        """Extract tables from image using Gemini AI with advanced processing"""
        try:
            prompt = self.create_table_extraction_prompt()
            
            generation_config = {
                'temperature': 0.1,
                'top_p': 0.8,
                'top_k': 40,
                'max_output_tokens': 8192,
            }
            
            response = self.model.generate_content(
                [prompt, image],
                generation_config=generation_config
            )
            
            response_text = response.text.strip()
            
            # Clean up response
            if response_text.startswith('```json'):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith('```'):
                response_text = response_text[3:-3].strip()
            
            if response_text.endswith('```'):
                response_text = response_text[:-3].strip()
            
            try:
                result = json.loads(response_text)
                
                if not isinstance(result, dict):
                    return {"has_tables": False, "tables": []}
                
                if "has_tables" not in result:
                    return {"has_tables": False, "tables": []}
                
                # Validate table structure
                if result.get("has_tables") and result.get("tables"):
                    valid_tables = []
                    for table in result["tables"]:
                        if isinstance(table, dict):
                            if "headers" not in table:
                                table["headers"] = []
                            if "data" not in table:
                                table["data"] = []
                            if "title" not in table:
                                table["title"] = None
                            valid_tables.append(table)
                    result["tables"] = valid_tables
                
                return result
                
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                return {"has_tables": False, "tables": []}
                
        except Exception as e:
            print(f"Error extracting tables from image: {e}")
            return {"has_tables": False, "tables": []}
    
    def save_combined_table_to_csv(self, combined_table: Dict, pdf_name: str) -> str:
        """Save combined table data to CSV file with advanced formatting"""
        try:
            import pandas as pd
            
            title = combined_table.get('title', '')
            if title:
                safe_filename = re.sub(r'[<>:"/\\|?*]', '', title)
                safe_filename = safe_filename.replace('(Rs. In Lakhs)', '').strip()
                safe_filename = re.sub(r'\s+', ' ', safe_filename)
                filename = f"{safe_filename}.csv"
            else:
                filename = f"{pdf_name}_Combined_Table.csv"
            
            filepath = self.output_dir / filename
            
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
            
            print(f"✓ Saved combined table: {filepath}")
            return str(filepath)
            
        except Exception as e:
            print(f"Error saving combined table: {e}")
            return None
    
    def normalize_title_for_grouping(self, title: str, page_num: int) -> str:
        """Normalize title for better grouping of continuation tables"""
        if not title or title.strip() == '':
            return f"Table_Page_{page_num}"
        
        normalized = re.sub(r'\s+', ' ', title.strip())
        
        # Remove continuation indicators
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
        
        # Normalize company patterns
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
    
    def are_headers_compatible(self, headers1: List, headers2: List) -> bool:
        """Check if two header sets are compatible for table continuation"""
        if not headers1 or not headers2:
            return True
        
        norm_headers1 = [re.sub(r'\s+', ' ', str(h).strip().lower()) for h in headers1]
        norm_headers2 = [re.sub(r'\s+', ' ', str(h).strip().lower()) for h in headers2]
        
        if norm_headers1 == norm_headers2:
            return True
        
        if len(norm_headers1) > 0 and len(norm_headers2) > 0:
            common_headers = set(norm_headers1) & set(norm_headers2)
            overlap_ratio = len(common_headers) / max(len(norm_headers1), len(norm_headers2))
            
            if overlap_ratio >= 0.7:
                return True
        
        if set(norm_headers1).issubset(set(norm_headers2)) or set(norm_headers2).issubset(set(norm_headers1)):
            return True
        
        financial_keywords = ['particulars', 'sr. no', 'march', 'december', 'audited', 'reviewed', 'quarter ended', 'nine months ended']
        headers1_has_financial = any(keyword in ' '.join(norm_headers1) for keyword in financial_keywords)
        headers2_has_financial = any(keyword in ' '.join(norm_headers2) for keyword in financial_keywords)
        
        if headers1_has_financial and headers2_has_financial:
            return True
        
        return False
    
    def process_pdf(self, pdf_path: str) -> Dict:
        """Process entire PDF and extract all tables with advanced AI"""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        self.setup_output_directory(str(pdf_path))
        
        pdf_name = pdf_path.stem
        print(f"Processing PDF with advanced AI: {pdf_name}")
        
        # Convert PDF to images
        images = self.pdf_to_images(str(pdf_path))
        if not images:
            return {
                "error": "Failed to convert PDF to images",
                "pdf_name": pdf_name,
                "total_pages": 0,
                "pages_with_tables": 0,
                "total_tables_extracted": 0,
                "csv_files": [],
                "page_results": [],
                "extracted_titles": []
            }
        
        results = {
            "pdf_name": pdf_name,
            "output_directory": str(self.output_dir),
            "total_pages": len(images),
            "pages_with_tables": 0,
            "total_tables_extracted": 0,
            "csv_files": [],
            "page_results": [],
            "extracted_titles": []
        }
        
        tables_by_title = {}
        
        # Process each page with AI
        for page_num, image in enumerate(images, 1):
            print(f"\nProcessing page {page_num}/{len(images)} with Gemini AI...")
            
            try:
                extraction_result = self.extract_tables_from_image(image)
                
                page_result = {
                    "page_number": page_num,
                    "has_tables": extraction_result.get("has_tables", False),
                    "tables_count": len(extraction_result.get("tables", [])),
                    "tables": []
                }
                
                if extraction_result.get("has_tables", False):
                    results["pages_with_tables"] += 1
                    tables = extraction_result.get("tables", [])
                    
                    for table_num, table_data in enumerate(tables, 1):
                        title = table_data.get('title', 'Untitled Table')
                        print(f"  Found table: {title}")
                        
                        if table_data.get('title'):
                            results["extracted_titles"].append(table_data.get('title'))
                        
                        normalized_title = self.normalize_title_for_grouping(title, page_num)
                        
                        if normalized_title not in tables_by_title:
                            tables_by_title[normalized_title] = {
                                "title": title,
                                "headers": table_data.get('headers', []),
                                "data": table_data.get('data', []),
                                "pages": [page_num],
                                "table_numbers": [table_num],
                                "original_titles": [title]
                            }
                        else:
                            existing_table = tables_by_title[normalized_title]
                            
                            if self.are_headers_compatible(existing_table["headers"], table_data.get('headers', [])):
                                existing_table["data"].extend(table_data.get('data', []))
                                existing_table["pages"].append(page_num)
                                existing_table["table_numbers"].append(table_num)
                                existing_table["original_titles"].append(title)
                                print(f"    Combined continuation data from pages: {existing_table['pages']}")
                            else:
                                alt_normalized_title = f"{normalized_title}_v{len([k for k in tables_by_title.keys() if k.startswith(normalized_title)])+1}"
                                tables_by_title[alt_normalized_title] = {
                                    "title": title,
                                    "headers": table_data.get('headers', []),
                                    "data": table_data.get('data', []),
                                    "pages": [page_num],
                                    "table_numbers": [table_num],
                                    "original_titles": [title]
                                }
                        
                        page_result["tables"].append({
                            "title": table_data.get("title"),
                            "table_number": table_data.get("table_number"),
                            "normalized_title": normalized_title,
                            "rows": len(table_data.get("data", [])),
                            "columns": len(table_data.get("headers", []))
                        })
                else:
                    print(f"  No tables found on page {page_num}")
                
                results["page_results"].append(page_result)
                
            except Exception as e:
                print(f"  Error processing page {page_num}: {e}")
                page_result = {
                    "page_number": page_num,
                    "has_tables": False,
                    "tables_count": 0,
                    "tables": [],
                    "error": str(e)
                }
                results["page_results"].append(page_result)
        
        # Save combined tables
        print(f"\nCombining and saving tables...")
        for normalized_title, combined_table in tables_by_title.items():
            print(f"\nSaving advanced table: {normalized_title}")
            print(f"  Pages: {combined_table['pages']}")
            print(f"  Total rows: {len(combined_table['data'])}")
            
            csv_path = self.save_combined_table_to_csv(combined_table, pdf_name)
            
            if csv_path:
                results["csv_files"].append(csv_path)
                results["total_tables_extracted"] += 1
        
        return results
    
    def generate_summary_report(self, results: Dict) -> str:
        """Generate a comprehensive summary report"""
        try:
            report_path = self.output_dir / f"{results['pdf_name']}_extraction_summary.txt"
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(f"Advanced PDF Table Extraction Summary\n")
                f.write(f"=" * 50 + "\n\n")
                f.write(f"PDF File: {results['pdf_name']}\n")
                f.write(f"Output Directory: {results['output_directory']}\n")
                f.write(f"Processing Method: Google Gemini 2.0 Flash with PyMuPDF\n")
                f.write(f"Total Pages: {results['total_pages']}\n")
                f.write(f"Pages with Tables: {results['pages_with_tables']}\n")
                f.write(f"Total Tables Extracted: {results['total_tables_extracted']}\n\n")
                
                f.write("Advanced Features Used:\n")
                f.write("✓ High-resolution PDF to image conversion (3x zoom)\n")
                f.write("✓ Gemini 2.0 Flash AI with specialized financial prompts\n")
                f.write("✓ Quarter/Nine Months period detection\n")
                f.write("✓ Deferred Tax Expenses extraction\n")
                f.write("✓ Roman numeral serial number handling\n")
                f.write("✓ Multi-page table continuation detection\n")
                f.write("✓ Excel formula error prevention\n")
                f.write("✓ Smart title normalization and grouping\n\n")
                
                if results.get('extracted_titles'):
                    f.write("Extracted Titles from PDF:\n")
                    f.write("-" * 30 + "\n")
                    for i, title in enumerate(results['extracted_titles'], 1):
                        f.write(f"{i}. {title}\n")
                    f.write("\n")
                
                f.write("Generated CSV Files:\n")
                f.write("-" * 30 + "\n")
                for csv_file in results['csv_files']:
                    f.write(f"• {os.path.basename(csv_file)}\n")
                
                f.write(f"\nDetailed Page Analysis:\n")
                f.write("-" * 30 + "\n")
                for page_result in results['page_results']:
                    f.write(f"Page {page_result['page_number']}: ")
                    if page_result['has_tables']:
                        f.write(f"{page_result['tables_count']} table(s) found\n")
                        for table in page_result['tables']:
                            f.write(f"  - {table['title']} ({table['rows']} rows, {table['columns']} cols)\n")
                    else:
                        f.write("No tables detected\n")
                
                f.write(f"\nProcessing completed successfully with advanced AI capabilities.\n")
            
            return str(report_path)
            
        except Exception as e:
            print(f"Error generating summary report: {e}")
            return None

@app.route('/download/<extraction_id>')
def download_zip(extraction_id):
    """Download all files as ZIP"""
    try:
        if extraction_id not in results_store:
            return jsonify({'error': 'Results not found'}), 404
        
        results = results_store[extraction_id]
        
        if not results['csv_files']:
            return jsonify({'error': 'No files to download'}), 404
        
        zip_path = os.path.join(os.path.dirname(results['csv_files'][0]), 'advanced_extraction_results.zip')
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file_path in results['csv_files']:
                if os.path.exists(file_path):
                    zipf.write(file_path, os.path.basename(file_path))
        
        return send_file(zip_path, as_attachment=True, download_name='advanced_extraction_results.zip')
        
    except Exception as e:
        return jsonify({'error': f'Download error: {str(e)}'}), 500

@app.route('/download_csv/<extraction_id>/<filename>')
def download_csv(extraction_id, filename):
    """Download single CSV file"""
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
    print(f"🚀 Starting Advanced PDF Table Extractor on port {port}")
    print(f"🧠 Powered by Google Gemini 2.0 Flash AI with PyMuPDF")
    print(f"📊 Advanced financial table extraction with Quarter/Nine Months support")
    app.run(debug=False, host='0.0.0.0', port=port)
