import os
import hashlib

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from services.job_analyzer import analyze_job
from scoring.career_score import compute_career_score


# =========================
# ENVIRONNEMENT
# =========================

load_dotenv()

API_SECRET_KEY = os.getenv("API_SECRET_KEY")


# =========================
# FASTAPI
# =========================

app = FastAPI(
    title="Career Intelligence AI",
    version="1.0.0"
)


# =========================
# CONFIGURATION
# =========================

MAX_JOBS_PER_REPORT = 20
MIN_SCORE = 70


# =========================
# POSTES A EXCLURE
# =========================

EXCLUDED_KEYWORDS = [
    # Technique hors cible
    "data engineer",
    "data scientist",
    "data engineering",

    # Conseil
    "consultant",
    "consultante",
    "consulting",
    "consultant(e)",
    "conseil",

    # Alternance
    "alternance",
    "alternant",
    "alternante",
    "apprentissage",

    # Stage
    "stage",
    "stagiaire"
]


# =========================
# MODELES
# =========================

class RawJob(BaseModel):
    company: str
    job_title: str
    location: Optional[str] = None
    description: str
    link: str


class ReportRequest(BaseModel):
    jobs: List[RawJob]


# =========================
# SECURITE
# =========================

def verify_key(x_api_key):

    if not API_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="API_SECRET_KEY non configurée"
        )

    if x_api_key != API_SECRET_KEY:
        raise HTTPException(
            status_code=401,
            detail="Clé API invalide"
        )


# =========================
# DOUBLONS
# =========================

def dedupe(jobs):

    seen = set()
    unique = []

    for job in jobs:

        link = job["link"]

        key = hashlib.md5(
            link.encode("utf-8")
        ).hexdigest()

        if key not in seen:

            seen.add(key)
            unique.append(job)

    return unique


# =========================
# EXCLUSIONS
# =========================

def is_excluded(title):

    title_lower = title.lower()

    for keyword in EXCLUDED_KEYWORDS:

        if keyword in title_lower:
            return True

    return False


# =========================
# EMAIL
# =========================

def build_job_block(
    company,
    job_title,
    score,
    link
):

    return f"""
    <div style="
        margin-bottom: 30px;
        padding: 20px;
        border: 1px solid #ddd;
        border-radius: 10px;
    ">

        <h2>{company}</h2>

        <p>
            <strong>{job_title}</strong>
        </p>

        <p>
            Score :
            <strong>{score}/100</strong>
        </p>

        <p>
            <a
                href="{link}"
                target="_blank"
            >
                Voir l'offre
            </a>
        </p>

    </div>
    """


def build_html(scored_jobs):

    blocks = []

    for job in scored_jobs:

        blocks.append(
            build_job_block(
                job["company"],
                job["job_title"],
                job["score"],
                job["link"]
            )
        )

    return f"""
    <html>

        <body>

            <h1>
                Career Intelligence AI
            </h1>

            <p>
                Voici les offres les plus pertinentes
                trouvées cette semaine.
            </p>

            <p>
                {len(scored_jobs)}
                offre(s) retenue(s).
            </p>

            {''.join(blocks)}

        </body>

    </html>
    """


# =========================
# HEALTH CHECK
# =========================

@app.get("/health")
def health():

    return {
        "status": "ok"
    }


# =========================
# GENERATE REPORT
# =========================

@app.post("/generate-report")
def generate_report(
    payload: ReportRequest,
    x_api_key: str = Header(None)
):

    # Vérification de la clé
    verify_key(x_api_key)

    # =========================
    # LIMITE MAXIMALE
    # =========================

    if len(payload.jobs) > MAX_JOBS_PER_REPORT:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Maximum {MAX_JOBS_PER_REPORT} "
                "offres par rapport"
            )
        )

    # =========================
    # CONVERSION
    # =========================

    raw_jobs = [
        job.model_dump()
        for job in payload.jobs
    ]

    # =========================
    # SUPPRESSION DES DOUBLONS
    # =========================

    unique_jobs = dedupe(raw_jobs)

    scored_jobs = []

    # =========================
    # ANALYSE DES OFFRES
    # =========================

    for raw in unique_jobs:

        offer = analyze_job(
            raw["description"]
        )

        job_title = (
            offer.job_title
            or raw["job_title"]
        )

        # =========================
        # EXCLUSION
        # =========================

        if is_excluded(job_title):
            continue

        # =========================
        # SCORE
        # =========================

        score = compute_career_score(
            offer
        )

        # =========================
        # AJOUT
        # =========================

        scored_jobs.append({

            "company": (
                offer.company
                or raw["company"]
            ),

            "job_title": job_title,

            "location": (
                offer.location
                or raw["location"]
                or ""
            ),

            "link": raw["link"],

            "score": score
        })

    # =========================
    # TRI
    # =========================

    scored_jobs.sort(
        key=lambda job: job["score"],
        reverse=True
    )

    # =========================
    # FILTRE SCORE
    # =========================

    scored_jobs = [
        job
        for job in scored_jobs
        if job["score"] >= MIN_SCORE
    ]

    # =========================
    # EMAIL
    # =========================

    subject = (
        "Veille emploi - "
        + str(len(scored_jobs))
        + " offres retenues"
    )

    email_html = build_html(
        scored_jobs
    )

    # =========================
    # REPONSE
    # =========================

    return {

        "count": len(scored_jobs),

        "subject": subject,

        "emailHtml": email_html,

        "jobs": scored_jobs
    }