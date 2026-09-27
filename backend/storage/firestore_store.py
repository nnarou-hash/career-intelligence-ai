"""Stockage des offres scorées dans Firestore, collection "offres".

Dédoublonnage : identifiant de document = SHA1(url + titre + entreprise),
tout en minuscules, pour être stable et insensible à la casse. Une offre
déjà présente dans Firestore n'est pas ré-écrite.

Authentification via variables d'environnement (jamais en dur) :
- en local : GOOGLE_APPLICATION_CREDENTIALS = chemin vers un fichier de clé
  de service JSON.
- en CI : GOOGLE_APPLICATION_CREDENTIALS_JSON = contenu JSON de la clé,
  stocké en GitHub Secret, écrit dans un fichier temporaire ici même.

Si aucune des deux n'est configurée, Firestore est ignoré (mode dégradé) :
aucune exception n'est levée, les offres sont simplement non enregistrées.
"""

import hashlib
import logging
import os
import tempfile

logger = logging.getLogger(__name__)

COLLECTION_NAME = "offres"

_client = None
_client_init_attempted = False


def compute_offer_id(url: str, title: str, company: str) -> str:
    """SHA1 stable, insensible à la casse, de url+titre+entreprise."""
    raw = f"{url}{title}{company}".strip().lower()
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _get_client():
    """Renvoie un client Firestore, ou None si les identifiants ne sont pas
    configurés ou si l'initialisation échoue (mode dégradé, ne lève jamais
    d'exception)."""
    global _client, _client_init_attempted

    if _client_init_attempted:
        return _client

    _client_init_attempted = True

    creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if creds_json and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        tmp.write(creds_json)
        tmp.close()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name

    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        logger.warning(
            "Firestore non configuré (GOOGLE_APPLICATION_CREDENTIALS[_JSON] "
            "absent) — les offres ne seront pas enregistrées"
        )
        return None

    try:
        from google.cloud import firestore
        _client = firestore.Client()
    except Exception:
        logger.exception("Firestore: échec de l'initialisation du client")
        _client = None

    return _client


def offer_exists(offer_id: str) -> bool:
    """Renvoie True si l'offre est déjà enregistrée. Renvoie toujours False
    si Firestore n'est pas configuré (mode dégradé : on ne peut pas savoir
    si l'offre a déjà été vue, donc on ne bloque rien)."""
    client = _get_client()
    if client is None:
        return False

    return client.collection(COLLECTION_NAME).document(offer_id).get().exists


def save_offer(job: dict, scores: dict) -> bool:
    """Enregistre une offre + ses sous-scores dans Firestore sous un id
    stable (SHA1 url+titre+entreprise). Renvoie False sans erreur si
    Firestore n'est pas configuré ou si l'offre existe déjà."""
    client = _get_client()
    if client is None:
        return False

    from google.cloud import firestore  # sûr : _get_client() a déjà réussi cet import

    offer_id = compute_offer_id(job["link"], job["job_title"], job["company"])
    doc_ref = client.collection(COLLECTION_NAME).document(offer_id)

    if doc_ref.get().exists:
        logger.info("Offre déjà enregistrée, ignorée: %s", offer_id)
        return False

    doc_ref.set({
        "company": job["company"],
        "job_title": job["job_title"],
        "location": job.get("location", ""),
        "link": job["link"],
        "source": job.get("source", ""),
        "salary": job.get("salary", ""),
        "total_score": scores["total"],
        "ai_resilience": scores["ai_resilience"],
        "business_fit": scores["business_fit"],
        "career_growth": scores["career_growth"],
        "package": scores["package"],
        "skills": scores["skills"],
        "created_at": firestore.SERVER_TIMESTAMP,
    })

    return True
