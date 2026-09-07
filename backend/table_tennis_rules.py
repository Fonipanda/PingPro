"""
Règles officielles du Tennis de Table - FFTT 2025
Basé sur le règlement sportif en vigueur au 1er juillet 2025 (mis à jour 16 janvier 2026)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum


class MatchFormat(Enum):
    """Formats de match officiels (règle 2.12.1)"""
    BEST_OF_3 = 3   # 2 manches pour gagner
    BEST_OF_5 = 5   # 3 manches pour gagner (standard compétition)
    BEST_OF_7 = 7   # 4 manches pour gagner (finales importantes)


@dataclass
class TableDimensions:
    """Dimensions officielles de la table (règle 2.1)"""
    length_m: float = 2.74      # Longueur en mètres
    width_m: float = 1.525      # Largeur en mètres
    height_m: float = 0.76      # Hauteur au-dessus du sol
    net_height_m: float = 0.1525  # Hauteur du filet (15.25 cm)
    line_width_cm: float = 2.0  # Largeur bandes blanches
    center_line_mm: float = 3.0  # Largeur ligne centrale (doubles)


@dataclass
class BallSpecifications:
    """Spécifications officielles de la balle (règle 2.3)"""
    diameter_mm: float = 40.0
    weight_g: float = 2.7
    material: str = "plastique"
    colors: List[str] = None
    
    def __post_init__(self):
        if self.colors is None:
            self.colors = ["blanc", "orange"]


@dataclass
class ServiceRules:
    """Règles du service (règle 2.6)"""
    min_toss_height_cm: float = 16.0  # Hauteur minimum de lancer
    toss_vertical: bool = True         # Lancer vertical sans effet
    hand_open: bool = True             # Paume ouverte et plate
    behind_end_line: bool = True       # Derrière la ligne de fond
    above_table_level: bool = True     # Au-dessus du niveau de la table
    visible_to_receiver: bool = True   # Visible par le relanceur


@dataclass
class ScoringRules:
    """Règles de score (règles 2.10, 2.11, 2.12, 2.13)"""
    points_to_win_game: int = 11          # Points pour gagner une manche
    minimum_lead: int = 2                  # Écart minimum pour gagner
    service_alternation: int = 2           # Alternance service tous les X points
    service_at_deuce: int = 1              # Service à 1 point chacun si 10-10
    deuce_score: Tuple[int, int] = (10, 10)  # Score de "deuce"


@dataclass
class AccelerationRule:
    """Règle d'accélération (règle 2.15)"""
    time_limit_minutes: int = 10      # Durée avant activation
    min_points_to_skip: int = 18      # Si >= 18 points, pas d'accélération
    max_returns_receiver: int = 13    # 13 renvois réussis = point au receveur
    service_per_point: int = 1        # 1 service par point en accélération


class PointOutcome(Enum):
    """Résultats possibles d'un échange (règle 2.10)"""
    SERVICE_FAULT = "service_fault"           # 2.10.1.1 - Service irrégulier
    RETURN_FAULT = "return_fault"             # 2.10.1.2 - Renvoi irrégulier
    BALL_TOUCHED_OTHER = "ball_touched_other" # 2.10.1.3 - Balle touche autre chose
    BALL_OVER_END = "ball_over_end"           # 2.10.1.4 - Balle franchit ligne de fond
    BALL_THROUGH_NET = "ball_through_net"     # 2.10.1.5 - Balle passe à travers filet
    OBSTRUCTION = "obstruction"               # 2.10.1.6 - Obstruction
    DOUBLE_HIT = "double_hit"                 # 2.10.1.7 - Double frappe délibérée
    ILLEGAL_RACKET = "illegal_racket"         # 2.10.1.8 - Face raquette non réglementaire
    TABLE_MOVED = "table_moved"               # 2.10.1.9 - Table déplacée
    NET_TOUCHED = "net_touched"               # 2.10.1.10 - Filet touché
    FREE_HAND_TOUCH = "free_hand_touch"       # 2.10.1.11 - Main libre touche table
    DOUBLES_SEQUENCE = "doubles_sequence"     # 2.10.1.12 - Séquence doubles violée


class LetSituation(Enum):
    """Situations de balle à remettre (règle 2.9)"""
    SERVICE_NET = "service_net"           # 2.9.1.1 - Service touche filet
    RECEIVER_NOT_READY = "not_ready"      # 2.9.1.2 - Receveur pas prêt
    EXTERNAL_INCIDENT = "external"        # 2.9.1.3 - Incident externe
    UMPIRE_INTERRUPTION = "umpire_stop"   # 2.9.1.4 - Arrêt par arbitre


class TableTennisRulesEngine:
    """Moteur de règles pour l'analyse de tennis de table"""
    
    def __init__(self, match_format: MatchFormat = MatchFormat.BEST_OF_5):
        self.match_format = match_format
        self.scoring = ScoringRules()
        self.service = ServiceRules()
        self.table = TableDimensions()
        self.ball = BallSpecifications()
        self.acceleration = AccelerationRule()
    
    def games_to_win_match(self) -> int:
        """Nombre de manches nécessaires pour gagner le match"""
        return (self.match_format.value // 2) + 1
    
    def is_game_won(self, score1: int, score2: int) -> Optional[int]:
        """
        Vérifie si une manche est gagnée
        Retourne 1 si joueur 1 gagne, 2 si joueur 2 gagne, None sinon
        """
        min_to_win = self.scoring.points_to_win_game
        min_lead = self.scoring.minimum_lead
        
        if score1 >= min_to_win and score1 - score2 >= min_lead:
            return 1
        elif score2 >= min_to_win and score2 - score1 >= min_lead:
            return 2
        return None
    
    def is_deuce(self, score1: int, score2: int) -> bool:
        """Vérifie si on est en situation de deuce (10-10 ou plus)"""
        return score1 >= 10 and score2 >= 10
    
    def get_service_count(self, score1: int, score2: int) -> int:
        """Nombre de services avant alternance selon le score"""
        if self.is_deuce(score1, score2):
            return self.scoring.service_at_deuce  # 1 service chacun
        return self.scoring.service_alternation   # 2 services chacun
    
    def who_serves(self, total_points: int, first_server: int = 1) -> int:
        """
        Détermine qui sert basé sur le nombre total de points joués
        Simplifié : ne gère pas le cas deuce automatiquement
        """
        services_per_player = 2
        cycle = services_per_player * 2  # 4 points par cycle complet
        position_in_cycle = total_points % cycle
        
        if position_in_cycle < services_per_player:
            return first_server
        return 3 - first_server  # L'autre joueur
    
    def validate_service_toss(self, toss_height_cm: float) -> Tuple[bool, str]:
        """Valide la hauteur du lancer au service (règle 2.6.2)"""
        if toss_height_cm >= self.service.min_toss_height_cm:
            return True, f"Service valide : lancer de {toss_height_cm:.1f}cm >= {self.service.min_toss_height_cm}cm"
        return False, f"Service irrégulier : lancer de {toss_height_cm:.1f}cm < {self.service.min_toss_height_cm}cm requis"
    
    def calculate_match_progress(
        self,
        games_player1: int,
        games_player2: int,
        current_game_score: Tuple[int, int]
    ) -> Dict:
        """Calcule la progression du match"""
        games_to_win = self.games_to_win_match()
        
        match_winner = None
        if games_player1 >= games_to_win:
            match_winner = 1
        elif games_player2 >= games_to_win:
            match_winner = 2
        
        current_game_winner = self.is_game_won(current_game_score[0], current_game_score[1])
        
        return {
            "match_format": self.match_format.name,
            "games_to_win": games_to_win,
            "games_player1": games_player1,
            "games_player2": games_player2,
            "current_game": {
                "player1": current_game_score[0],
                "player2": current_game_score[1],
                "is_deuce": self.is_deuce(*current_game_score),
                "game_winner": current_game_winner
            },
            "match_winner": match_winner,
            "match_complete": match_winner is not None
        }
    
    def should_activate_acceleration(
        self,
        game_duration_minutes: float,
        total_points: int
    ) -> bool:
        """Vérifie si la règle d'accélération doit être activée (règle 2.15)"""
        if total_points >= self.acceleration.min_points_to_skip:
            return False  # Pas d'accélération si >= 18 points
        return game_duration_minutes >= self.acceleration.time_limit_minutes


STROKE_TYPES_OFFICIAL = {
    'coup_droit': {
        'name': 'Coup droit',
        'english': 'Forehand',
        'abbreviation': 'CD',
        'description': 'Frappe effectuée du côté de la main tenant la raquette'
    },
    'revers': {
        'name': 'Revers',
        'english': 'Backhand',
        'abbreviation': 'RV',
        'description': 'Frappe effectuée du côté opposé à la main tenant la raquette'
    },
    'topspin': {
        'name': 'Top spin',
        'english': 'Topspin',
        'abbreviation': 'TS',
        'description': 'Frappe avec effet lifté (rotation vers l\'avant)'
    },
    'backspin': {
        'name': 'Coupé / Chop',
        'english': 'Backspin / Chop',
        'abbreviation': 'BS',
        'description': 'Frappe avec effet coupé (rotation vers l\'arrière)'
    },
    'sidespin': {
        'name': 'Latéral',
        'english': 'Sidespin',
        'abbreviation': 'SS',
        'description': 'Frappe avec effet latéral'
    },
    'smash': {
        'name': 'Smash',
        'english': 'Smash',
        'abbreviation': 'SM',
        'description': 'Frappe puissante descendante sur balle haute'
    },
    'bloc': {
        'name': 'Bloc',
        'english': 'Block',
        'abbreviation': 'BL',
        'description': 'Renvoi passif d\'une frappe adverse'
    },
    'flip': {
        'name': 'Flip',
        'english': 'Flip',
        'abbreviation': 'FL',
        'description': 'Attaque courte sur balle courte au-dessus de la table'
    },
    'poussette': {
        'name': 'Poussette',
        'english': 'Push',
        'abbreviation': 'PS',
        'description': 'Renvoi coupé court, souvent en remise de service'
    },
    'lob': {
        'name': 'Lob',
        'english': 'Lob',
        'abbreviation': 'LB',
        'description': 'Balle haute défensive avec rotation'
    },
    'contre_top': {
        'name': 'Contre-top',
        'english': 'Counter-loop',
        'abbreviation': 'CT',
        'description': 'Topspin en réponse à un topspin adverse'
    }
}


SERVICE_TYPES_OFFICIAL = {
    'service_court': {
        'name': 'Service court',
        'english': 'Short serve',
        'effect': 'variable',
        'description': 'Service avec 2ème rebond sur la table adverse'
    },
    'service_long': {
        'name': 'Service long',
        'english': 'Long serve',
        'effect': 'variable',
        'description': 'Service rapide vers le fond de table'
    },
    'service_pendulaire': {
        'name': 'Service pendulaire',
        'english': 'Pendulum serve',
        'effect': 'sidespin',
        'description': 'Service avec mouvement latéral du bras'
    },
    'service_marteau': {
        'name': 'Service marteau',
        'english': 'Tomahawk serve',
        'effect': 'sidespin inverse',
        'description': 'Service avec mouvement inverse du pendulaire'
    },
    'service_bombe': {
        'name': 'Service bombe',
        'english': 'Fast long serve',
        'effect': 'topspin',
        'description': 'Service très rapide et lifté'
    },
    'service_fantome': {
        'name': 'Service fantôme',
        'english': 'Ghost serve',
        'effect': 'sans effet apparent',
        'description': 'Service trompeur avec peu ou pas d\'effet'
    }
}


FAULT_TYPES_OFFICIAL = {
    'faute_filet': {
        'name': 'Faute au filet',
        'rule': '2.10.1.5',
        'description': 'Balle ne franchit pas le filet'
    },
    'faute_dehors': {
        'name': 'Faute dehors',
        'rule': '2.10.1.4',
        'description': 'Balle sort des limites de la table'
    },
    'faute_service': {
        'name': 'Faute au service',
        'rule': '2.10.1.1',
        'description': 'Service non réglementaire'
    },
    'double_rebond': {
        'name': 'Double rebond',
        'rule': '2.10.1.2',
        'description': 'Balle rebondit deux fois avant renvoi'
    },
    'obstruction': {
        'name': 'Obstruction',
        'rule': '2.10.1.6',
        'description': 'Joueur fait obstruction à la balle'
    },
    'touche_filet': {
        'name': 'Touche filet',
        'rule': '2.10.1.10',
        'description': 'Joueur touche le filet pendant l\'échange'
    },
    'main_libre_table': {
        'name': 'Main libre sur table',
        'rule': '2.10.1.11',
        'description': 'Main libre touche la surface de jeu'
    }
}
