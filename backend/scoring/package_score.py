from models.job_offer import JobOffer

def compute_package_score(job: JobOffer, profile: dict) -> int:

    salary = (job.salary or "").lower()

    if "60" in salary or "65" in salary or "70" in salary:
        return 20

    if "55" in salary:
        return 15

    if salary == "":
        return 10

    return 5
