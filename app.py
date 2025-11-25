import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from starlette.concurrency import run_in_threadpool

from models import JobPostingAnalysis, AnalysisRequest, CoverLetterRequest
from llm import generate_cover_letter_chain, run_llm_analysis_chain

# Initialize FastAPI App
app = FastAPI(
    title="Applify",
    description="AI-powered job/profile alignment assessment."
)

# Set up CORS (Crucial for the React frontend to communicate with this API)
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy"}

@app.post("/api/v1/analyze-match/", response_model=JobPostingAnalysis)
async def analyze_job_posting(request: AnalysisRequest):
    """
    Takes a job posting URL and returns a structured analysis object
    by running a LangChain pipeline.
    
    Note: The use of run_in_threadpool is VITAL here. It runs the
    blocking, synchronous LLM code in a separate thread, keeping
    FastAPI's main event loop free for high concurrency.
    """
    job_description = request.job_posting_content
    profile_description = request.resume_text or ""

    # 2. Run the heavy LLM analysis
    analysis_result = await run_in_threadpool(run_llm_analysis_chain, job_description, profile_description)

    # 3. Return the result
    return analysis_result

@app.post("/api/v1/generate-cover-letter", 
             response_class=PlainTextResponse,
             status_code=200,
             summary="Generate personalized cover letter using LLM.")
async def generate_cover_letter(request_data: CoverLetterRequest):
    """
    Receives all necessary inputs (Job, Profile, Analysis, Template) and calls the 
    LLM chain to generate a final, personalized cover letter text.
    """
    logging.info("Received request for cover letter generation via app.post.")
    
    if not request_data.job_description or not request_data.profile_content:
        raise HTTPException(
            status_code=400,
            detail="Job description and profile content are required for generation."
        )

    try:
        final_letter_text = await run_in_threadpool(
            generate_cover_letter_chain,
            request_data.job_description,
            request_data.profile_content,
            request_data.analysis_data,
            request_data.template_content
        )
        
        return final_letter_text

    except Exception as e:
        logging.error(f"Error during LLM cover letter generation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate letter due to a service error. Details: {e}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)