from models.job_offer import JobOffer
from scoring.normalize import normalize
from scoring.synonymes import expand_synonyms

def compute_business_fit(job: JobOffer, profile: dict) -> int:
    score = 0

    keywords = profile["experience_keywords"]

    text = normalize(job.description or "")

    for keyword in keywords:
        variants = expand_synonyms(keyword)
        if any(variant in text for variant in variants):
            score += 3

    return min(score, 25)
