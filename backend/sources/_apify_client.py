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

# Budget total par actor, partagé entre tous ses mots-clés (une exécution
# d'actor par mot-clé) : sans lui, 11 mots-clés x WAIT_DURATION pouvaient
# occuper un actor lent pendant ~55 min. Une fois épuisé, les mots-clés
# restants de cet actor sont sautés ; les autres sources ne sont pas
# affectées (elles ont leur propre budget, et run_veille les interroge en
# parallèle).
APIFY_BUDGET_MINUTES = float(os.getenv("APIFY_BUDGET_MINUTES", 8))

# En dessous de ce temps restant, un nouveau run n'aurait pas le temps
# d'aboutir : inutile de le lancer (et de le payer).
MIN_REMAINING = timedelta(seconds=30)


def start_budget() -> float:
    """Échéance (time.monotonic) du budget APIFY_BUDGET_MINUTES d'un actor,
    à passer à run_apify_actor / budget_remaining."""
    return time.monotonic() + APIFY_BUDGET_MINUTES * 60


def budget_remaining(deadline: float) -> timedelta:
    return timedelta(seconds=max(0.0, deadline - time.monotonic()))


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


def run_apify_actor(
    actor_id: str,
    run_input: dict,
    token_env_var: str = "APIFY_TOKEN",
    deadline: float | None = None,
) -> list[dict]:
    """Lance un actor Apify et renvoie les items de son dataset par défaut.

    `deadline` (voir start_budget) borne l'attente à ce qu'il reste du
    budget de l'actor, et arrête aussi le run côté Apify (run_timeout) pour
    qu'il ne continue pas à consommer du crédit après qu'on l'a abandonné.

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

    wait = WAIT_DURATION
    if deadline is not None:
        wait = min(WAIT_DURATION, budget_remaining(deadline))
        if wait < MIN_REMAINING:
            logger.warning(
                "Apify: budget de %s min épuisé pour l'actor %s — run non lancé",
                APIFY_BUDGET_MINUTES, actor_id,
            )
            return []

    try:
        client = ApifyClient(token)
        run = client.actor(actor_id).call(
            run_input=run_input, wait_duration=wait, run_timeout=wait
        )

        status = _champ(run, "status")
        if status and status != "SUCCEEDED":
            logger.warning(
                "Apify: run de l'actor %s toujours à '%s' après %s — dataset ignoré "
                "(quota dépassé, run lent, ou bloqué)",
                actor_id, status, wait,
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
