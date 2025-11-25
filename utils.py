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