Ce dépôt contient déjà une version fonctionnelle du projet. Ne repars pas de zéro et ne supprime aucun fichier existant. Mon travail de scoring est l'actif principal du projet : il doit être conservé et réutilisé tel quel.

## Étape 1 — inventaire avant toute modification

Commence par lire et me résumer :

- `backend/scoring/` — les cinq modules : `ai_resilience.py`, `business_fit.py`, `career_growth.py`, `package_score.py`, `skills_score.py`, et l'agrégateur `career_score.py`
- `backend/services/` — `job_analyzer.py`, `cv_generator.py`, `profile_loader.py`
- `backend/models/job_offer.py` — la structure de données attendue
- `backend/api_server.py` et `backend/main.py` — les points d'entrée actuels
- `data/candidate_profile.json` et `data/candidate_master_cv.json`

Dis-moi ce que fait chaque module, quelles sont les signatures d'entrée et de sortie du scoring, et quel format d'objet offre le pipeline attend. ATTENDS MA VALIDATION avant d'écrire du code.

## Étape 2 — ce que je veux ajouter

Le projet tourne aujourd'hui en local, déclenché par n8n. Je veux le rendre entièrement automatique, sans serveur à maintenir :

    GitHub Actions (cron samedi)
        Apify  -> LinkedIn
        Apify  -> Indeed
        API France Travail (gratuite, OAuth2 client credentials)
                  v
        backend/scoring/  <- MON scoring existant, reutilise tel quel
                  v
            Firestore (collection "offres")
                  v
        email HTML (Gmail SMTP) + tableau de bord Firebase Hosting

### À créer

| Fichier | Rôle |
|---|---|
| `backend/sources/apify_linkedin.py` | collecte LinkedIn via Apify |
| `backend/sources/apify_indeed.py` | collecte Indeed via Apify |
| `backend/sour| `backend/sour| `backend/sour| `backend/sour| `backend/sour| `backend/storage/firestore_store.py` | écriture et dédoublonnage |
| `backend/notify/email_report.py` | email HTML |
| `run_veille.py` | point d'entrée en lot, à la racine |
| `.github/workflows/veille.yml` | cron samedi + workflow_dispatch |
| `public/index.html` | tableau de bord |
| `firebase.json`, `firestore.rules` | hébergement et règles |

### À conserver intact

`backend/scoring/`, `backend/services/`, `backend/mode`backend/scoring/`, `badaptation y est nécessaire, explique-la-moi avant de la faire.
Garde `api_server.py` fonctionnel pour l'usage local : mode lot et mode API doivent coexister.

## Exigences

Réutilisation du scoring — `run_veille.py` doit appeler mes modules existants, pas réimplémenter une note. Les sous-scores (résilience IA, adéqRéutilisation du volution, package, compétences) doivent être stockés séparément dans Firestore et affichés individuellement dans le tableau de bord et l'email. C'est la finesse de ce scoring qui fait la valeur de l'outil.

Dédoublonnage — identifiant stable par hachage SHA1 de url + titre + entreprise, insensible à la casse. Une offre déjà enregiDédoublonnage — identifiant stable par hachage SHA1 desoDédoublonnage — identifiant stable par hachage SHA1 de url + tit échoue, les autres continuent. Aucune erreDédoublonnage — identifiant stable par hachage SHA1 de url +nement, jamais en dur. `.env` pour le local, GitHub Secrets pour la CI. `.env` ne doit jamais être commité.

Dépendances — `requirements.txt` ne contient que fastapi et uvicorn, il est incomplet. Analyse tous les imports du projet et complète-le.

## Mon profil de recherch## Mon profil de recherch## Mon profil de recherch## Mon profil de recherch## Mon profil de recherch## Mon profil de recherch## Mon profil de recherch## Mon profil de recherch## Mon profil de recherch## Mon profil de recherch## Mon profil de recherch## Mon profil de recherch## Mon profil de recherch## Mon profil de recherch## Mon profil de recherch## Mon profil de recherch#ersion : l'expérience BI est un atout pour la gouvernance
- Je ne vise PAS les postes de DPO ni les postes juridiques
- Intitulés cibles : Data Steward, Data Quality Analyst/Manager, Data Management Analyst, Analyste Data Office, Responsable référentiels/MDM

Vérifie que `data/candidate_profile.json` reflète ce positionnement. Sinon, propose-moi une mise à jour.

Mots-clés par défaut : data steward, data quality, data management, data office, gouvernance des donnéesMots-clés par défaut : data steward, data quality, data management, data office, gouvernance des donnéesMots-clés par défaut : data ste
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -dIn et Indeed interdisent le scraping dans leurs conditions d'u- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - est ce qui contient le coût

## Méthode de travail

1. Crée `CLAUDE.md` résumant l'architecture, pour tes prochaines sessions.
2. Travaille sur la branche courante.
3. Teste réellement avant de me livrer : compilation de tous les modules, validation YAML du workflow, le scoring existant tourne toujours sur `data/job_offer.txt`, deux offres identiques en casse différente produisent le même identifiant, une source non configurée est ignorée sans planter. Montre-moi la sortie de ces tests.
4. Commits atomiques, un par étape logique.
5. Termine par le tableau des secrets et variables GitHub à créer.

Ne me demande aucune clé d'API : le projet doit fonctionner en mode dégradé sans elles.

Si tu trouves un défaut dans ma demande ou dans mon code existant, signale-le plutôt que de le contourner silencieusement.

Réponds en français.
