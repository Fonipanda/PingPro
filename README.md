# PingPro - Analyse IA pour Tennis de Table

Application d'analyse vidéo propulsée par l'intelligence artificielle pour améliorer vos performances au tennis de table.

## Fonctionnalités

### Analyse Vidéo
- **Upload de vidéos** : Importez vos vidéos de matchs pour analyse
- **Détection de balle** : Suivi en temps réel de la trajectoire de la balle avec TTNet
- **Analyse technique** : Évaluation des coups (topspin, slice, smash, service)
- **Analyse de positionnement** : Couverture du terrain et déplacements
- **Détection d'événements** : Rebonds, services, coups au filet

### Analyse en Temps Réel
- **Streaming WebSocket** : Analyse en direct via webcam
- **Statistiques live** : Score, durée des échanges, vitesse de balle
- **Visualisation de trajectoire** : Affichage SVG animé du parcours de la balle
- **Événements temps réel** : Notifications instantanées des actions détectées

### Métriques de Performance
- **Score technique** : Consistance et qualité des coups
- **Score de positionnement** : Couverture et équilibre
- **Score de timing** : Précision temporelle des frappes
- **Recommandations IA** : Conseils personnalisés via GPT-4o

## Architecture

```
PingPro/
├── backend/                    # API FastAPI + Analyse IA
│   ├── server.py              # Point d'entrée API principale
│   ├── ttnet_analysis.py      # Analyse vision par ordinateur TTNet
│   ├── video_processor.py     # Traitement vidéo et lexique technique
│   ├── streaming_server.py    # WebSocket pour streaming temps réel
│   ├── real_time_ttnet_analyzer.py  # Analyseur temps réel
│   ├── tt3d_advanced_analysis.py    # Analyse 3D avancée
│   └── requirements.txt       # Dépendances Python
│
├── frontend/                   # Application React
│   ├── src/
│   │   ├── App.js             # Composant principal + pages
│   │   ├── App.css            # Styles et animations
│   │   ├── RealTimeAnalysis.js # Composant analyse temps réel
│   │   ├── components/ui/     # Composants shadcn/ui
│   │   ├── hooks/             # Hooks personnalisés
│   │   └── lib/               # Utilitaires
│   ├── public/
│   └── package.json
│
└── .emergent/                  # Configuration Emergent
```

## Technologies

### Backend
- **FastAPI** - Framework API async haute performance
- **OpenCV** - Traitement d'images et vidéos
- **NumPy** - Calculs numériques
- **PyTorch** - Deep learning (TTNet)
- **MongoDB** - Base de données (Motor async)
- **WebSockets** - Communication temps réel
- **Emergent LLM** - Intégration GPT-4o pour analyse

### Frontend
- **React 19** - Framework UI
- **Tailwind CSS** - Styles utilitaires
- **shadcn/ui** - Composants UI modernes
- **Recharts** - Graphiques et visualisations
- **Lucide React** - Icônes
- **React Router** - Navigation

## Installation

### Prérequis
- Python 3.10+
- Node.js 18+
- MongoDB
- FFmpeg (pour traitement vidéo)

### Backend

```bash
cd backend

# Créer environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
.\venv\Scripts\activate  # Windows

# Installer dépendances
pip install -r requirements.txt

# Configurer variables d'environnement
# Créer fichier .env avec :
# MONGO_URL=mongodb://localhost:27017
# DB_NAME=pingpro

# Lancer le serveur
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend

# Installer dépendances
yarn install
# ou
npm install

# Configurer l'URL du backend
# Créer fichier .env avec :
# REACT_APP_BACKEND_URL=http://localhost:8000

# Lancer l'application
yarn start
# ou
npm start
```

## Utilisation

### Analyse de Vidéo
1. Accédez à la page d'accueil
2. Uploadez une vidéo de match (.mp4, .mov, .avi)
3. Configurez les paramètres d'analyse (côté joueur, niveau)
4. Lancez l'analyse et attendez les résultats
5. Consultez les métriques, graphiques et recommandations

### Analyse Temps Réel
1. Accédez à la page "Analyse en Direct"
2. Sélectionnez votre source vidéo (webcam)
3. Cliquez sur "Démarrer"
4. Visualisez les statistiques en temps réel
5. Consultez les événements détectés

## API Endpoints

### Analyse Vidéo
- `POST /api/upload` - Upload de vidéo
- `POST /api/analyze/{video_id}` - Lancer l'analyse
- `GET /api/status/{analysis_id}` - Statut de l'analyse
- `GET /api/results/{analysis_id}` - Résultats

### Temps Réel
- `WS /ws/realtime/{client_id}` - WebSocket streaming
- `POST /api/recording/start` - Démarrer enregistrement
- `POST /api/recording/stop` - Arrêter enregistrement

## Configuration

### Variables d'environnement Backend
```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=pingpro
```

### Variables d'environnement Frontend
```env
REACT_APP_BACKEND_URL=http://localhost:8000
```

## Algorithmes de Calcul

### Score Technique
- Taux de détection de balle (45%)
- Variété du lexique technique (25%)
- Fluidité de trajectoire (15%)
- Qualité des coups (15%)

### Score de Positionnement
- Score d'équilibre (base)
- Couverture du terrain (+20%)
- Niveau d'activité (+10%)

### Score de Timing
- Durée moyenne des échanges
- Consistance (variance des durées)
- Taux d'erreurs au filet (pénalité)

### Score Global
- Attaque (35%)
- Défense (25%)
- Consistance (25%)
- Variété (15%)

## Design UI

L'interface utilise un design moderne avec :
- **Glassmorphism** : Effets de flou et transparence
- **Animations CSS** : Transitions fluides et feedback visuel
- **Thème sombre** : Fond dégradé slate avec accents colorés
- **Responsive** : Adapté desktop et mobile
- **Accessibilité** : Support `prefers-reduced-motion`

## Licence

Projet privé - Tous droits réservés

## Auteur

PingPro Team
