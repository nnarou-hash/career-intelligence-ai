"""Collecte d'offres Indeed via un actor Apify.

ATTENTION : DEFAULT_ACTOR_ID et les noms de champs lus sur `item` sont des
hypothèses basées sur des actors communautaires courants (ex.
misceres/indeed-scraper) — à vérifier et ajuster selon l'actor réellement
utilisé sur votre compte Apify, dont le schéma de sortie peut différer.
Fixez APIFY_INDEED_ACTOR_ID pour surcharger.
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

DEFAULT_ACTOR_ID = "misceres~indeed-scraper"


def _as_text(value) -> str:
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value or "")


def fetch_jobs(keywords: list[str], location: str = "Île-de-France") -> list[dict]:
    """Renvoie une liste d'offres brutes normalisées, dédupliquées par lien.

    Une exécution d'actor par mot-clé (pas un seul "OR" groupé), fusionnées
    ensuite. Renvoie [] si Apify n'est pas configuré (APIFY_TOKEN absent)
    ou si l'appel échoue. Tous les mots-clés partagent un même budget
    (APIFY_BUDGET_MINUTES) : une fois épuisé, les mots-clés restants sont
    sautés et on renvoie ce qui a déjà été collecté."""
    actor_id = os.getenv("APIFY_INDEED_ACTOR_ID", DEFAULT_ACTOR_ID)

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
            "position": keyword,
            "location": location,
            "country": "FR",
            "maxItems": 50,
        }

        items = run_apify_actor(actor_id, run_input, deadline=deadline)

        for item in items:
            link = item.get("url") or item.get("link") or ""
            if link:
                if link in seen_links:
                    continue
                seen_links.add(link)

            jobs.append({
                "source": "indeed",
                "company": item.get("company") or "",
                "job_title": item.get("positionName") or item.get("title") or "",
                "location": item.get("location") or location,
                "description": item.get("descriptionText") or item.get("description") or "",
                "link": link,
                "salary": item.get("salary") or "",
                # Hypothèse de nom de champ (liste ou chaîne selon l'actor),
                # lu par services.prefilter ; vide si absent.
                "contract_type": _as_text(item.get("jobType")),
            })

    return jobs
