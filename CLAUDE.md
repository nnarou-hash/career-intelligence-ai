# Career Intelligence AI — architecture

Assistant IA qui analyse des offres d'emploi et priorise les candidatures
selon un profil cible (reconversion BI → Data Governance / Data Stewardship).

Deux modes coexistent et partagent le même cœur de scoring :

- **Mode lot** (`run_veille.py`, à la racine) : automatisé, déclenché par
  `.github/workflows/veille.yml` (cron samedi + `workflow_dispatch`).
- **Mode API / local** (`backend/api_server.py`, `backend/main.py`) :
  usage manuel ou piloté par n8n en local (`start.sh`).

## Pipeline du mode lot

```
GitHub Actions (cron samedi)
  Apify -> LinkedIn        (backend/sources/apify_linkedin.py)
  Apify -> Indeed          (backend/sources/apify_indeed.py)
  France Travail (OAuth2)  (backend/sources/france_travail.py)
        v
  backend/services/job_analyzer.py   (extraction structurée via OpenAI)
        v
  backend/scoring/career_score.py    (agrégation des 5 sous-scores)
        v
  backend/storage/firestore_store.py (dédoublonnage + écriture Firestore)
        v
  backend/notify/email_report.py (Gmail SMTP) + public/index.html (Firebase Hosting)
```

Chaque source de `backend/sources/` est isolée : si elle n'est pas
configurée (variables d'environnement absentes) ou si l'appel échoue, elle
renvoie `[]` sans lever d'exception — `run_veille.py` continue avec les
autres sources. Idem pour Firestore et l'email : en mode dégradé (pas de
clés), le run se termine normalement, simplement rien n'est persisté/envoyé.

## Scoring (`backend/scoring/`) — l'actif principal du projet

5 modules indépendants, chacun `compute_X(job[, profile]) -> int`, dont les
scores max s'additionnent à exactement 100 :

| Module | Clé | Max | Entrée |
|---|---|---|---|
| `skills_score.py` | `skills` | 30 | `job`, `profile["must_have_skills"]` |
| `business_fit.py` | `business_fit` | 25 | `job`, `profile["experience_keywords"]` |
| `package_score.py` | `package` | 20 | `job`, `profile` (non utilisé actuellement) |
| `career_growth.py` | `career_growth` | 15 | `job` |
| `ai_resilience.py` | `ai_resilience` | 10 | `job` |

`career_score.py` est l'agrégateur réel : `compute_career_score(job, profile) -> dict`
appelle les 5 modules ci-dessus et retourne
`{"total": int, "ai_resilience": int, "business_fit": int, "career_growth": int, "package": int, "skills": int}`.
Si la somme dépasse 100 (signe d'un bug dans un module), un `logging.warning`
est émis et le total est plafonné — jamais silencieusement.

`compute_career_score_value(job, profile) -> int` est un wrapper de
compatibilité qui ne renvoie que le total, utilisé par `api_server.py` et
`main.py` pour éviter de les réécrire en profondeur.

`TOP_PAYING_COMPANIES` / `is_top_paying_company()` (bonus +15 historique
pour les entreprises réputées bien payer) sont conservés dans le fichier
mais **non branchés** dans l'agrégation actuelle : aucun des 5 modules ne
tient compte du "prestige" de l'entreprise, et l'ajouter ferait dépasser le
score max de 100 de façon systématique (pas seulement en cas de bug). À
rebrancher explicitement si ce bonus doit revenir.

## Dédoublonnage

Identifiant stable : `SHA1(url + titre + entreprise)`, tout en minuscules
(`backend/storage/firestore_store.compute_offer_id`). Une offre déjà connue
de Firestore n'est ni re-scorée en base ni re-signalée par email la semaine
suivante (voir `firestore_store.offer_exists`). En mode dégradé (Firestore
non configuré), `offer_exists` renvoie toujours `False` : tout est
re-signalé à chaque run, faute de mémoire persistante.

## Conventions d'exécution (répertoire courant)

`backend/services/profile_loader.py` et `backend/models/job_offer.py` ne
dépendent pas du cwd. En revanche :

- `backend/main.py` et l'ancien `data/job_offer.txt` sont **relatifs à la
  racine du dépôt** → lancer avec `PYTHONPATH=backend python backend/main.py`
  depuis la racine.
- `backend/api_server.py` (via `uvicorn`) est lancé avec `cd backend` (voir
  `start.sh`) — `profile_loader.py` résout donc `data/candidate_profile.json`
  par rapport à son propre emplacement de fichier (`os.path.dirname(__file__)`),
  pas par rapport au cwd, pour fonctionner dans les deux cas.
- `run_veille.py` s'exécute depuis la racine du dépôt et ajoute lui-même
  `backend/` à `sys.path` (backend n'est pas un package Python — pas de
  `__init__.py` — ses modules s'importent par chemins absolus internes du
  type `from services.job_analyzer import ...`).

## Variables d'environnement (jamais en dur, `.env` en local / GitHub Secrets en CI)

Voir le tableau complet livré en fin de migration. Résumé des noms :
`OPENAI_API_KEY`, `API_SECRET_KEY`, `APIFY_TOKEN`, `APIFY_LINKEDIN_ACTOR_ID`,
`APIFY_INDEED_ACTOR_ID`, `FRANCE_TRAVAIL_CLIENT_ID`,
`FRANCE_TRAVAIL_CLIENT_SECRET`, `GOOGLE_APPLICATION_CREDENTIALS` (local) /
`GOOGLE_APPLICATION_CREDENTIALS_JSON` (CI), `GMAIL_ADDRESS`,
`GMAIL_APP_PASSWORD`, `REPORT_RECIPIENT`.

## Points connus, à surveiller

- Les identifiants d'actor Apify (`DEFAULT_ACTOR_ID` dans
  `apify_linkedin.py` / `apify_indeed.py`) et les noms de champs lus sur les
  items retournés sont des hypothèses à vérifier contre l'actor réellement
  utilisé — le schéma de sortie varie selon l'actor Apify choisi.
- `profile["red_flags"]` (dans `data/candidate_profile.json`) n'est branché
  dans aucun module de scoring ni d'exclusion à ce jour.
- La collecte LinkedIn/Indeed passe par Apify plutôt que par du scraping
  direct — les conditions d'utilisation de ces plateformes sont un sujet
  géré au niveau du choix de prestataire (Apify), pas dans ce code.
