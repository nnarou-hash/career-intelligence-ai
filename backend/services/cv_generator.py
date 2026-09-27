"""
cv_generator.py

Service qui génère, pour une offre d'emploi donnée, un CV adapté et une
lettre de motivation à partir du CV maître (data/candidate_master_cv.json).

À appeler uniquement pour les offres qui dépassent le seuil de Career Score,
là où ce score est déjà calculé (main.py).
"""

from openai import OpenAI
from dotenv import load_dotenv

import json
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = "gpt-5.6-luna"  # même modèle que job_analyzer.py
MASTER_CV_PATH = "data/candidate_master_cv.json"

EXTRACT_KEYWORDS_SYSTEM_PROMPT = """
Tu es un expert ATS (Applicant Tracking System) et recrutement Data.
Réponds UNIQUEMENT avec un JSON.

{
"keywords_ats": [],
"competences_requises": [],
"niveau_experience": "",
"ton_entreprise": "",
"priorites_poste": []
}
"""

GENERATE_CV_SYSTEM_PROMPT = """
Tu es un rédacteur CV spécialisé en reconversion Data Governance.
Tu génères une version adaptée d'un CV maître à partir d'une offre d'emploi.
Réordonne les expériences les plus pertinentes en premier.
Reformule les bullet points pour intégrer les mots-clés ATS fournis, sans jamais inventer de fait.
Garde le format 2 pages.
Réponds en Markdown structuré (sections : Résumé, Expériences, Compétences, Certifications).
"""

GENERATE_LETTER_SYSTEM_PROMPT = """
Tu es un rédacteur spécialisé en lettres de motivation pour la reconversion en Data Governance.
Ton professionnel, pas de superlatifs excessifs.
Relie 2-3 expériences concrètes du candidat (pas toutes) aux priorités du poste.
Présente la reconversion BI vers Data Governance comme une continuité, pas une rupture.
Pas de formule de politesse générique en ouverture ("Je me permets de vous contacter...").
Termine par une phrase d'ouverture à l'échange, sans excès d'enthousiasme.
Longueur : 150-200 mots.
"""


def load_master_cv() -> dict:
    with open(MASTER_CV_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_ats_keywords(job_description: str) -> dict:
    """Analyse l'offre et extrait mots-clés ATS, compétences requises,
    niveau d'expérience et priorités du poste."""
    response = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": EXTRACT_KEYWORDS_SYSTEM_PROMPT},
            {"role": "user", "content": job_description},
        ],
    )
    return json.loads(response.output_text)


def generate_tailored_cv(job_description: str, extracted_keywords: dict) -> str:
    """Génère une version du CV adaptée à l'offre, en Markdown."""
    master_cv = load_master_cv()
    user_content = f"""CV maître (JSON) : {json.dumps(master_cv, ensure_ascii=False)}
Offre analysée : {job_description}
Mots-clés ATS : {json.dumps(extracted_keywords, ensure_ascii=False)}"""

    response = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": GENERATE_CV_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    return response.output_text


def generate_cover_letter(
    job_description: str, company: str, job_title: str, extracted_keywords: dict
) -> str:
    """Génère une lettre de motivation courte et personnalisée pour l'offre."""
    master_cv = load_master_cv()
    user_content = f"""CV maître (JSON) : {json.dumps(master_cv, ensure_ascii=False)}
Offre : {job_description}
Entreprise : {company} | Poste : {job_title}
Priorités du poste : {extracted_keywords.get('priorites_poste')}"""

    response = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": GENERATE_LETTER_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    return response.output_text
