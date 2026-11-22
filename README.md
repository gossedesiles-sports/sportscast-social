# Sportscast — visuels réseaux sociaux

Images publiques utilisées par Metricool pour les posts Instagram de Sportscast.

- `atelier.html` : copie de l'Atelier réseaux sociaux (même rendu).
- `plans/<lundi>.json` : le plan de la semaine, écrit par la tâche du lundi.
- `render.py` + `.github/workflows/render.yml` : à chaque nouveau plan, GitHub rend les visuels
  (covers récupérées depuis les flux RSS) dans `images/<lundi>/`, avec `manifest.json`.
- Lien public d'une image : `https://raw.githubusercontent.com/gossedesiles-sports/sportscast-social/main/images/...`

Si l'atelier change, recopier sa nouvelle version dans `atelier.html`.
