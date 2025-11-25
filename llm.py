from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from models import JobPostingAnalysis
import dotenv

dotenv.load_dotenv()

# --- Setup ---
parser = PydanticOutputParser(pydantic_object=JobPostingAnalysis)
llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)

# 1. Define the Prompt using ChatPromptTemplate (Best Practice)
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are an assistant that analyzes a job posting against a candidate's profile. **Your task is to compare the two documents and return a JSON strictly matching this schema**: {format_instructions}"),
        ("human", "--- Job Description ---\n{job_description}\n\n--- Candidate Profile ---\n{profile_content}") # ADDED PROFILE_CONTENT VARIABLE
    ]
).partial(format_instructions=parser.get_format_instructions())


# 2. Define the Chain using LCEL's pipe operator (|)
# The chain passes the input through the prompt, into the LLM, and then through the parser.
chain = prompt | llm | parser

# --- Execution Function ---
def run_llm_analysis_chain(job_description: str, profile_content: str) -> JobPostingAnalysis:
    """
    Calls an LLM via LangChain (LCEL) to analyze a job description.
    Returns a Pydantic-validated JobPostingAnalysis object.
    """
    # The invoke method replaces .run()
    result = chain.invoke({"job_description": job_description, "profile_content": profile_content}) 
    return result

if __name__ == "__main__":
    sample_job_description = (
        "We are looking for a Data Scientist with experience in Python, "
        "Pandas, and Scikit-learn. The candidate should have at least 5 years "
        "of experience in data analysis and machine learning."
    )
    sample_profile_content = (
        "Experienced Data Analyst (4 years) skilled in R, SQL, and some basic Python scripting. "
        "I have worked on statistical modeling projects but have limited exposure to Scikit-learn."
    )
    
    analysis = run_llm_analysis_chain(
        job_description=sample_job_description,
        profile_content=sample_profile_content
    )
    
    print(analysis.model_dump_json(indent=2))