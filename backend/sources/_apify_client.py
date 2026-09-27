"""Petit wrapper commun pour lancer un actor Apify depuis les sources
apify_linkedin.py et apify_indeed.py, sans dupliquer la logique d'appel."""

import logging
import os

logger = logging.getLogger(__name__)


def _champ(run, *noms):
    """Lit un champ sur `run`, que ce soit un dict (anciennes versions
    d'apify-client) ou un objet Run/dataclass (versions récentes) — évite
    un TypeError: 'Run' object is not subscriptable."""
    for n in noms:
        if isinstance(run, dict) and n in run:
            return run[n]
        v = getattr(run, n, None)
        if v is not None:
            return v
    return None


def run_apify_actor(actor_id: str, run_input: dict, token_env_var: str = "APIFY_TOKEN") -> list[dict]:
    """Lance un actor Apify et renvoie les items de son dataset par défaut.

    Ne lève jamais d'exception : si le token n'est pas configuré, si le
    paquet apify-client n'est pas installé, ou si l'appel échoue, renvoie
    une liste vide et journalise un avertissement (la source est ignorée,
    le reste du run continue).
    """
    token = os.getenv(token_env_var)
    if not token:
        logger.warning("Apify non configuré (%s absent) — source ignorée", token_env_var)
        return []

    try:
        from apify_client import ApifyClient
    except ImportError:
        logger.warning("Le paquet apify-client n'est pas installé — source ignorée")
        return []

    try:
        client = ApifyClient(token)
        run = client.actor(actor_id).call(run_input=run_input)

        status = _champ(run, "status")
        if status and status != "SUCCEEDED":
            logger.warning(
                "Apify: run de l'actor %s terminé avec le statut %s — dataset ignoré",
                actor_id, status,
            )
            return []

        dataset_id = _champ(run, "default_dataset_id", "defaultDatasetId")
        if not dataset_id:
            raise RuntimeError(f"dataset introuvable, type reçu : {type(run)}")

        return list(client.dataset(dataset_id).iterate_items())
    except Exception:
        logger.exception("Apify: échec de l'exécution de l'actor %s", actor_id)
        return []
