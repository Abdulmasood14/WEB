import os
import logging
import pandas as pd
import google.generativeai as genai
from typing import Optional, Dict, Any, List
import json
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFExtractor:
    def __init__(self):
        """Initialize the PDF extractor with Google Gemini API"""
        try:
            # Configure Google Gemini API
            api_key = os.environ.get('GOOGLE_API_KEY')
            if not api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set")
            
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            logger.info("PDF Extractor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize PDF Extractor: {str(e)}")
            raise

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF using PyMuPDF with error handling"""
        try:
            import fitz  # PyMuPDF
            
            # Open PDF document
            doc = fitz.open(pdf_path)
            text = ""
            
            # Extract text from each page
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text += page.get_text()
                text += "\n\n"  # Add page separator
            
            doc.close()
            
            if not text.strip():
                raise ValueError("No text could be extracted from the PDF")
            
            logger.info(f"Successfully extracted {len(text)} characters from PDF")
            return text
            
        except ImportError:
            logger.error("PyMuPDF (fitz) not available. Cannot extract PDF text.")
            raise ImportError("PyMuPDF is required for PDF text extraction")
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise

    def process_with_gemini(self, text: str) -> Dict[str, Any]:
        """Process extracted text with Google Gemini API"""
        try:
            # Create a comprehensive prompt for data extraction
            prompt = f"""
            Please analyze the following text and extract structured information. 
            Return the response as a JSON object with the following structure:
            {{
                "summary": "Brief summary of the document",
                "key_points": ["List of key points"],
                "entities": {{
                    "people": ["List of person names"],
                    "organizations": ["List of organization names"],
                    "locations": ["List of locations"],
                    "dates": ["List of dates"]
                }},
                "topics": ["List of main topics"],
                "document_type": "Type of document (e.g., report, contract, etc.)",
                "metadata": {{
                    "word_count": approximate_word_count,
                    "language": "detected_language"
                }}
            }}
            
            Text to analyze:
            {text[:4000]}...
            """
            
            # Generate response using Gemini
            response = self.model.generate_content(prompt)
            
            if not response or not response.text:
                raise ValueError("Empty response from Gemini API")
            
            # Parse JSON response
            try:
                structured_data = json.loads(response.text)
            except json.JSONDecodeError:
                # If JSON parsing fails, create a basic structure
                structured_data = {
                    "summary": response.text[:500] + "..." if len(response.text) > 500 else response.text,
                    "key_points": self._extract_sentences(response.text)[:5],
                    "entities": {"people": [], "organizations": [], "locations": [], "dates": []},
                    "topics": ["General Document"],
                    "document_type": "Unknown",
                    "metadata": {"word_count": len(text.split()), "language": "Unknown"}
                }
            
            logger.info("Successfully processed text with Gemini API")
            return structured_data
            
        except Exception as e:
            logger.error(f"Error processing with Gemini API: {str(e)}")
            # Return fallback data structure
            return {
                "summary": "Error processing document with AI",
                "key_points": ["Document processing failed"],
                "entities": {"people": [], "organizations": [], "locations": [], "dates": []},
                "topics": ["Error"],
                "document_type": "Unknown",
                "metadata": {"word_count": len(text.split()), "language": "Unknown"},
                "error": str(e)
            }

    def _extract_sentences(self, text: str) -> List[str]:
        """Extract sentences from text for fallback processing"""
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10][:10]

    def extract_data(self, pdf_path: str) -> Optional[Dict[str, Any]]:
        """Main method to extract and process data from PDF"""
        try:
            # Check if file exists
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            # Extract text from PDF
            logger.info(f"Starting text extraction from: {pdf_path}")
            text = self.extract_text_from_pdf(pdf_path)
            
            if not text.strip():
                raise ValueError("No text content found in PDF")
            
            # Process text with Gemini API
            logger.info("Processing extracted text with AI")
            structured_data = self.process_with_gemini(text)
            
            # Add original text length for reference
            structured_data["original_text_length"] = len(text)
            structured_data["extraction_status"] = "success"
            
            return structured_data
            
        except Exception as e:
            logger.error(f"Error in extract_data: {str(e)}")
            return {
                "extraction_status": "failed",
                "error": str(e),
                "summary": "Failed to process document",
                "key_points": [],
                "entities": {"people": [], "organizations": [], "locations": [], "dates": []},
                "topics": [],
                "document_type": "Unknown",
                "metadata": {"word_count": 0, "language": "Unknown"}
            }

    def save_to_excel(self, data: Dict[str, Any], output_path: str) -> bool:
        """Save extracted data to Excel file"""
        try:
            # Create DataFrame from structured data
            df_data = []
            
            # Add basic information
            df_data.append(["Document Type", data.get("document_type", "Unknown")])
            df_data.append(["Summary", data.get("summary", "No summary available")])
            df_data.append(["Word Count", data.get("metadata", {}).get("word_count", 0)])
            df_data.append(["Language", data.get("metadata", {}).get("language", "Unknown")])
            
            # Add key points
            key_points = data.get("key_points", [])
            for i, point in enumerate(key_points, 1):
                df_data.append([f"Key Point {i}", point])
            
            # Add entities
            entities = data.get("entities", {})
            for entity_type, entity_list in entities.items():
                for entity in entity_list:
                    df_data.append([f"{entity_type.capitalize()}", entity])
            
            # Add topics
            topics = data.get("topics", [])
            for topic in topics:
                df_data.append(["Topic", topic])
            
            # Create DataFrame
            df = pd.DataFrame(df_data, columns=["Field", "Value"])
            
            # Save to Excel
            df.to_excel(output_path, index=False)
            logger.info(f"Data saved to Excel: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving to Excel: {str(e)}")
            return False
