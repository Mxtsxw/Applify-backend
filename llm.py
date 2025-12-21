import os
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from models import JobPostingAnalysis
import dotenv

import logging

from utils import get_default_template
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='app.log')

# Create a custom logger desidgned for LLM operations
LLM_LOGGER = logging.getLogger("llm_logger")
file_handler = logging.FileHandler('llm_operations.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
LLM_LOGGER.addHandler(file_handler)
LLM_LOGGER.setLevel(logging.INFO)

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
    # Invoke the chain with both job description and profile content
    result = chain.invoke({"job_description": job_description, "profile_content": profile_content}) 
    logging.info(f"LLM analysis result: {job_description[:30]}... vs {profile_content[:30]}..., Result: {result}")
    LLM_LOGGER.info(f"LLM analysis completed for job description and profile content\n {job_description}... \n {profile_content}... \n Result: {result}")
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

def generate_cover_letter_chain(
    job_description: str, 
    profile_content: str, 
    analysis_data: JobPostingAnalysis, 
    user_template: str | None,
    language: str = "English"
) -> str:
    """
    Generates a personalized cover letter by contextually integrating job analysis into a template.
    """
    
    # 1. Choose the template source
    template_to_use = user_template if user_template and user_template.strip() else get_default_template()

    # 2. Prepare the data
    analysis_json = analysis_data.model_dump_json(indent=2)

    # 3. Construct the dynamic prompt (The key change is here)
    system_prompt = (
        "You are an expert ghostwriter and consultant. Your primary task is to create a single, cohesive, "
        "highly personalized cover letter. You must use the provided Analysis Data to **contextually adapt** "
        "and **seamlessly integrate** facts about the candidate's match (e.g., matching skills, previous experience and projects,"
        "and growth areas) directly into the flow and sections of the provided template. "
        "Do NOT use brackets or explicit placeholders. The final output must read naturally."
    )

    # The human prompt now emphasizes integration over replacement.

    # --- AI ANALYSIS DATA (Use this for facts and scores) ---
    # {analysis_json.}

    human_prompt = f"""    
    --- JOB DESCRIPTION (Use this for context and requirements) ---
    {job_description}
    
    --- CANDIDATE PROFILE (Use this for professional tone and background) ---
    {profile_content}
    
    --- BASE TEMPLATE (Adapt and integrate the data into this structure) ---
    {template_to_use}

    INSTRUCTIONS:
    1. **Personalize:** Integrate specific matched skills and scores from the AI Analysis into the BASE TEMPLATE text.
    2. **Address Gaps:** If there are 'missingSkills', briefly and positively mention the intent to develop those areas.
    3. **Tone:** Maintain the professional tone of the BASE TEMPLATE.
    4. **Language:** Write the final cover letter strictly in {language}.
    5. **Output:** Return ONLY the final, polished cover letter text.
    """

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", human_prompt)
    ])
    
    # 4. Define and Invoke the chain
    chain = prompt_template | llm
    
    response = chain.invoke({}) 
    
    logging.info(f"Cover letter generated successfully using contextual integration.")
    return response.content