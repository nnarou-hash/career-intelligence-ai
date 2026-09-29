"""Petit wrapper commun pour lancer un actor Apify depuis les sources
apify_linkedin.py et apify_indeed.py, sans dupliquer la logique d'appel."""

import logging
import os
import time
from datetime import timedelta

logger = logging.getLogger(__name__)

# call() d'apify-client attend indéfiniment la fin du run si wait_duration
# n'est pas fourni ("It waits indefinitely, unless the wait_duration
# argument is provided.") — c'est ce qui a fait tourner un run pendant 8h
# au lieu de ~10min. Borne de sécurité par actor : au-delà, on considère le
# run comme non terminé et on l'ignore (voir vérification du statut plus
# bas), sans jamais bloquer tout le pipeline.
WAIT_DURATION = timedelta(minutes=5)

# Budget global cumulé sur l'ensemble des actors Apify (LinkedIn + Indeed,
# tous mots-clés confondus) pour un run de run_veille.py. Avec 11 mots-clés
# x 2 actors x jusqu'à 5min chacun (WAIT_DURATION), le pire cas atteint
# 110min — plus que le timeout du job GitHub Actions. Au-delà de ce budget,
# les exécutions Apify restantes sont abandonnées et le run continue avec
# les autres sources (France Travail) plutôt que de risquer une coupure
# sans aucun résultat.
APIFY_BUDGET_SECONDS = int(os.getenv("APIFY_BUDGET_MINUTES", "30")) * 60

_budget_start: float | None = None
_budget_exhausted_logged = False


def _budget_depasse() -> bool:
    """True si le temps cumulé passé sur les actors Apify dépasse
    APIFY_BUDGET_SECONDS. Démarre le chrono au premier appel."""
    global _budget_start, _budget_exhausted_logged

    if _budget_start is None:
        _budget_start = time.monotonic()
        return False

    if time.monotonic() - _budget_start < APIFY_BUDGET_SECONDS:
        return False

    if not _budget_exhausted_logged:
        logger.error(
            "Apify: budget global de %d min dépassé — exécutions Apify "
            "restantes abandonnées, on continue avec les autres sources",
            APIFY_BUDGET_SECONDS // 60,
        )
        _budget_exhausted_logged = True

    return True


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

    if _budget_depasse():
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
