from models.job_offer import JobOffer
from scoring.normalize import normalize

# Positionnement recherché : postes hybrides BI + gouvernance des données,
# pas des postes BI purs ni gouvernance pure. Ces deux listes sont déjà des
# termes "à plat" (pas de recherche de synonymes ici, volontairement — les
# variantes comme "dashboard"/"tableau de bord" ou "MDM"/"data catalog"
# sont déjà énumérées séparément) : réutiliser expand_synonyms()
# réintroduirait le problème identifié sur "bi", qui matche par sous-chaîne
# dans des mots sans rapport ("ambiance", "disponibilité"...).
FAMILLE_BI = [
    "business intelligence",
    "reporting",
    "tableau de bord",
    "dashboard",
    "power bi",
    "sql",
    "indicateurs",
    "kpi",
    "analyse de données",
    "pilotage de la performance",
    "s&op",
    "prévision de la demande",
]

FAMILLE_GOUVERNANCE = [
    "gouvernance des données",
    "data steward",
    "data owner",
    "qualité des données",
    "référentiels",
    "mdm",
    "data catalog",
    "traçabilité",
    "lineage",
    "conformité",
    "rgpd",
    "dictionnaire de données",
    "politique de données",
]


def _couverture(text: str, termes: list[str]) -> float:
    """Fraction des termes de la famille détectés (sous-chaîne directe,
    texte déjà normalisé des deux côtés) dans le texte de l'offre."""
    detectes = sum(1 for terme in termes if normalize(terme) in text)
    return detectes / len(termes)


def compute_coverage_bi(job: JobOffer) -> float:
    return _couverture(normalize(job.description or ""), FAMILLE_BI)


def compute_coverage_gouvernance(job: JobOffer) -> float:
    return _couverture(normalize(job.description or ""), FAMILLE_GOUVERNANCE)


def compute_skills_score(job: JobOffer, profile: dict) -> int:
    """Score multiplicatif (pas additif) : une offre doit couvrir les deux
    familles (BI et gouvernance) pour bien scorer. Une famille à 0 annule
    le score, même si l'autre famille est parfaitement couverte."""
    couverture_bi = compute_coverage_bi(job)
    couverture_gouvernance = compute_coverage_gouvernance(job)

    score = 30 * (couverture_bi * couverture_gouvernance) ** 0.5

    return round(score)
