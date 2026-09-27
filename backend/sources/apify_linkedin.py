"""Collecte d'offres LinkedIn via l'actor Apify curious_coder~linkedin-jobs-scraper.

Le schéma d'entrée (keywords/location/limitPerSource) est vérifié contre la
documentation publique de l'actor : pas d'authentification requise, il
tourne sur les pages de recherche publiques LinkedIn (pas de cookie de
session nécessaire). En revanche, les noms de champs lus sur `item` en
sortie (`descriptionText`, `jobUrl`, etc.) restent une hypothèse à
confirmer sur un run réel — la doc publique ne détaille que l'entrée.
Fixez APIFY_LINKEDIN_ACTOR_ID pour changer d'actor.
"""

import os

from sources._apify_client import run_apify_actor

DEFAULT_ACTOR_ID = "curious_coder~linkedin-jobs-scraper"


def fetch_jobs(keywords: list[str], location: str = "Île-de-France, France") -> list[dict]:
    """Renvoie une liste d'offres brutes normalisées. Renvoie [] si Apify
    n'est pas configuré (APIFY_TOKEN absent) ou si l'appel échoue."""
    actor_id = os.getenv("APIFY_LINKEDIN_ACTOR_ID", DEFAULT_ACTOR_ID)

    run_input = {
        "keywords": " OR ".join(keywords),
        "location": location,
        "limitPerSource": 50,
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
