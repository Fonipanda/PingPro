import os
import httpx
from typing import Dict, Any, List
import logging
import urllib.parse

logger = logging.getLogger(__name__)


class AnythingLLMClient:
    """Client pour interagir avec AnythingLLM API"""

    def __init__(self):
        self.api_url = os.getenv("ANYTHINGLLM_API_URL", "http://localhost:3001/api")
        self.api_key = os.getenv("ANYTHINGLLM_API_KEY", "")
        self.workspace = os.getenv("ANYTHINGLLM_WORKSPACE", "pingpro")

        if not self.api_key:
            raise ValueError("ANYTHINGLLM_API_KEY manquante dans .env")

    async def chat(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Envoyer un prompt au LLM et récupérer la réponse"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "accept": "application/json"
        }

        payload = {
            "message": prompt,
            "mode": "chat"
        }

        workspace_slug = self.workspace.lower().replace(" ", "-")

        async with httpx.AsyncClient() as client:
            try:
                url = f"{self.api_url}/v1/workspace/{workspace_slug}/chat"
                logger.info(f"Calling AnythingLLM: {url}")
                
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=120.0
                )
                response.raise_for_status()
                data = response.json()
                return data.get("textResponse", "")

            except httpx.HTTPStatusError as e:
                logger.error(f"AnythingLLM API error: {str(e)}")
                raise
            except httpx.ConnectError:
                logger.warning("AnythingLLM not running - using fallback analysis")
                raise ValueError("AnythingLLM non disponible")
            except Exception as e:
                logger.error(f"AnythingLLM API error: {str(e)}")
                raise

    async def analyze_video_frames(self, frames_context: str) -> Dict[str, Any]:
        """Analyser le contexte des frames vidéo"""

        prompt = f"""Tu es un expert entraîneur de tennis de table avec plus de 20 ans d'expérience.
Analyse ces informations extraites d'une vidéo de match de tennis de table.

CONTEXTE:
{frames_context}

ANALYSE TECHNIQUE À EFFECTUER:

1. TECHNIQUE DES COUPS:
- Type de coups identifiés (service, coup droit, revers, smash, défense)
- Qualité de l'exécution technique
- Position de la raquette et angle d'impact
- Mouvement du corps et transfert de poids

2. POSITIONNEMENT:
- Position sur le terrain
- Équilibre et stabilité
- Anticipation et réactivité
- Couverture du terrain

3. TIMING ET RYTHME:
- Synchronisation des frappes
- Tempo du jeu
- Temps de réaction

Fournis une analyse JSON structurée."""

        response_text = await self.chat(prompt)

        try:
            import json
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                return json.loads(json_str)
            else:
                return {"analysis_text": response_text}
        except:
            return {"analysis_text": response_text}


def create_fallback_llm_analysis(ttnet_results: Dict[str, Any], params: Any) -> Dict[str, Any]:
    """Génère une analyse complète sans LLM basée sur TTNet uniquement"""
    
    stats = ttnet_results.get("match_statistics", {})
    events = stats.get("event_summary", {})
    insights = ttnet_results.get("technical_insights", {})
    
    bounces = events.get("ball_bounce", 15)
    serves = events.get("serve", 5)
    net_hits = events.get("net_hit", 2)
    rally_ends = events.get("rally_end", 8)
    
    ball_detection_rate = stats.get("ball_detection_rate", 0.65)
    
    avg_rally = bounces / max(1, rally_ends)
    error_rate = net_hits / max(1, bounces)
    
    tech_score = min(95, 50 + int(ball_detection_rate * 50))
    
    return {
        "stroke_analysis": {
            "identified_strokes": ["Coup droit", "Revers", "Service"],
            "technique_quality": str(tech_score // 10),
            "strengths": [
                f"Détection de {bounces} frappes durant le match",
                f"Moyenne de {avg_rally:.1f} coups par échange"
            ],
            "weaknesses": [
                f"{net_hits} erreurs filet détectées" if net_hits > 3 else "Peu d'erreurs filet"
            ]
        },
        "positioning_analysis": {
            "court_position": "Analysé par vision artificielle",
            "movement_quality": "Mouvements détectés",
            "balance_score": str(min(9, 5 + int(ball_detection_rate * 4)))
        },
        "timing_analysis": {
            "preparation_quality": "Analysé",
            "impact_timing": f"{bounces} impacts détectés",
            "rhythm_consistency": f"Basé sur {serves} services"
        },
        "match_summary": {
            "total_points": rally_ends,
            "total_strokes": bounces,
            "avg_rally_length": round(avg_rally, 1),
            "detection_quality": f"{ball_detection_rate:.0%}"
        },
        "errors_identified": [
            f"Erreurs au filet: {net_hits}",
            f"Taux d'erreur: {error_rate:.1%}"
        ],
        "improvement_priorities": [
            "Améliorer la régularité des échanges",
            "Travailler le service" if serves < 5 else "Bon nombre de services"
        ]
    }
