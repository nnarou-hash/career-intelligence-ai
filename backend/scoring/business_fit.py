from models.job_offer import JobOffer

def compute_business_fit(job: JobOffer, profile: dict) -> int:
    score = 0

    keywords = profile["experience_keywords"]

    text = (
        job.job_title
        + " "
        + job.sector
        + " "
        + " ".join(job.skills)
    ).lower()

    for keyword in keywords:
        if keyword.lower() in text:
            score += 3

    return min(score, 25)
