"""Stockage des offres scorées dans Firestore, collection "offres".

Dédoublonnage : identifiant de document = SHA1(url + titre + entreprise),
tout en minuscules, pour être stable et insensible à la casse. Une offre
déjà présente dans Firestore n'est pas ré-écrite.

Champs du document : titre, entreprise, lieu, url, source, salary,
description (texte brut complet, tronqué si nécessaire, voir
MAX_DESCRIPTION_BYTES), description_tronquee (bool), date_collecte, et les
6 champs de score (total_score + les 5 sous-scores). La description brute
est conservée pour permettre un re-scoring (`rescore`) sans re-collecter
ni repayer OpenAI.

Authentification via variables d'environnement (jamais en dur) :
- en local : GOOGLE_APPLICATION_CREDENTIALS = chemin vers un fichier de clé
  de service JSON.
- en CI : GOOGLE_APPLICATION_CREDENTIALS_JSON = contenu JSON de la clé,
  stocké en GitHub Secret, écrit dans un fichier temporaire ici même.

Collection annexe "offres_vues" : une entrée minimale (url, score, date)
pour CHAQUE offre scorée, y compris sous MIN_SCORE, qui ne vont pas dans
"offres" (le tableau de bord affiche toute cette collection). Sert
uniquement de mémoire au dédoublonnage, pour ne pas repayer chaque semaine
l'analyse OpenAI des offres faibles. Non lisible côté client (aucune règle
dans firestore.rules), seul le compte de service y accède.

Si aucune des deux n'est configurée, Firestore est ignoré (mode dégradé) :
aucune exception n'est levée, les offres sont simplement non enregistrées.
"""

import hashlib
import logging
import os
import tempfile

logger = logging.getLogger(__name__)

COLLECTION_NAME = "offres"
SEEN_COLLECTION_NAME = "offres_vues"

# Une marge sous la limite Firestore de 1 MiB par document, pour laisser de
# la place aux autres champs du même document.
MAX_DESCRIPTION_BYTES = 900_000

_client = None
_client_init_attempted = False


def compute_offer_id(url: str, title: str, company: str) -> str:
    """SHA1 stable, insensible à la casse, de url+titre+entreprise."""
    raw = f"{url}{title}{company}".strip().lower()
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _truncate_description(description: str) -> tuple[str, bool]:
    """Tronque la description à MAX_DESCRIPTION_BYTES (en octets UTF-8,
    sans couper un caractère multi-octets en deux). Renvoie (texte,
    a_ete_tronquee)."""
    encoded = description.encode("utf-8")
    if len(encoded) <= MAX_DESCRIPTION_BYTES:
        return description, False

    truncated = encoded[:MAX_DESCRIPTION_BYTES].decode("utf-8", errors="ignore")
    return truncated, True


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


def load_known_keys() -> tuple[set[str], set[str]]:
    """Renvoie (ids, urls) de toutes les offres déjà connues, dans
    "offres" et "offres_vues", en une seule lecture par collection
    (projection sur le seul champ url) — au lieu d'un get() par offre.
    Les urls couvrent les documents plus anciens dont l'id avait été
    calculé à partir des champs extraits par le LLM. Renvoie deux
    ensembles vides si Firestore n'est pas configuré (mode dégradé)."""
    client = _get_client()
    if client is None:
        return set(), set()

    ids, urls = set(), set()
    for name in (COLLECTION_NAME, SEEN_COLLECTION_NAME):
        for doc in client.collection(name).select(["url"]).stream():
            ids.add(doc.id)
            url = (doc.to_dict() or {}).get("url")
            if url:
                urls.add(url)

    return ids, urls


def mark_seen(offer_id: str, url: str, total_score: int) -> bool:
    """Mémorise une offre scorée dans "offres_vues" (voir docstring du
    module). Renvoie False sans erreur si Firestore n'est pas configuré."""
    client = _get_client()
    if client is None:
        return False

    from google.cloud import firestore  # sûr : _get_client() a déjà réussi cet import

    client.collection(SEEN_COLLECTION_NAME).document(offer_id).set({
        "url": url,
        "total_score": total_score,
        "date_collecte": firestore.SERVER_TIMESTAMP,
    })
    return True


def save_offer(job: dict, scores: dict, offer_id: str | None = None) -> bool:
    """Enregistre une offre + sa description brute + ses sous-scores dans
    Firestore sous un id stable (SHA1 url+titre+entreprise). `offer_id`
    permet d'imposer l'id calculé en amont sur les champs bruts (voir
    run_veille.py) ; à défaut, il est calculé sur `job`. Renvoie False
    sans erreur si Firestore n'est pas configuré ou si l'offre existe déjà."""
    client = _get_client()
    if client is None:
        return False

    from google.cloud import firestore  # sûr : _get_client() a déjà réussi cet import

    offer_id = offer_id or compute_offer_id(job["link"], job["job_title"], job["company"])
    doc_ref = client.collection(COLLECTION_NAME).document(offer_id)

    if doc_ref.get().exists:
        logger.info("Offre déjà enregistrée, ignorée: %s", offer_id)
        return False

    description, tronquee = _truncate_description(job.get("description", "") or "")
    if tronquee:
        logger.warning(
            "Description tronquée à %d octets pour %s", MAX_DESCRIPTION_BYTES, offer_id
        )

    doc_ref.set({
        "titre": job["job_title"],
        "entreprise": job["company"],
        "lieu": job.get("location", ""),
        "url": job["link"],
        "source": job.get("source", ""),
        "salary": job.get("salary", ""),
        "description": description,
        "description_tronquee": tronquee,
        "total_score": scores["total"],
        "ai_resilience": scores["ai_resilience"],
        "business_fit": scores["business_fit"],
        "career_growth": scores["career_growth"],
        "package": scores["package"],
        "skills": scores["skills"],
        "couverture_bi": scores.get("couverture_bi", 0.0),
        "couverture_gouvernance": scores.get("couverture_gouvernance", 0.0),
        "date_collecte": firestore.SERVER_TIMESTAMP,
    })

    return True


def iter_all_offers():
    """Générateur (offer_id, doc_dict) sur toute la collection "offres".
    N'itère rien si Firestore n'est pas configuré."""
    client = _get_client()
    if client is None:
        return

    for doc in client.collection(COLLECTION_NAME).stream():
        yield doc.id, doc.to_dict()


def update_scores(offer_id: str, scores: dict) -> bool:
    """Met à jour uniquement les champs de score d'un document existant
    (utilisé par la commande `rescore`), sans toucher aux autres champs.
    Renvoie False sans erreur si Firestore n'est pas configuré."""
    client = _get_client()
    if client is None:
        return False

    client.collection(COLLECTION_NAME).document(offer_id).update({
        "total_score": scores["total"],
        "ai_resilience": scores["ai_resilience"],
        "business_fit": scores["business_fit"],
        "career_growth": scores["career_growth"],
        "package": scores["package"],
        "skills": scores["skills"],
        "couverture_bi": scores.get("couverture_bi", 0.0),
        "couverture_gouvernance": scores.get("couverture_gouvernance", 0.0),
    })
    return True
