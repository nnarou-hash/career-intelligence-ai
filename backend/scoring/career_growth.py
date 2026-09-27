from models.job_offer import JobOffer

def compute_career_growth(job: JobOffer) -> int:

    title = job.job_title.lower()

    if "manager" in title:
        return 15

    if "officer" in title:
        return 13

    if "governance" in title:
        return 15

    return 8
