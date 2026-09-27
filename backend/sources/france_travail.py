"""Collecte d'offres via l'API officielle France Travail (ex Pôle Emploi),
gratuite, authentification OAuth2 client_credentials.

Inscription et création d'une application sur https://francetravail.io.
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire"
SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
SCOPE = "api_offresdemploiv2 o2dsoffre"


def _get_access_token() -> str | None:
    client_id = os.getenv("FRANCE_TRAVAIL_CLIENT_ID")
    client_secret = os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET")

    if not client_id or not client_secret:
        logger.warning(
            "France Travail non configuré (FRANCE_TRAVAIL_CLIENT_ID/"
            "FRANCE_TRAVAIL_CLIENT_SECRET absents) — source ignorée"
        )
        return None

    try:
        response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": SCOPE,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()["access_token"]
    except requests.RequestException:
        logger.exception("France Travail: échec de l'authentification OAuth2")
        return None


def fetch_jobs(keywords: list[str]) -> list[dict]:
    """Interroge l'API France Travail pour chaque mot-clé et renvoie une
    liste d'offres brutes normalisées. Renvoie [] sans lever d'exception si
    les identifiants ne sont pas configurés ou si l'appel échoue."""
    token = _get_access_token()
    if not token:
        return []

    headers = {"Authorization": f"Bearer {token}"}
    jobs = []

    for keyword in keywords:
        try:
            response = requests.get(
                SEARCH_URL,
                headers=headers,
                params={"motsCles": keyword, "range": "0-49"},
                timeout=15,
            )
            if response.status_code == 204:
                continue
            response.raise_for_status()
            results = response.json().get("resultats", [])
        except requests.RequestException:
            logger.exception(
                "France Travail: échec de la recherche pour le mot-clé '%s'", keyword
            )
            continue

        for offer in results:
            entreprise = offer.get("entreprise") or {}
            lieu = offer.get("lieuTravail") or {}
            origine = offer.get("origineOffre") or {}
            salaire = offer.get("salaire") or {}

            jobs.append({
                "source": "france_travail",
                "company": entreprise.get("nom") or "",
                "job_title": offer.get("intitule") or "",
                "location": lieu.get("libelle") or "",
                "description": offer.get("description") or "",
                "link": origine.get("urlOrigine") or "",
                "salary": salaire.get("libelle") or "",
            })

    return jobs
