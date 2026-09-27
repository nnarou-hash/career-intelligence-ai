from models.job_offer import JobOffer

TOP_PAYING_COMPANIES = [
    # Tech, Data, IA
    "mongodb", "vmware", "oracle", "salesforce", "cisco", "red hat", "adobe",
    "microsoft", "sap", "meta", "google", "alphabet", "apple", "amazon", "aws",
    "datadog", "dataiku", "mistral ai", "criteo", "algolia", "finastra",
    "kyndryl", "nokia", "amadeus", "contentsquare", "snowflake", "databricks",
    "ibm", "servicenow", "sopra steria", "inetum", "doctolib",
    # Conseil
    "mckinsey", "boston consulting group", "bcg", "bain", "kearney",
    "oliver wyman", "roland berger", "advancy", "l.e.k", "kea & partners",
    "sia partners", "capgemini invent", "capgemini", "accenture", "deloitte",
    "pwc", "ey", "kpmg", "forvis mazars", "wavestone", "accuracy",
    # Banque, finance, assurance
    "credit agricole", "bnp paribas", "societe generale", "bpce",
    "credit mutuel", "rothschild", "lazard", "natixis", "goldman sachs",
    "jpmorgan", "morgan stanley", "bank of america", "citi", "hsbc",
    "boursobank", "amundi", "axa", "allianz", "cnp assurances", "covea",
    "groupama", "bpifrance", "banque postale", "euronext",
    "edmond de rothschild", "oddo bhf", "europ assistance",
    # Luxe et cosmetique
    "lvmh", "louis vuitton", "hermes", "kering", "chanel", "l'oreal",
    "christian dior", "richemont", "cartier", "moet hennessy", "clarins",
    "estee lauder", "sephora",
    # Industrie, aero, defense, auto
    "airbus", "thales", "safran", "dassault aviation", "schneider electric",
    "alstom", "valeo", "stellantis", "renault", "michelin", "saint-gobain",
    "vinci", "bouygues", "legrand", "naval group", "mbda", "knds", "nexter",
    "siemens", "honeywell", "arcelormittal", "air liquide", "arkema",
    "forvia", "faurecia", "plastic omnium", "sncf", "ratp", "cma cgm",
    "slb", "schlumberger", "subsea7", "technip energies", "cemex",
    "liebherr",
    # Energie et utilities
    "totalenergies", "edf", "engie", "veolia", "rte", "enedis", "grtgaz",
    # Pharma, sante
    "sanofi", "pfizer", "ipsen", "servier", "novartis", "roche", "gsk",
    "astrazeneca", "boehringer ingelheim", "merck", "johnson & johnson",
    "abbvie", "biomerieux", "boston scientific", "iqvia", "stryker",
    "danone", "pernod ricard",
]


def is_top_paying_company(company_name):
    company_lower = company_name.lower()
    for name in TOP_PAYING_COMPANIES:
        if name in company_lower:
            return True
    return False


def compute_career_score(job: JobOffer):
    score = 0
    skills = " ".join(job.skills).lower()
    title = job.job_title.lower()
    sector = job.sector.lower()

    if "governance" in skills:
        score += 20
    if "gouvernance" in skills:
        score += 20
    if "data management" in skills:
        score += 15
    if "gestion des données" in skills:
        score += 15
    if "quality" in skills:
        score += 15
    if "qualité" in skills:
        score += 15
    if "sql" in skills:
        score += 15
    if "power bi" in skills:
        score += 15
    if "reporting" in skills:
        score += 10
    if "coordination" in skills:
        score += 10
    if "business intelligence" in skills:
        score += 10
    if "manager" in title:
        score += 5
    if "officer" in title:
        score += 5
    if "banque" in sector:
        score += 5
    if "luxe" in sector:
        score += 5
    if "transport" in sector:
        score += 5

    if is_top_paying_company(job.company):
        score += 15

    return min(score, 100)