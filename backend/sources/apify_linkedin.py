"""Collecte d'offres LinkedIn via l'actor Apify curious_coder~linkedin-jobs-scraper.

Le schéma d'entrée (keywords/location/limitPerSource) est vérifié contre la
documentation publique de l'actor : pas d'authentification requise, il
tourne sur les pages de recherche publiques LinkedIn (pas de cookie de
session nécessaire). En revanche, les noms de champs lus sur `item` en
sortie (`descriptionText`, `jobUrl`, etc.) restent une hypothèse à
confirmer sur un run réel — la doc publique ne détaille que l'entrée.
Fixez APIFY_LINKEDIN_ACTOR_ID pour changer d'actor.
"""

import logging
import os

from sources._apify_client import (
    MIN_REMAINING,
    budget_remaining,
    run_apify_actor,
    start_budget,
)

logger = logging.getLogger(__name__)

DEFAULT_ACTOR_ID = "curious_coder~linkedin-jobs-scraper"


def fetch_jobs(keywords: list[str], location: str = "Île-de-France, France") -> list[dict]:
    """Renvoie une liste d'offres brutes normalisées, dédupliquées par lien.

    Une exécution d'actor par mot-clé (pas un seul "OR" groupé), fusionnées
    ensuite : chaque mot-clé a ses propres résultats sur LinkedIn plutôt que
    d'être noyé dans une recherche combinée. Renvoie [] si Apify n'est pas
    configuré (APIFY_TOKEN absent) ou si l'appel échoue. Tous les mots-clés
    partagent un même budget (APIFY_BUDGET_MINUTES) : une fois épuisé, les
    mots-clés restants sont sautés et on renvoie ce qui a déjà été collecté."""
    actor_id = os.getenv("APIFY_LINKEDIN_ACTOR_ID", DEFAULT_ACTOR_ID)

    jobs = []
    seen_links = set()
    deadline = start_budget()

    for i, keyword in enumerate(keywords):
        if budget_remaining(deadline) < MIN_REMAINING:
            logger.warning(
                "%s: budget Apify épuisé, %d mot(s)-clé(s) non interrogé(s)",
                actor_id, len(keywords) - i,
            )
            break

        run_input = {
            "keywords": keyword,
            "location": location,
            "limitPerSource": 50,
        }

        items = run_apify_actor(actor_id, run_input, deadline=deadline)

        for item in items:
            link = item.get("jobUrl") or item.get("link") or item.get("url") or ""
            if link:
                if link in seen_links:
                    continue
                seen_links.add(link)

            jobs.append({
                "source": "linkedin",
                "company": item.get("companyName") or item.get("company") or "",
                "job_title": item.get("title") or item.get("jobTitle") or "",
                "location": item.get("location") or location,
                "description": item.get("descriptionText") or item.get("description") or "",
                "link": link,
                "salary": item.get("salary") or "",
                # Hypothèse de nom de champ (ex. "Full-time", "Internship"),
                # lu par services.prefilter ; vide si absent.
                "contract_type": item.get("employmentType") or item.get("contractType") or "",
            })

    return jobs
