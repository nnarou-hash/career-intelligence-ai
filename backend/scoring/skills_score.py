from models.job_offer import JobOffer

def compute_skills_score(job: JobOffer, profile: dict) -> int:
    score = 0

    target_skills = profile["must_have_skills"]

    for skill in job.skills:
        score += target_skills.get(skill, 0)

    return min(score, 30)
