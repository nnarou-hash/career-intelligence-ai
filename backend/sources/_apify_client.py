"""Petit wrapper commun pour lancer un actor Apify depuis les sources
apify_linkedin.py et apify_indeed.py, sans dupliquer la logique d'appel."""

import logging
import os
from datetime import timedelta

logger = logging.getLogger(__name__)

# call() d'apify-client attend indéfiniment la fin du run si wait_duration
# n'est pas fourni ("It waits indefinitely, unless the wait_duration
# argument is provided.") — c'est ce qui a fait tourner un run pendant 8h
# au lieu de ~10min. Borne de sécurité par actor : au-delà, on considère le
# run comme non terminé et on l'ignore (voir vérification du statut plus
# bas), sans jamais bloquer tout le pipeline.
WAIT_DURATION = timedelta(minutes=5)


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
        from apify_client.errors import ApifyApiError
    except ImportError:
        logger.warning("Le paquet apify-client n'est pas installé — source ignorée")
        return []

    try:
        client = ApifyClient(token)
        run = client.actor(actor_id).call(run_input=run_input, wait_duration=WAIT_DURATION)

        status = _champ(run, "status")
        if status and status != "SUCCEEDED":
            logger.warning(
                "Apify: run de l'actor %s toujours à '%s' après %s — dataset ignoré "
                "(quota dépassé, run lent, ou bloqué)",
                actor_id, status, WAIT_DURATION,
            )
            return []

        dataset_id = _champ(run, "default_dataset_id", "defaultDatasetId")
        if not dataset_id:
            raise RuntimeError(f"dataset introuvable, type reçu : {type(run)}")

        return list(client.dataset(dataset_id).iterate_items())
    except ApifyApiError as e:
        message = str(e)
        if "usage" in message.lower() or "limit" in message.lower():
            logger.error(
                "Apify: quota mensuel dépassé (pas une panne) — source ignorée. "
                "Détail : %s", message,
            )
        else:
            logger.exception("Apify: erreur API pour l'actor %s", actor_id)
        return []
    except Exception:
        logger.exception("Apify: échec de l'exécution de l'actor %s", actor_id)
        return []
