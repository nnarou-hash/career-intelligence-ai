"""Collecte d'offres LinkedIn via un actor Apify.

ATTENTION : DEFAULT_ACTOR_ID et les noms de champs lus sur `item` sont des
hypothèses basées sur des actors communautaires courants (ex.
bebity/linkedin-jobs-scraper) — à vérifier et ajuster selon l'actor
réellement utilisé sur votre compte Apify, dont le schéma de sortie peut
différer. Fixez APIFY_LINKEDIN_ACTOR_ID pour surcharger.
"""

import os

from sources._apify_client import run_apify_actor

DEFAULT_ACTOR_ID = "bebity/linkedin-jobs-scraper"


def fetch_jobs(keywords: list[str], location: str = "Île-de-France, France") -> list[dict]:
    """Renvoie une liste d'offres brutes normalisées. Renvoie [] si Apify
    n'est pas configuré (APIFY_TOKEN absent) ou si l'appel échoue."""
    actor_id = os.getenv("APIFY_LINKEDIN_ACTOR_ID", DEFAULT_ACTOR_ID)

    run_input = {
        "title": " OR ".join(keywords),
        "location": location,
        "rows": 50,
    }

    items = run_apify_actor(actor_id, run_input)

    jobs = []
    for item in items:
        jobs.append({
            "source": "linkedin",
            "company": item.get("companyName") or item.get("company") or "",
            "job_title": item.get("title") or item.get("jobTitle") or "",
            "location": item.get("location") or location,
            "description": item.get("descriptionText") or item.get("description") or "",
            "link": item.get("jobUrl") or item.get("link") or item.get("url") or "",
            "salary": item.get("salary") or "",
        })

    return jobs
