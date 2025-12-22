import logging
from app.config import settings
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from app.models.schemas import JobPostingAnalysis
from app.core.logging import llm_logger
from app.config import settings

# LLM Setup
llm = ChatOpenAI(
    model_name="gpt-4o-mini", 
    temperature=0,
    api_key=settings.OPENAI_API_KEY
    )
parser = PydanticOutputParser(pydantic_object=JobPostingAnalysis)


def get_default_template() -> str:
    try:
        with open(settings.DEFAULT_TEMPLATE_PATH, 'r') as f:
            return f.read()
    except:
        return "Dear Hiring Manager, please find my application attached."

def run_analysis(job_description: str, profile_content: str) -> JobPostingAnalysis:

    llm_logger.info("--- ANALYSIS REQUEST STARTED ---")
    llm_logger.info(f"JOB DESCRIPTION:\n{job_description[:]}...")
    llm_logger.info(f"CANDIDATE PROFILE:\n{profile_content[:]}...")

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an assistant that analyzes a job posting against a candidate's profile. Return JSON strictly matching: {format_instructions}"),
        ("human", "--- Job Description ---\n{job_description}\n\n--- Candidate Profile ---\n{profile_content}")
    ]).partial(format_instructions=parser.get_format_instructions())

    chain = prompt | llm | parser
    result = chain.invoke({"job_description": job_description, "profile_content": profile_content})

    llm_logger.info(f"ANALYSIS RESULT:\n{result.model_dump_json()}")
    return result

def generate_cover_letter(job_description: str, profile_content: str, analysis_data: JobPostingAnalysis, user_template: str | None, language: str) -> str:

    print(job_description, profile_content, analysis_data, user_template, language)
    llm_logger.info("--- COVER LETTER GENERATION STARTED ---")
    llm_logger.info(f"ANALYSIS DATA SCORES: {analysis_data.breakdown}")

    template_to_use = user_template if user_template else get_default_template()
    
    system_prompt = (
        "You are an expert ghostwriter. Create a cohesive, highly personalized cover letter. "
        "Contextually adapt facts about the candidate's match into the template flow."
    )
    
    human_prompt = """    
    --- JOB DESCRIPTION ---
    {job_description}
    
    --- CANDIDATE PROFILE ---
    {profile_content}
    
    --- MATCH ANALYSIS ---
    {analysis_json}

    --- BASE TEMPLATE ---
    {template_to_use}

    INSTRUCTIONS:
    1. Integrate matched skills/scores into the template.
    2. Maintain professional tone.
    3. Write strictly in {language}.
    4. Return ONLY the text.
    """

    chain = ChatPromptTemplate.from_messages([
        ("system", system_prompt), 
        ("human", human_prompt)
    ]) | llm
    
    response = chain.invoke({
        "job_description": job_description,
        "profile_content": profile_content,
        "analysis_json": analysis_data.model_dump_json(),
        "template_to_use": template_to_use,
        "language": language
    })

    llm_logger.info(f"COVER LETTER PROMPT:\n{human_prompt[:]}")

    return response.content