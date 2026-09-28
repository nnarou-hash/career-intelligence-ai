from openai import OpenAI
from dotenv import load_dotenv
from models.job_offer import JobOffer

import json
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
Tu es un expert du recrutement Data.

Analyse cette offre.

Réponds UNIQUEMENT avec un JSON.

{
"company":"",
"job_title":"",
"location":"",
"sector":"",
"experience":"",
"skills":[],
"salary":""
}
"""


def analyze_job(job_description: str) -> JobOffer:
    response = client.responses.create(
        model="gpt-5.6-luna",
        input=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": job_description,
            },
        ],
    )
    data = json.loads(response.output_text)
    # Texte brut conservé pour le scoring (business_fit/skills_score) ; le
    # LLM n'est pas sollicité pour le reproduire, seulement pour en extraire
    # les champs structurés ci-dessus.
    data["description"] = job_description
    return JobOffer(**data)