# PingPro Backend

## Installation rapide

1. **Créer un environnement virtuel**
```bash
python -m venv venv
```

2. **Activer l'environnement**
- Windows PowerShell: `.\venv\Scripts\Activate.ps1`
- Windows CMD: `.\venv\Scripts\activate.bat`
- Linux/Mac: `source venv/bin/activate`

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Configurer les variables d'environnement**
```bash
# Copier le fichier exemple
copy env.example .env

# Éditer .env avec vos valeurs :
# MONGO_URL=mongodb://localhost:27017
# DB_NAME=pingpro
```

5. **Lancer le serveur**
```bash
uvicorn server:app --reload --host 0.0.0.0 --port 8080
```

Le serveur sera accessible sur http://localhost:8080

## Endpoints API

- GET `/` - Page d'accueil
- POST `/api/upload` - Upload de vidéo
- POST `/api/analyze/{video_id}` - Lancer l'analyse
- GET `/api/status/{analysis_id}` - Statut de l'analyse
- GET `/api/results/{analysis_id}` - Résultats
- WS `/ws/realtime/{client_id}` - WebSocket temps réel

## Structure

- `server.py` - API FastAPI principale
- `ttnet_analysis.py` - Analyse vision par ordinateur
- `video_processor.py` - Traitement vidéo et lexique
- `streaming_server.py` - Gestion WebSocket
- `real_time_ttnet_analyzer.py` - Analyseur temps réel
- `tt3d_advanced_analysis.py` - Analyse 3D avancée
