from services.job_analyzer import analyze_job
from services.cv_generator import extract_ats_keywords, generate_tailored_cv, generate_cover_letter
from scoring.career_score import compute_career_score

with open("data/job_offer.txt", "r", encoding="utf-8") as file:
    job_description = file.read()

job = analyze_job(job_description)

score = compute_career_score(job)

print("=" * 60)
print("CAREER INTELLIGENCE AI")
print("=" * 60)

print(f"Entreprise : {job.company}")
print(f"Poste : {job.job_title}")
print(f"Secteur : {job.sector}")
print(f"Expérience : {job.experience}")
print(f"Salaire : {job.salary}")

print("\nCompétences")

for skill in job.skills:
    print(f"✓ {skill}")

print("\nScore :", score, "/100")

if score >= 85:
    print("🟢 POSTULER")

    # Guardrail : on ne génère CV/lettre que pour les offres à fort score
    print("\nGénération du CV adapté et de la lettre de motivation...")

    keywords = extract_ats_keywords(job_description)
    cv_adapte = generate_tailored_cv(job_description, keywords)
    lettre = generate_cover_letter(job_description, job.company, job.job_title, keywords)

    print("\n--- CV ADAPTÉ (brouillon, à relire avant envoi) ---")
    print(cv_adapte)

    print("\n--- LETTRE DE MOTIVATION (brouillon, à relire avant envoi) ---")
    print(lettre)

elif score >= 70:
    print("🟡 À ÉTUDIER")

else:
    print("🔴 PASSER")
