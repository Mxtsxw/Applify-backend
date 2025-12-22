import os
import logging
from PyPDF2 import PdfReader
from docx import Document

def extract_text_from_file(file_path: str) -> str:
    """Robustly extracts text from PDF, DOCX, or TXT files."""
    if not os.path.exists(file_path):
        return "[Error: File not found on server]"
    
    ext = file_path.split('.')[-1].lower()
    text = ""

    try:
        if ext == 'pdf':
            reader = PdfReader(file_path)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        elif ext in ['docx', 'doc']:
            doc = Document(file_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif ext == 'txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            return "[Error: Unsupported file format.]"
            
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")
        return "[Error: Could not parse file content.]"

    return text.strip()