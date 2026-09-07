# PingPro Frontend

## Installation rapide

1. **Installer les dépendances**
```bash
npm install --legacy-peer-deps
# ou
yarn install
```

2. **Configurer l'URL du backend**
```bash
# Copier le fichier exemple
copy env.example .env

# Éditer .env avec :
# REACT_APP_BACKEND_URL=http://localhost:8080
```

3. **Lancer l'application**
```bash
npm start
# ou
yarn start
```

L'application sera accessible sur http://localhost:3000

## Scripts disponibles

- `npm start` - Lancer en mode développement
- `npm build` - Compiler pour production
- `npm test` - Lancer les tests

## Technologies

- React 19
- Tailwind CSS
- shadcn/ui
- Recharts
- React Router
- Lucide React
