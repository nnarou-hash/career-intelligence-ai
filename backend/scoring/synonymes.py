"""Dictionnaire de synonymes français/anglais pour business_fit.py et
skills_score.py : un mot-clé du profil compte comme trouvé si lui-même ou
l'un de ses synonymes apparaît dans le texte normalisé de l'offre. À
enrichir au besoin — pas de format figé, juste clé française -> liste de
variantes (anglais, sigles, etc.)."""

from scoring.normalize import normalize

SYNONYMES = {
    "gouvernance des données": ["data governance"],
    "qualité des données": ["data quality"],
    "référentiel": ["master data", "mdm", "repository"],
    "pilotage": ["reporting", "business intelligence", "bi"],
    "tableau de bord": ["dashboard"],
    "prévision de la demande": ["demand planning", "forecasting", "s&op"],
    "responsable de données": ["data owner", "data steward"],
    "catalogue de données": ["data catalog"],
    "traçabilité": ["data lineage"],
    "conformité": ["compliance", "rgpd", "gdpr"],
}


def expand_synonyms(keyword: str) -> set[str]:
    """Renvoie {mot-clé normalisé} ∪ tous ses synonymes connus, dans les
    deux sens (mot-clé = la clé française, ou l'une des variantes)."""
    norm_kw = normalize(keyword)
    variants = {norm_kw}

    for fr_term, variants_list in SYNONYMES.items():
        norm_fr = normalize(fr_term)
        norm_variants = [normalize(v) for v in variants_list]

        if norm_kw == norm_fr or norm_kw in norm_variants:
            variants.add(norm_fr)
            variants.update(norm_variants)

    return variants
