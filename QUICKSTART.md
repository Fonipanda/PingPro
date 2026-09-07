# Quick Start Guide - PingPro

## Démarrage rapide (5 minutes)

### 1. Configuration Backend

```bash
# Se placer dans le dossier backend
cd backend

# Créer et activer l'environnement virtuel
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell

# Installer les dépendances
pip install -r requirements.txt

# Configurer l'environnement
copy env.example .env
# Éditer .env si besoin (MongoDB, etc.)

# Lancer le serveur
uvicorn server:app --reload --host 0.0.0.0 --port 8080
```

Le backend est maintenant accessible sur **http://localhost:8080**

### 2. Configuration Frontend

```bash
# Ouvrir un nouveau terminal
cd frontend

# Installer les dépendances
npm install --legacy-peer-deps

# Configurer l'environnement
copy env.example .env
# Vérifier que REACT_APP_BACKEND_URL=http://localhost:8080

# Lancer l'application
npm start
```

Le frontend est maintenant accessible sur **http://localhost:3000**

## Lancement depuis PyCharm

1. Ouvrir le projet PingPro dans PyCharm
2. Dans la barre d'outils, vous verrez deux configurations :
   - **Backend Server** - Lance le serveur FastAPI
   - **Frontend Dev Server** - Lance l'application React

3. Cliquer sur ▶️ pour lancer chaque configuration

### Configuration de l'environnement virtuel dans PyCharm

1. File → Settings → Project: PingPro → Python Interpreter
2. Cliquer sur ⚙️ → Add
3. Sélectionner "Existing environment"
4. Naviguer vers `backend\venv\Scripts\python.exe`
5. Cliquer OK

## Problèmes courants

### Backend : "ModuleNotFoundError"
```bash
# Vérifier que l'environnement virtuel est activé
.\venv\Scripts\Activate.ps1

# Réinstaller les dépendances
pip install -r requirements.txt
```

### Frontend : Conflit de dépendances
```bash
# Utiliser legacy-peer-deps
npm install --legacy-peer-deps

# Ou forcer l'installation
npm install --force
```

### Port déjà utilisé
```bash
# Backend - changer le port dans la commande
uvicorn server:app --reload --host 0.0.0.0 --port 8081

# Frontend - définir PORT dans .env
PORT=3001
```

## Test de l'application

1. Backend opérationnel : http://localhost:8080
2. Frontend opérationnel : http://localhost:3000
3. Uploader une vidéo de tennis de table
4. Lancer l'analyse
5. Consulter les résultats

## MongoDB (optionnel)

Si vous n'avez pas MongoDB installé, vous pouvez :

1. **Installer MongoDB Community** : https://www.mongodb.com/try/download/community
2. **Utiliser MongoDB Atlas** (cloud gratuit) : https://www.mongodb.com/cloud/atlas
3. **Lancer avec Docker** :
```bash
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

Puis mettre à jour `backend/.env` :
```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=pingpro
```

## Support

Pour tout problème, vérifier :
- Python 3.10+ est installé
- Node.js 18+ est installé
- Les ports 8080 et 3000 sont libres
- MongoDB est en cours d'exécution (si utilisé)
