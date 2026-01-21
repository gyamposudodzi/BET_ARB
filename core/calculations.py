import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from config.settings import settings

@dataclass
class ArbitrageOpportunity:
    event_id: int
    sport_key: str
    market_type: str
    outcomes: List[Dict]  # [{"bookmaker": name, "outcome": type, "odds": decimal}]
    profit_percentage: float
    stake_allocations: Dict[str, float]  # bookmaker_outcome: stake_amount
    total_investment: float
    guaranteed_return: float
    
    def to_dict(self):
        return {
            "event_id": self.event_id,
            "sport_key": self.sport_key,
            "market_type": self.market_type,
            "profit_percentage": self.profit_percentage,
            "total_investment": self.total_investment,
            "guaranteed_return": self.guaranteed_return,
            "stake_allocations": self.stake_allocations,
        }

class ArbitrageCalculator:
    def __init__(self, min_profit: float = None):
        self.min_profit = min_profit or settings.MIN_PROFIT_THRESHOLD
    
    def calculate_arbitrage(self, outcomes: List[Tuple[float, str, str]]) -> Optional[ArbitrageOpportunity]:
        """
        Calculate arbitrage opportunity for given outcomes
        outcomes: [(odds, bookmaker_name, outcome_type), ...]
        
        Returns ArbitrageOpportunity if profit > min_profit, None otherwise
        """
        if len(outcomes) < 2:
            return None
        
        # Calculate implied probabilities
        implied_probs = [1 / odds for odds, _, _ in outcomes]
        total_prob = sum(implied_probs)
        
        # Check for arbitrage
        if total_prob < 1 - (self.min_profit / 100):
            profit = (1 - total_prob) * 100
            
            # Calculate stake allocations (for $100 total investment)
            stake_allocations = {}
            total_investment = 100.0
            
            for i, (odds, bookmaker, outcome) in enumerate(outcomes):
                stake_percentage = implied_probs[i] / total_prob
                stake_amount = total_investment * stake_percentage
                key = f"{bookmaker}_{outcome}"
                stake_allocations[key] = round(stake_amount, 2)
            
            guaranteed_return = total_investment * (1 + profit / 100)
            
            # For now, return placeholder event_id (will be set by detector)
            return ArbitrageOpportunity(
                event_id=0,
                sport_key="",
                market_type="h2h",
                outcomes=[{"bookmaker": bm, "outcome": out, "odds": odds} for odds, bm, out in outcomes],
                profit_percentage=round(profit, 2),
                stake_allocations=stake_allocations,
                total_investment=total_investment,
                guaranteed_return=round(guaranteed_return, 2)
            )
        
        return None
    
    def calculate_stakes(self, total_investment: float, stake_allocations: Dict[str, float]) -> Dict[str, float]:
        """Scale stake allocations to actual investment amount"""
        current_total = sum(stake_allocations.values())
        if current_total == 0:
            return stake_allocations
        
        scaling_factor = total_investment / current_total
        return {key: round(stake * scaling_factor, 2) for key, stake in stake_allocations.items()}
    
    def find_arbitrage_combinations(self, odds_dict: Dict[str, Dict[str, float]]) -> List[ArbitrageOpportunity]:
        """
        Find all arbitrage combinations from odds dictionary
        odds_dict: {
            "bookmaker1": {"home": 2.1, "away": 1.8},
            "bookmaker2": {"home": 2.0, "away": 1.9},
        }
        """
        opportunities = []
        
        # Extract all unique outcomes
        all_outcomes = set()
        for bookmaker_odds in odds_dict.values():
            all_outcomes.update(bookmaker_odds.keys())
        
        # For each outcome combination (2-way for now)
        outcomes_list = list(all_outcomes)
        
        if len(outcomes_list) >= 2:
            # Check all bookmaker combinations for each outcome pair
            for i in range(len(outcomes_list)):
                for j in range(i + 1, len(outcomes_list)):
                    outcome1 = outcomes_list[i]
                    outcome2 = outcomes_list[j]
                    
                    # Get best odds for each outcome
                    best_odds1 = max(
                        [(odds, bm) for bm, odds_dict_bm in odds_dict.items() 
                         if outcome1 in odds_dict_bm],
                        key=lambda x: x[0]
                    )
                    
                    best_odds2 = max(
                        [(odds, bm) for bm, odds_dict_bm in odds_dict.items() 
                         if outcome2 in odds_dict_bm],
                        key=lambda x: x[0]
                    )
                    
                    # Check if from different bookmakers
                    if best_odds1[1] != best_odds2[1]:
                        outcomes = [
                            (best_odds1[0], best_odds1[1], outcome1),
                            (best_odds2[0], best_odds2[1], outcome2)
                        ]
                        
                        arb = self.calculate_arbitrage(outcomes)
                        if arb:
                            opportunities.append(arb)
        
        return opportunities