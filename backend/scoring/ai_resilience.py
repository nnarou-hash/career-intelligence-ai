from models.job_offer import JobOffer

def compute_ai_resilience(job: JobOffer) -> int:

    title = job.job_title.lower()

    if "governance" in title:
        return 10

    if "manager" in title:
        return 10

    if "officer" in title:
        return 9

    if "analyst" in title:
        return 7

    return 5
