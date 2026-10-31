"""Pré-filtre déterministe appliqué AVANT tout appel OpenAI (run_veille.py),
pour ne pas payer l'analyse LLM d'offres qui seraient de toute façon
écartées.

Ne travaille que sur les champs bruts normalisés par sources/*.py
(job_title, location, description, contract_type). Les comparaisons se
font sur le texte normalisé (scoring.normalize : sans casse, accents ni
ponctuation) et par mot entier, pour que "LIMS" ne matche pas "limsoft".

En cas d'information absente (lieu vide, type de contrat inconnu), l'offre
est conservée : on ne rejette que sur un signal explicite.
"""

import re

from scoring.normalize import normalize

MOTIF_SANS_DESCRIPTION = "sans description"
MOTIF_CONTRAT = "contrat exclu (CDD/intérim/alternance/stage)"
MOTIF_LIEU = "hors Île-de-France sans télétravail"
MOTIF_MOT_CLE = "mot-clé éliminatoire"

# Comparés au champ contract_type (codes France Travail : CDD, MIS =
# intérim, SAI = saisonnier, qui est un CDD ; libellés LinkedIn/Indeed en
# anglais ou en français selon l'actor).
CONTRATS_EXCLUS = [
    "cdd", "mis", "sai", "interim", "temporaire", "temporary",
    "alternance", "apprentissage", "stage", "internship",
]

# Comparés à l'intitulé, quand la source ne renseigne pas le contrat.
CONTRATS_EXCLUS_TITRE = [
    "cdd", "interim", "alternance", "alternant", "alternante",
    "apprenti", "apprentie", "apprentissage", "stage", "stagiaire",
]

# Recherchés dans l'intitulé et la description.
MOTS_CLES_ELIMINATOIRES = [
    "management d'équipe",
    "BCBS 239",
    "Kinaxis",
    "LIMS",
    "FuturMaster",
    "Google Analytics",
]

TELETRAVAIL = ["teletravail", "remote", "travail a distance"]

# Départements d'Île-de-France, en code seul ("92 - Nanterre" chez France
# Travail, "Nanterre (92)" chez Indeed) ou en code postal ("92000").
_IDF_DEPARTEMENTS = re.compile(r"\b(75|77|78|91|92|93|94|95)(\d{3})?\b")
_IDF_LIBELLES = ["ile de france", "paris", "idf"]

# Lieux trop vagues pour conclure (souvent des offres à distance).
_LIEUX_INCONNUS = {"", "france"}


def _contains_word(text: str, terms: list[str]) -> str | None:
    """Renvoie le premier terme de `terms` présent comme mot(s) entier(s)
    dans `text` (déjà normalisé), ou None."""
    padded = f" {text} "
    for term in terms:
        if f" {normalize(term)} " in padded:
            return term
    return None


def _is_idf(location: str) -> bool:
    return bool(_IDF_DEPARTEMENTS.search(location)) or any(
        f" {l} " in f" {location} " for l in _IDF_LIBELLES
    )


def rejection_reason(raw: dict) -> str | None:
    """Renvoie le motif de rejet de l'offre brute, ou None si elle doit
    être analysée. Les motifs sont testés dans l'ordre, seul le premier
    est retenu (pour un décompte par motif sans double comptage)."""
    description = normalize(raw.get("description") or "")
    if not description:
        return MOTIF_SANS_DESCRIPTION

    title = normalize(raw.get("job_title") or "")
    contract = normalize(raw.get("contract_type") or "")
    if _contains_word(contract, CONTRATS_EXCLUS) or _contains_word(title, CONTRATS_EXCLUS_TITRE):
        return MOTIF_CONTRAT

    location = normalize(raw.get("location") or "")
    if (
        location not in _LIEUX_INCONNUS
        and not _is_idf(location)
        and not _contains_word(description, TELETRAVAIL)
    ):
        return MOTIF_LIEU

    if _contains_word(f"{title} {description}", MOTS_CLES_ELIMINATOIRES):
        return MOTIF_MOT_CLE

    return None
