"""Collecte d'offres Indeed via un actor Apify.

ATTENTION : DEFAULT_ACTOR_ID et les noms de champs lus sur `item` sont des
hypothèses basées sur des actors communautaires courants (ex.
misceres/indeed-scraper) — à vérifier et ajuster selon l'actor réellement
utilisé sur votre compte Apify, dont le schéma de sortie peut différer.
Fixez APIFY_INDEED_ACTOR_ID pour surcharger.
"""

import os

from sources._apify_client import run_apify_actor

DEFAULT_ACTOR_ID = "misceres/indeed-scraper"


def fetch_jobs(keywords: list[str], location: str = "Île-de-France") -> list[dict]:
    """Renvoie une liste d'offres brutes normalisées. Renvoie [] si Apify
    n'est pas configuré (APIFY_TOKEN absent) ou si l'appel échoue."""
    actor_id = os.getenv("APIFY_INDEED_ACTOR_ID", DEFAULT_ACTOR_ID)

    run_input = {
        "position": " OR ".join(keywords),
        "location": location,
        "maxItems": 50,
    }

    items = run_apify_actor(actor_id, run_input)

    jobs = []
    for item in items:
        jobs.append({
            "source": "indeed",
            "company": item.get("company") or "",
            "job_title": item.get("positionName") or item.get("title") or "",
            "location": item.get("location") or location,
            "description": item.get("descriptionText") or item.get("description") or "",
            "link": item.get("url") or item.get("link") or "",
            "salary": item.get("salary") or "",
        })

    return jobs
