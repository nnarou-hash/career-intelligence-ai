"""Envoi du rapport hebdomadaire par email (HTML), via Gmail SMTP.

Identifiants via variables d'environnement (jamais en dur) :
- GMAIL_ADDRESS : adresse Gmail expéditrice
- GMAIL_APP_PASSWORD : mot de passe d'application Gmail (pas le mot de
  passe du compte — nécessite la validation en 2 étapes activée)
- REPORT_RECIPIENT : adresse destinataire (par défaut GMAIL_ADDRESS)

Si GMAIL_ADDRESS/GMAIL_APP_PASSWORD ne sont pas configurés, l'envoi est
ignoré (mode dégradé) : aucune exception n'est levée.
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465

# (clé du sous-score, libellé affiché, score max) — triés par poids décroissant.
SUB_SCORE_LABELS = [
    ("skills", "Compétences", 30),
    ("business_fit", "Adéquation métier", 25),
    ("package", "Package", 20),
    ("career_growth", "Évolution", 15),
    ("ai_resilience", "Résilience IA", 10),
]


def _build_job_block(job: dict, scores: dict) -> str:
    sub_rows = "".join(
        f"<tr><td>{label}</td><td>{scores[key]}/{max_value}</td></tr>"
        for key, label, max_value in SUB_SCORE_LABELS
    )

    return f"""
    <div style="margin-bottom:30px;padding:20px;border:1px solid #ddd;border-radius:10px;">
        <h2>{job['company']}</h2>
        <p><strong>{job['job_title']}</strong> — {job.get('location', '')}</p>
        <p>Score global : <strong>{scores['total']}/100</strong></p>
        <table style="border-collapse:collapse;width:100%;">
            {sub_rows}
        </table>
        <p><a href="{job['link']}" target="_blank">Voir l'offre</a></p>
    </div>
    """


def build_html(scored_jobs: list[dict]) -> str:
    """scored_jobs : liste de {"job": dict, "scores": dict}."""
    blocks = "".join(
        _build_job_block(entry["job"], entry["scores"]) for entry in scored_jobs
    )

    return f"""
    <html><body>
        <h1>Career Intelligence AI — Veille hebdomadaire</h1>
        <p>{len(scored_jobs)} offre(s) retenue(s) cette semaine.</p>
        {blocks}
    </body></html>
    """


def send_report(scored_jobs: list[dict]) -> bool:
    """Envoie le rapport HTML par email. Renvoie False sans erreur si Gmail
    n'est pas configuré ou si l'envoi échoue."""
    gmail_address = os.getenv("GMAIL_ADDRESS")
    gmail_app_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_address or not gmail_app_password:
        logger.warning(
            "Gmail non configuré (GMAIL_ADDRESS/GMAIL_APP_PASSWORD absents) "
            "— email non envoyé"
        )
        return False

    recipient = os.getenv("REPORT_RECIPIENT", gmail_address)

    message = MIMEMultipart("alternative")
    message["Subject"] = f"Veille emploi — {len(scored_jobs)} offre(s) retenue(s)"
    message["From"] = gmail_address
    message["To"] = recipient
    message.attach(MIMEText(build_html(scored_jobs), "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(gmail_address, gmail_app_password)
            server.sendmail(gmail_address, recipient, message.as_string())
        return True
    except Exception:
        logger.exception("Échec de l'envoi de l'email via Gmail SMTP")
        return False
