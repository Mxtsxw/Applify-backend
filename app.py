from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from models import JobPostingAnalysis, AnalysisRequest
from llm import run_llm_analysis_chain

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)