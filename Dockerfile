FROM python:3.11-slim

WORKDIR /app

# Installer les dépendances système nécessaires pour BeautifulSoup et requests
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copier le script dans le conteneur
COPY main.py .
COPY core/ core/


# Installer les dépendances Python
RUN pip install --no-cache-dir requests beautifulsoup4 pendulum loguru

# Définir la commande par défaut
CMD ["python", "main.py"]


# Pour exécuter ce conteneur avec un montage du fichier de base de données local (par exemple, bdd.sqlite) dans le conteneur :
# Remplacez /chemin/vers/bdd.sqlite par le chemin réel sur votre machine hôte
# Le fichier sera monté dans /app/bdd.sqlite dans le conteneur

# Commande à utiliser :
# docker run --rm -v /chemin/vers/bdd.sqlite:/app/bdd.sqlite leslibrairies