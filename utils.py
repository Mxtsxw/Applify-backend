import os
import logging
import requests
from fastapi import HTTPException

TEMPLATE_FILE_PATH = os.path.join(os.path.dirname(__file__), "templates", "coverLetter.txt")
_DEFAULT_TEMPLATE_CACHE: str | None = None

def get_default_template() -> str:
    """
    Reads and returns the default cover letter template from the file system.
    Caches the result after the first read.
    """
    global _DEFAULT_TEMPLATE_CACHE
    
    if _DEFAULT_TEMPLATE_CACHE is not None:
        return _DEFAULT_TEMPLATE_CACHE

    if not os.path.exists(TEMPLATE_FILE_PATH):
        logging.error(f"Template file not found at path: {TEMPLATE_FILE_PATH}")
        # Return a simple fallback if the file is missing to prevent crash
        return "Error: Template file missing. Please configure templates/coverLetter.txt."

    try:
        with open(TEMPLATE_FILE_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
            _DEFAULT_TEMPLATE_CACHE = content
            return content
    except Exception as e:
        logging.error(f"Error reading template file {TEMPLATE_FILE_PATH}: {e}")
        return "Error: Could not read template content."

def fetch_content_from_url(url: str) -> str:
    """
    Simulates loading the main text content from a URL.
    In a real app, this would involve a library like BeautifulSoup
    or LangChain's WebBaseLoader to parse and clean the HTML.
    """
    try:
        # Use a timeout to prevent hanging the worker thread
        response = requests.get(url, timeout=10)
        response.raise_for_status() # Raise exception for bad status codes (4xx or 5xx)
        
        # --- Placeholder for HTML/Job Description Extraction ---
        # In a real application, you would parse 'response.text' here
        # to isolate the actual job description text.
        
        mock_job_description = (
            "Job Title: Senior Data Scientist. Location: Remote. "
            "We are looking for an experienced Data Scientist to join our team. "
            "Requires 5+ years of experience with Python, Pandas, and Scikit-learn. "
            "Must have strong communication skills and experience deploying models with AWS. "
            "Experience with Kubernetes is a huge plus. Agile experience required."
        )
        return mock_job_description
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch content from URL: {e}")