"""Normalisation de texte partagée par business_fit.py et skills_score.py,
appliquée des deux côtés (texte de l'offre et mots-clés du profil) pour que
la comparaison ne dépende ni de la casse, ni des accents, ni de la
ponctuation. Ex. : "Data-Gouvernance" et "data gouvernance" normalisent
tous deux vers "data gouvernance".
"""

import re
import unicodedata


def normalize(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
