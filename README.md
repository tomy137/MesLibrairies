# MesLibrairies

Un outil Python pour scraper les nouveautés livres sur [leslibraires.fr](https://www.leslibraires.fr), stocker les résultats dans une base SQLite, et envoyer un rapport hebdomadaire par email.

## Fonctionnalités

- Scraping des livres par auteur depuis leslibraires.fr
- Stockage des livres et auteurs dans une base SQLite
- Envoi d'un rapport hebdomadaire des nouveautés par email
- Utilisable en ligne de commande ou via Docker

## Prérequis

- Python 3.10+ ou Docker
- Un serveur SMTP pour l'envoi d'emails (voir variables d'environnement)

## Installation

### Utilisation locale

```bash
git clone https://github.com/votre-utilisateur/MesLibrairies.git
cd MesLibrairies
pip install -r requirements.txt  # (à créer si besoin)
```

### Utilisation avec Docker

```bash
docker build -t leslibrairies .
docker run --rm -v $(pwd)/books.db:/app/books.db leslibrairies
```

## Variables d'environnement

- `DB_PATH` : Chemin vers la base SQLite (défaut : `books.db`)
- `SOURCE_URL` : URL source (défaut : `https://www.leslibraires.fr`)
- `SMTP_SERVER`, `SMTP_PORT`, `SMTP_LOGIN`, `SMTP_PASSWORD` : Pour l'envoi d'emails

## Utilisation

### Ajouter un auteur

L'ID et le slug sont récupérables dans l'URL de l'auteur quand vous êtes sur le site. 

- https://www.leslibraires.fr/personne/{SLUG}/{ID}/

Exemple : 
- https://www.leslibraires.fr/personne/stephen-king/1949874/

```bash
python main.py add --author_id=1949874 --author_slug=stephen-king
```

### Scraper tous les auteurs de la base

```bash
python main.py refresh
```

### Envoyer le rapport hebdomadaire par email

```bash
python main.py send_report --mail_to=destinataire@email.com
```

### Tout faire (scraper + envoyer le rapport)

```bash
python main.py --mail_to=destinataire@email.com
```

## Initialisation rapide

Un script d'initialisation est fourni pour ajouter une liste d'auteurs :

```bash
bash init_thomas.sh
```

## Structure du projet

```
MesLibrairies/
├── main.py
├── core/
│   ├── db.py
│   ├── mailer.py
│   └── scrapper.py
├── books.db (Automatiquement ajouté)
├── Dockerfile
└── init_thomas.sh
```

## Licence

Ce projet est sous licence [GNU GPL v3](LICENSE).