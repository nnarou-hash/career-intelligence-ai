import logging

from models.job_offer import JobOffer
from scoring.ai_resilience import compute_ai_resilience
from scoring.business_fit import compute_business_fit
from scoring.career_growth import compute_career_growth
from scoring.package_score import compute_package_score
from scoring.skills_score import (
    compute_skills_score,
    compute_coverage_bi,
    compute_coverage_gouvernance,
)

logger = logging.getLogger(__name__)

# Bonus historique pour les entreprises réputées bien payer. Conservé tel
# quel mais non branché dans l'agrégation ci-dessous : les 5 modules déjà
# sommés totalisent 100 (10+25+15+20+30) ; l'ajouter ferait systématiquement
# dépasser le score max. À rebrancher explicitement si besoin (cf. CLAUDE.md).
TOP_PAYING_COMPANIES = [
    # Tech, Data, IA
    "mongodb", "vmware", "oracle", "salesforce", "cisco", "red hat", "adobe",
    "microsoft", "sap", "meta", "google", "alphabet", "apple", "amazon", "aws",
    "datadog", "dataiku", "mistral ai", "criteo", "algolia", "finastra",
    "kyndryl", "nokia", "amadeus", "contentsquare", "snowflake", "databricks",
    "ibm", "servicenow", "sopra steria", "inetum", "doctolib",
    # Conseil
    "mckinsey", "boston consulting group", "bcg", "bain", "kearney",
    "oliver wyman", "roland berger", "advancy", "l.e.k", "kea & partners",
    "sia partners", "capgemini invent", "capgemini", "accenture", "deloitte",
    "pwc", "ey", "kpmg", "forvis mazars", "wavestone", "accuracy",
    # Banque, finance, assurance
    "credit agricole", "bnp paribas", "societe generale", "bpce",
    "credit mutuel", "rothschild", "lazard", "natixis", "goldman sachs",
    "jpmorgan", "morgan stanley", "bank of america", "citi", "hsbc",
    "boursobank", "amundi", "axa", "allianz", "cnp assurances", "covea",
    "groupama", "bpifrance", "banque postale", "euronext",
    "edmond de rothschild", "oddo bhf", "europ assistance",
    # Luxe et cosmetique
    "lvmh", "louis vuitton", "hermes", "kering", "chanel", "l'oreal",
    "christian dior", "richemont", "cartier", "moet hennessy", "clarins",
    "estee lauder", "sephora",
    # Industrie, aero, defense, auto
    "airbus", "thales", "safran", "dassault aviation", "schneider electric",
    "alstom", "valeo", "stellantis", "renault", "michelin", "saint-gobain",
    "vinci", "bouygues", "legrand", "naval group", "mbda", "knds", "nexter",
    "siemens", "honeywell", "arcelormittal", "air liquide", "arkema",
    "forvia", "faurecia", "plastic omnium", "sncf", "ratp", "cma cgm",
    "slb", "schlumberger", "subsea7", "technip energies", "cemex",
    "liebherr",
    # Energie et utilities
    "totalenergies", "edf", "engie", "veolia", "rte", "enedis", "grtgaz",
    # Pharma, sante
    "sanofi", "pfizer", "ipsen", "servier", "novartis", "roche", "gsk",
    "astrazeneca", "boehringer ingelheim", "merck", "johnson & johnson",
    "abbvie", "biomerieux", "boston scientific", "iqvia", "stryker",
    "danone", "pernod ricard",
]


def is_top_paying_company(company_name):
    company_lower = company_name.lower()
    for name in TOP_PAYING_COMPANIES:
        if name in company_lower:
            return True
    return False


def compute_career_score(job: JobOffer, profile: dict) -> dict:
    """Agrège les 5 modules de scoring (résilience IA, adéquation métier,
    évolution de carrière, package, compétences) en un score global /100.

    Retourne le détail complet : {"total": int, "ai_resilience": int,
    "business_fit": int, "career_growth": int, "package": int, "skills": int}.
    """
    sub_scores = {
        "ai_resilience": compute_ai_resilience(job),
        "business_fit": compute_business_fit(job, profile),
        "career_growth": compute_career_growth(job),
        "package": compute_package_score(job, profile),
        "skills": compute_skills_score(job, profile),
    }

    total = sum(sub_scores.values())

    if total > 100:
        logger.warning(
            "career_score total=%s dépasse 100 pour %s / %s — "
            "vérifier les bornes des modules de scoring",
            total, job.company, job.job_title,
        )
        total = min(total, 100)

    return {
        "total": total,
        **sub_scores,
        # Diagnostic (pas sommé dans le total) : équilibre entre les deux
        # familles de compétences derrière le score multiplicatif de
        # skills_score, affiché dans le tableau de bord.
        "couverture_bi": compute_coverage_bi(job),
        "couverture_gouvernance": compute_coverage_gouvernance(job),
    }


def compute_career_score_value(job: JobOffer, profile: dict) -> int:
    """Compatibilité : renvoie uniquement le score global (int), pour les
    appelants (api_server.py, main.py) qui n'ont pas besoin du détail."""
    return compute_career_score(job, profile)["total"]