# Career Intelligence AI 🚀

## Vision

Career Intelligence AI est un assistant IA conçu pour analyser les offres d'emploi et aider les candidats à identifier les opportunités les plus pertinentes en fonction de leurs objectifs de carrière.

L'objectif est d'aller au-delà des simples alertes d'emploi en fournissant une analyse intelligente de chaque offre : adéquation avec le profil, estimation du salaire, potentiel d'évolution, qualité du package et priorisation des candidatures.

---

## Fonctionnalités (MVP)

- Analyse automatique d'une offre d'emploi
- Calcul d'un score de matching
- Explication du score
- Estimation du salaire (si non communiqué)
- Évaluation du potentiel d'évolution
- Priorisation des opportunités
- Notification des offres les plus pertinentes

---

## Roadmap

### Sprint 1
- Analyse d'une offre
- Calcul du score de matching
- Explication du résultat

### Sprint 2
- Collecte automatique des offres
- Déduplication

### Sprint 3
- Tableau de bord
- Historique des offres

### Sprint 4
- Notifications (Telegram / Email)

### Sprint 5
- Statistiques de recherche
- Analyse du marché de l'emploi

---

## Stack technique

- Python
- FastAPI
- n8n
- OpenAI API
- SQLite (MVP)
- GitHub

---

## Architecture

```
Job Boards
      │
      ▼
 Collecteur d'offres
      │
      ▼
 Analyse IA
      │
      ▼
 Scoring Engine
      │
      ▼
 Dashboard
      │
      ▼
 Notifications
```

---

## Objectif

Construire un assistant de carrière capable de recommander les meilleures opportunités en fonction d'un profil utilisateur, de ses critères de rémunération et de ses objectifs professionnels.

---

## Statut

🚧 En cours de développement
