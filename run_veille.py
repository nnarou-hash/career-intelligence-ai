"""Point d'entrée batch de la veille emploi automatisée.

Pipeline : collecte (Apify LinkedIn, Apify Indeed, France Travail) ->
analyse (services.job_analyzer, réutilisé tel quel) -> scoring
(scoring.career_score, réutilisé tel quel) -> Firestore (dédoublonnage) ->
email (notify.email_report).

Déclenché par le workflow GitHub Actions `.github/workflows/veille.yml`
(cron du samedi, ou workflow_dispatch manuel).

Isolation des erreurs :
- une source de collecte non configurée ou en échec est ignorée, les
  autres continuent (voir sources/*.py, qui renvoient [] sans exception) ;
- une offre dont l'analyse LLM échoue est ignorée, le run continue ;
- une offre déjà connue de Firestore n'est pas re-signalée par email.
"""

import logging
import os
import sys

# backend/ n'est pas un package Python (pas de __init__.py) : ses modules
# s'importent entre eux avec des chemins absolus internes (ex.
# `from services.job_analyzer import ...`) en supposant que backend/ est à
# la racine du sys.path — c'est le cas quand on lance uvicorn ou main.py
# depuis backend/. On reproduit ça ici pour ne rien changer à backend/.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

from services.job_analyzer import analyze_job
from services.profile_loader import load_candidate_profile
from scoring.career_score import compute_career_score
from storage import firestore_store
from notify.email_report import send_report
from sources import apify_linkedin, apify_indeed, france_travail

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("run_veille")

DEFAULT_KEYWORDS = [
    "data steward",
    "data quality",
    "data management",
    "data office",
    "gouvernance des données",
]

MIN_SCORE = 70

# Intitulés hors cible : postes techniques, conseil, alternance/stage, et
# DPO/juridique (positionnement du profil, voir data/candidate_profile.json).
EXCLUDED_KEYWORDS = [
    "data engineer",
    "data scientist",
    "data engineering",
    "consultant",
    "consultante",
    "consulting",
    "consultant(e)",
    "conseil",
    "alternance",
    "alternant",
    "alternante",
    "apprentissage",
    "stage",
    "stagiaire",
    "dpo",
    "délégué à la protection des données",
    "juridique",
    "legal",
    "avocat",
]


def is_excluded(title: str) -> bool:
    title_lower = title.lower()
    return any(keyword in title_lower for keyword in EXCLUDED_KEYWORDS)


def collect_all_jobs(keywords: list[str]) -> list[dict]:
    """Interroge chaque source indépendamment ; une source qui échoue ou
    n'est pas configurée est ignorée, sans arrêter les autres."""
    all_jobs = []

    sources = (
        ("Apify LinkedIn", lambda: apify_linkedin.fetch_jobs(keywords)),
        ("Apify Indeed", lambda: apify_indeed.fetch_jobs(keywords)),
        ("France Travail", lambda: france_travail.fetch_jobs(keywords)),
    )

    for source_name, fetch in sources:
        try:
            jobs = fetch()
            logger.info("%s: %d offre(s) collectée(s)", source_name, len(jobs))
            all_jobs.extend(jobs)
        except Exception:
            logger.exception("%s: échec de la collecte, source ignorée", source_name)

    return all_jobs


def run(keywords: list[str] | None = None) -> list[dict]:
    keywords = keywords or DEFAULT_KEYWORDS
    profile = load_candidate_profile()

    raw_jobs = collect_all_jobs(keywords)
    scored_jobs = []

    for raw in raw_jobs:
        if not raw.get("description"):
            continue

        try:
            offer = analyze_job(raw["description"])
        except Exception:
            logger.exception(
                "Analyse échouée pour '%s' (%s), offre ignorée",
                raw.get("job_title"), raw.get("link"),
            )
            continue

        job_title = offer.job_title or raw.get("job_title", "")

        if is_excluded(job_title):
            continue

        link = raw.get("link", "")
        company = offer.company or raw.get("company", "")

        offer_id = firestore_store.compute_offer_id(link, job_title, company)
        if firestore_store.offer_exists(offer_id):
            logger.info("Offre déjà connue, non re-signalée: %s", link)
            continue

        scores = compute_career_score(offer, profile)

        if scores["total"] < MIN_SCORE:
            continue

        job = {
            "company": company,
            "job_title": job_title,
            "location": offer.location or raw.get("location", ""),
            "link": link,
            "source": raw.get("source", ""),
            "salary": offer.salary or raw.get("salary", ""),
        }

        firestore_store.save_offer(job, scores)
        scored_jobs.append({"job": job, "scores": scores})

    scored_jobs.sort(key=lambda entry: entry["scores"]["total"], reverse=True)

    send_report(scored_jobs)

    logger.info(
        "Run terminé : %d offre(s) retenue(s) sur %d collectée(s)",
        len(scored_jobs), len(raw_jobs),
    )

    return scored_jobs


if __name__ == "__main__":
    run()
