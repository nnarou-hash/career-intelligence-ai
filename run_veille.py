"""Point d'entrée batch de la veille emploi automatisée.

Pipeline : collecte (Apify LinkedIn, Apify Indeed, France Travail) ->
analyse (services.job_analyzer, réutilisé tel quel) -> scoring
(scoring.career_score, réutilisé tel quel) -> Firestore (dédoublonnage) ->
email (notify.email_report).

Déclenché par le workflow GitHub Actions `.github/workflows/veille.yml`
(cron du samedi, ou workflow_dispatch manuel).

Isolation des erreurs :
- une source de collecte non configurée ou en échec est ignorée, les
  autres continuent (voir sources/*.py, qui renvoient [] sans exception) ;
- une offre dont l'analyse LLM échoue est ignorée, le run continue ;
- une offre déjà connue de Firestore n'est pas re-signalée par email.
"""

import argparse
import logging
import os
import statistics
import sys

# backend/ n'est pas un package Python (pas de __init__.py) : ses modules
# s'importent entre eux avec des chemins absolus internes (ex.
# `from services.job_analyzer import ...`) en supposant que backend/ est à
# la racine du sys.path — c'est le cas quand on lance uvicorn ou main.py
# depuis backend/. On reproduit ça ici pour ne rien changer à backend/.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

from models.job_offer import JobOffer
from services.job_analyzer import analyze_job
from services.profile_loader import load_candidate_profile
from scoring.career_score import compute_career_score
from scoring.normalize import normalize
from scoring.synonymes import expand_synonyms
from storage import firestore_store
from notify.email_report import send_report
from sources import apify_linkedin, apify_indeed, france_travail

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("run_veille")

DEFAULT_KEYWORDS = [
    "data steward",
    "data quality",
    "data management",
    "data office",
    "gouvernance des données",
    "référentiels données",
    "MDM",
    "business intelligence",
    "BI",
    "S&OP",
    "prévisions",
]

MIN_SCORE = int(os.getenv("MIN_SCORE", 60))

LIEU = os.getenv("LIEU", "Île-de-France")


def _keywords_from_env() -> list[str]:
    raw = os.getenv("MOTS_CLES")
    if not raw:
        return DEFAULT_KEYWORDS
    keywords = [k.strip() for k in raw.split(",") if k.strip()]
    return keywords or DEFAULT_KEYWORDS

# Intitulés hors cible : postes techniques, conseil, alternance/stage, et
# DPO/juridique (positionnement du profil, voir data/candidate_profile.json).
EXCLUDED_KEYWORDS = [
    "data engineer",
    "data scientist",
    "data engineering",
    "consultant",
    "consultante",
    "consulting",
    "consultant(e)",
    "conseil",
    "alternance",
    "alternant",
    "alternante",
    "apprentissage",
    "stage",
    "stagiaire",
    "dpo",
    "délégué à la protection des données",
    "juridique",
    "legal",
    "avocat",
]


def is_excluded(title: str) -> bool:
    title_lower = title.lower()
    return any(keyword in title_lower for keyword in EXCLUDED_KEYWORDS)


SOURCE_FETCHERS = {
    "linkedin": lambda keywords, location: apify_linkedin.fetch_jobs(keywords, location),
    "indeed": lambda keywords, location: apify_indeed.fetch_jobs(keywords, location),
    "france_travail": lambda keywords, location: france_travail.fetch_jobs(keywords),
}


def collect_all_jobs(
    keywords: list[str], location: str, sources: list[str] | None = None
) -> list[dict]:
    """Interroge chaque source indépendamment ; une source qui échoue ou
    n'est pas configurée est ignorée, sans arrêter les autres. `sources`
    restreint à un sous-ensemble de SOURCE_FETCHERS (linkedin/indeed/
    france_travail) ; None = toutes."""
    active_sources = sources or list(SOURCE_FETCHERS)
    all_jobs = []

    for name in active_sources:
        fetch = SOURCE_FETCHERS.get(name)
        if fetch is None:
            logger.warning("Source inconnue ignorée : %s", name)
            continue

        try:
            jobs = fetch(keywords, location)
            logger.info("%s: %d offre(s) collectée(s)", name, len(jobs))
            all_jobs.extend(jobs)
        except Exception:
            logger.exception("%s: échec de la collecte, source ignorée", name)

    return all_jobs


def _debug_print(raw: dict, offer, scores: dict, profile: dict) -> None:
    """Diagnostic --debug-scoring : n'influence aucun score, ne fait que
    reproduire en lecture seule le texte/matching que business_fit.py et
    skills_score.py voient réellement (description complète normalisée +
    synonymes), pour comprendre où les points se perdent."""
    description = raw.get("description", "")
    normalized_text = normalize(description)

    matched_keywords = [
        kw for kw in profile["experience_keywords"]
        if any(v in normalized_text for v in expand_synonyms(kw))
    ]
    matched_skills = [
        s for s in profile["must_have_skills"]
        if any(v in normalized_text for v in expand_synonyms(s))
    ]

    print(f"\n--- {offer.job_title} ({offer.company}) ---")
    print(f"Longueur description brute                : {len(description)} caractères")
    print(f"Texte normalisé (business_fit/skills_score) : {len(normalized_text)} caractères")
    print(
        f"Sous-scores : total={scores['total']} skills={scores['skills']}/30 "
        f"business_fit={scores['business_fit']}/25 package={scores['package']}/20 "
        f"career_growth={scores['career_growth']}/15 ai_resilience={scores['ai_resilience']}/10"
    )
    print(f"Mots-clés profil trouvés (business_fit, avec synonymes) : {matched_keywords or '(aucun)'}")
    print(f"Compétences profil trouvées (skills_score, avec synonymes) : {matched_skills or '(aucune)'}")


def _print_summary(all_scored: list[dict]) -> None:
    """Affiche min/max/médiane des scores, le nombre d'offres >= 60, le
    détail des 5 meilleures, et le nombre d'offres plafonnant à 30/30 sur
    skills_score."""
    if not all_scored:
        print("\nAucune offre scorée sur ce run.")
        return

    totals = [entry["scores"]["total"] for entry in all_scored]
    skills_capped = sum(1 for entry in all_scored if entry["scores"]["skills"] >= 30)

    print(f"\n=== Résumé ({len(all_scored)} offre(s) scorée(s)) ===")
    print(f"Score minimum : {min(totals)}")
    print(f"Score maximum : {max(totals)}")
    print(f"Score médian  : {statistics.median(totals):.1f}")
    print(f"Offres >= 60  : {sum(1 for t in totals if t >= 60)} / {len(totals)}")
    print(f"Offres à 30/30 sur skills_score : {skills_capped} / {len(totals)}")

    top5 = sorted(all_scored, key=lambda e: e["scores"]["total"], reverse=True)[:5]
    print("\n--- Top 5 ---")
    for entry in top5:
        job, scores = entry["job"], entry["scores"]
        print(
            f"{scores['total']:3d}/100  {job['job_title']} ({job['company']})  "
            f"skills={scores['skills']}/30 business_fit={scores['business_fit']}/25 "
            f"package={scores['package']}/20 career_growth={scores['career_growth']}/15 "
            f"ai_resilience={scores['ai_resilience']}/10"
        )


def run(
    keywords: list[str] | None = None,
    debug: bool = False,
    send_email: bool = True,
    store_all: bool = False,
    sources: list[str] | None = None,
) -> list[dict]:
    """store_all=True écrit dans Firestore même les offres sous MIN_SCORE
    (utile pour calibrer le barème sur un jeu complet). send_email=False
    désactive l'envoi du rapport (utile pour une collecte de test).
    `sources` restreint aux sources actives (linkedin/indeed/
    france_travail) ; None = toutes. Renvoie la liste de TOUTES les offres
    scorées (non exclues, non dupliquées), quel que soit le seuil."""
    keywords = keywords or _keywords_from_env()
    profile = load_candidate_profile()

    raw_jobs = collect_all_jobs(keywords, LIEU, sources)
    scored_jobs = []
    all_scored = []
    debug_count = 0

    for raw in raw_jobs:
        if not raw.get("description"):
            continue

        try:
            offer = analyze_job(raw["description"])
        except Exception:
            logger.exception(
                "Analyse échouée pour '%s' (%s), offre ignorée",
                raw.get("job_title"), raw.get("link"),
            )
            continue

        job_title = offer.job_title or raw.get("job_title", "")

        if is_excluded(job_title):
            continue

        link = raw.get("link", "")
        company = offer.company or raw.get("company", "")

        offer_id = firestore_store.compute_offer_id(link, job_title, company)
        if firestore_store.offer_exists(offer_id):
            logger.info("Offre déjà connue, non re-signalée: %s", link)
            continue

        scores = compute_career_score(offer, profile)

        if debug and debug_count < 5:
            _debug_print(raw, offer, scores, profile)
            debug_count += 1

        job = {
            "company": company,
            "job_title": job_title,
            "location": offer.location or raw.get("location", ""),
            "link": link,
            "source": raw.get("source", ""),
            "salary": offer.salary or raw.get("salary", ""),
            "description": raw.get("description", ""),
        }

        all_scored.append({"job": job, "scores": scores})

        if store_all or scores["total"] >= MIN_SCORE:
            firestore_store.save_offer(job, scores)

        if scores["total"] >= MIN_SCORE:
            scored_jobs.append({"job": job, "scores": scores})

    scored_jobs.sort(key=lambda entry: entry["scores"]["total"], reverse=True)

    if send_email:
        send_report(scored_jobs)
    else:
        logger.info("Email désactivé pour ce run (send_email=False)")

    logger.info(
        "Run terminé : %d offre(s) retenue(s) (email) sur %d collectée(s), "
        "%d scorée(s) au total",
        len(scored_jobs), len(raw_jobs), len(all_scored),
    )

    return all_scored


def rescore() -> None:
    """Relit toutes les offres Firestore, recalcule les scores avec la
    logique de scoring actuelle et met à jour les documents. Aucune
    collecte, aucun appel Apify/France Travail/OpenAI — sert à calibrer le
    barème sans frais."""
    profile = load_candidate_profile()
    updated = 0

    for offer_id, doc in firestore_store.iter_all_offers():
        offer = JobOffer(
            company=doc.get("entreprise", ""),
            job_title=doc.get("titre", ""),
            location=doc.get("lieu", ""),
            sector="",
            experience="",
            skills=[],
            salary=doc.get("salary", ""),
            description=doc.get("description", ""),
        )

        scores = compute_career_score(offer, profile)
        firestore_store.update_scores(offer_id, scores)
        updated += 1
        logger.info(
            "Rescoré : %s (%s) -> %d/100", offer.job_title, offer.company, scores["total"]
        )

    logger.info("rescore terminé : %d offre(s) mise(s) à jour", updated)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "rescore"],
        help=(
            "run (défaut) : collecte + scoring + Firestore + email. "
            "rescore : relit Firestore et recalcule les scores, sans collecte."
        ),
    )
    parser.add_argument(
        "--debug-scoring",
        action="store_true",
        help=(
            "Affiche, pour les 5 premières offres analysées, le titre, la "
            "longueur de la description, le détail des 5 sous-scores et les "
            "mots-clés/compétences du profil effectivement trouvés."
        ),
    )
    parser.add_argument(
        "--no-email",
        action="store_true",
        help="Désactive l'envoi du rapport email pour ce run (collecte de test).",
    )
    parser.add_argument(
        "--store-all-scores",
        action="store_true",
        help=(
            "Écrit dans Firestore même les offres sous MIN_SCORE (jeu complet "
            "pour calibrer le barème)."
        ),
    )
    parser.add_argument(
        "--sources",
        type=str,
        default=None,
        help=(
            "Sources actives, séparées par des virgules parmi linkedin, "
            "indeed, france_travail. Défaut : toutes."
        ),
    )
    args = parser.parse_args()

    if args.command == "rescore":
        rescore()
    else:
        sources = (
            [s.strip() for s in args.sources.split(",") if s.strip()]
            if args.sources else None
        )
        all_scored = run(
            debug=args.debug_scoring,
            send_email=not args.no_email,
            store_all=args.store_all_scores,
            sources=sources,
        )
        _print_summary(all_scored)
