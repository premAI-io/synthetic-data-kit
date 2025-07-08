# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.
# PDF parser logic
import os
from typing import Dict, Any

from synthetic_data_kit.utils.text import clean_extracted_text

class PDFParser:
    """Parser for PDF documents"""
    
    def parse(self, file_path: str) -> str:
        """Parse a PDF file into plain text
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Extracted text from the PDF
        """
        # Primary extraction using pdfminer
        text = self._extract_with_pdfminer(file_path)
        
        # Clean the extracted text
        text = clean_extracted_text(text)
        
        # If text is empty or very short, try OCR fallback
        if not text or len(text.strip()) < 10:
            text = self._extract_with_ocr_fallback(file_path)
            text = clean_extracted_text(text)
        
        return text
    
    def _extract_with_pdfminer(self, file_path: str) -> str:
        """Extract text using pdfminer"""
        try:
            from pdfminer.high_level import extract_text
            return extract_text(file_path)
        except ImportError:
            raise ImportError("pdfminer.six is required for PDF parsing. Install it with: pip install pdfminer.six")
        except Exception:
            # If pdfminer fails, return empty string to trigger fallback
            return ""
    
    def _extract_with_ocr_fallback(self, file_path: str) -> str:
        """Fallback OCR extraction using PyMuPDF and pytesseract"""
        try:
            import fitz  # PyMuPDF
            import pytesseract
            from PIL import Image
            import io
            
            # Open the PDF document
            doc = fitz.open(file_path)
            
            # Extract text from each page
            text = ""
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Convert page to image
                pix = page.get_pixmap()
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                
                # Extract text from image using OCR
                page_text = pytesseract.image_to_string(image)
                text += page_text + "\n"
            
            doc.close()
            return text
            
        except ImportError as e:
            missing_lib = "PyMuPDF" if "fitz" in str(e) else "pytesseract"
            print(f"Warning: {missing_lib} not available for OCR fallback. Install with: pip install {missing_lib}")
            return ""
        except Exception as e:
            print(f"Warning: OCR fallback failed: {str(e)}")
            return ""


    def save(self, content: str, output_path: str) -> None:
        """Save the extracted text to a file
        
        Args:
            content: Extracted text content
            output_path: Path to save the text
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)