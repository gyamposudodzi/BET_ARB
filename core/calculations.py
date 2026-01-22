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
        
        # Check for arbitrage (convert min_profit from percentage to decimal)
        min_profit_decimal = self.min_profit / 100
        if total_prob < 1 - min_profit_decimal:
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
            
            # Create outcomes list for the opportunity
            opportunity_outcomes = []
            for odds, bookmaker, outcome in outcomes:
                opportunity_outcomes.append({
                    "bookmaker": bookmaker,
                    "outcome": outcome,
                    "odds": odds
                })
            
            return ArbitrageOpportunity(
                event_id=0,
                sport_key="",
                market_type="h2h",
                outcomes=opportunity_outcomes,
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
                    
                    # Get best odds for each outcome - FIXED: use odds_dict_bm[outcome] not odds
                    best_odds1_list = [
                        (odds_dict_bm[outcome1], bm) 
                        for bm, odds_dict_bm in odds_dict.items() 
                        if outcome1 in odds_dict_bm
                    ]
                    
                    best_odds2_list = [
                        (odds_dict_bm[outcome2], bm) 
                        for bm, odds_dict_bm in odds_dict.items() 
                        if outcome2 in odds_dict_bm
                    ]
                    
                    if best_odds1_list and best_odds2_list:
                        best_odds1 = max(best_odds1_list, key=lambda x: x[0])
                        best_odds2 = max(best_odds2_list, key=lambda x: x[0])
                        
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
    
    def find_all_arbitrage_opportunities(self, events_data: List[Dict]) -> List[ArbitrageOpportunity]:
        """
        Find arbitrage opportunities from raw events data
        events_data: List of events from API with bookmakers and markets
        """
        all_opportunities = []
        
        for event in events_data:
            event_id = event.get("id", "")
            sport_key = event.get("sport_key", "")
            
            # Build odds dictionary for this event
            odds_dict = {}
            
            for bookmaker in event.get("bookmakers", []):
                bookmaker_key = bookmaker.get("key", "")
                
                for market in bookmaker.get("markets", []):
                    if market.get("key") == "h2h":  # Moneyline market
                        if bookmaker_key not in odds_dict:
                            odds_dict[bookmaker_key] = {}
                        
                        for outcome in market.get("outcomes", []):
                            outcome_name = outcome.get("name", "").lower()
                            price = outcome.get("price", 0)
                            
                            if price > 0:  # Only add valid odds
                                odds_dict[bookmaker_key][outcome_name] = price
            
            # Find arbitrage opportunities for this event
            event_opportunities = self.find_arbitrage_combinations(odds_dict)
            
            # Add event metadata to each opportunity
            for opp in event_opportunities:
                opp.event_id = event_id
                opp.sport_key = sport_key
            
            all_opportunities.extend(event_opportunities)
        
        return all_opportunities