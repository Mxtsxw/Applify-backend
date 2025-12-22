import logging
from app.config import settings
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from app.models.schemas import JobPostingAnalysis

# LLM Setup
llm = ChatOpenAI(
    model_name="gpt-4o-mini", 
    temperature=0,
    api_key=settings.OPENAI_API_KEY
    )
parser = PydanticOutputParser(pydantic_object=JobPostingAnalysis)

DEFAULT_TEMPLATE_PATH = "templates/coverLetter.txt"

def get_default_template() -> str:
    try:
        with open(DEFAULT_TEMPLATE_PATH, 'r') as f:
            return f.read()
    except:
        return "Dear Hiring Manager, please find my application attached."

def run_analysis(job_description: str, profile_content: str) -> JobPostingAnalysis:
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an assistant that analyzes a job posting against a candidate's profile. Return JSON strictly matching: {format_instructions}"),
        ("human", "--- Job Description ---\n{job_description}\n\n--- Candidate Profile ---\n{profile_content}")
    ]).partial(format_instructions=parser.get_format_instructions())

    chain = prompt | llm | parser
    return chain.invoke({"job_description": job_description, "profile_content": profile_content})

def generate_cover_letter(job_description: str, profile_content: str, analysis_data: JobPostingAnalysis, user_template: str | None, language: str) -> str:
    template_to_use = user_template if user_template else get_default_template()
    
    system_prompt = (
        "You are an expert ghostwriter. Create a cohesive, highly personalized cover letter. "
        "Contextually adapt facts about the candidate's match into the template flow."
    )
    
    human_prompt = f"""    
    --- JOB DESCRIPTION ---
    {job_description}
    
    --- CANDIDATE PROFILE ---
    {profile_content}
    
    --- MATCH ANALYSIS ---
    {analysis_data.model_dump_json()}

    --- BASE TEMPLATE ---
    {template_to_use}

    INSTRUCTIONS:
    1. Integrate matched skills/scores into the template.
    2. Maintain professional tone.
    3. Write strictly in {language}.
    4. Return ONLY the text.
    """

    chain = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", human_prompt)]) | llm
    return chain.invoke({}).content