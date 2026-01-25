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
    opportunity_type: str = "arbitrage" # 'arbitrage' or 'value_bet'
    
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
            
            # Initial precise calculation
            for i, (odds, bookmaker, outcome) in enumerate(outcomes):
                stake_percentage = implied_probs[i] / total_prob
                stake_amount = total_investment * stake_percentage
                key = f"{bookmaker}|{outcome}"
                stake_allocations[key] = stake_amount # Keep precise for now
            
            # Apply Rounding if enabled
            if settings.ROUND_STAKES and settings.ROUNDING_BASE > 0:
                base = settings.ROUNDING_BASE
                new_allocations = {}
                new_total_investment = 0.0
                
                for key, amount in stake_allocations.items():
                    # Round to nearest base (e.g. 5)
                    rounded = base * round(amount / base)
                    if rounded < base: rounded = base # Minimum bet is the base unit
                    new_allocations[key] = float(rounded)
                    new_total_investment += rounded
                
                stake_allocations = new_allocations
                total_investment = new_total_investment
            
            # Recalculate Profit based on FINAL stakes
            # Revenue = Stake * Odds (for the winning outcome)
            # Since we don't know which one wins, we calculate the worst-case scenario
            # to be safe, or just check that ALL scenarios yield > 0 profit.
            
            min_return = float('inf')
            
            # Check return for each outcome winning
            for i, (odds, bookmaker, outcome) in enumerate(outcomes):
                key = f"{bookmaker}|{outcome}"
                stake_on_winner = stake_allocations.get(key, 0)
                revenue = stake_on_winner * odds
                min_return = min(min_return, revenue)
            
            guaranteed_return = min_return # In a perfect arb with rounding, this varies strictly.
            total_profit = guaranteed_return - total_investment
            profit_percentage = (total_profit / total_investment) * 100 if total_investment > 0 else 0
            
            # SANITY CHECK: Filter out results that are too good to be true (e.g. Outright partial matches)
            if profit_percentage > settings.MAX_PROFIT_THRESHOLD and getattr(settings, "MAX_PROFIT_THRESHOLD", 0) > 0:
                # Log this? for now just silently return None or maybe create a record with 'invalid' status?
                # Returning None is safest to avoid spamming alerts.
                return None
            
            # If rounding killed the profit, ignore this opportunity (unless it's value betting)
            if profit_percentage <= 0:
                # Optional: Log that rounding killed an arb
                return None
            
            # Final formatting
            stake_allocations = {k: round(v, 2) for k, v in stake_allocations.items()}
            
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
                profit_percentage=round(profit_percentage, 2),
                stake_allocations=stake_allocations,
                total_investment=round(total_investment, 2),
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
        Find all arbitrage combinations from odds dictionary supporting n-way markets
        and dynamic team names.
        """
        opportunities = []
        
        # 1. Identify all unique outcomes
        all_outcomes = set()
        for bm_odds in odds_dict.values():
            all_outcomes.update(bm_odds.keys())
            
        # 2. Categorize outcomes
        draw_outcomes = {o for o in all_outcomes if o.lower() == 'draw' or o.lower() == 'x'}
        competitor_outcomes = [o for o in all_outcomes if o not in draw_outcomes]
        
        # 3. Generate Valid Schemas
        # We assume events usually have 2 main competitors + optional draw.
        # If there are outcome naming discrepancies (e.g., "Man Utd" vs "Manchester United"),
        # The Odds API should have normalized them. If not, this logic treats them as conflicting competitors
        # and won't match them (which is safe).
        
        generated_schemas = []
        
        import itertools
        
        # Generate pairs of competitors
        for c1, c2 in itertools.combinations(competitor_outcomes, 2):
            # If Draw exists, prioritize 3-way schema
            if draw_outcomes:
                for draw in draw_outcomes:
                    generated_schemas.append({c1, c2, draw})
            else:
                # No draw detected, try 2-way schema
                generated_schemas.append({c1, c2})
                
        # 4. Process Schemas
        for schema in generated_schemas:
            best_odds_combination = []
            possible_schema = True
            
            for outcome in schema:
                # Find max odds for this specific outcome
                valid_offers = []
                for bm_name, bm_odds in odds_dict.items():
                    if outcome in bm_odds:
                        valid_offers.append((bm_odds[outcome], bm_name))
                
                if not valid_offers:
                    possible_schema = False
                    break
                
                best_price, best_bm = max(valid_offers, key=lambda x: x[0])
                best_odds_combination.append((best_price, best_bm, outcome))
            
            if possible_schema and len(best_odds_combination) == len(schema):
                arb = self.calculate_arbitrage(best_odds_combination)
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
        
    def calculate_true_probs(self, odds_list: List[float]) -> List[float]:
        """
        Calculate true probabilities by removing vigorish (margin).
        Uses a simple proportional distribution of the margin.
        """
        implied_probs = [1 / o for o in odds_list]
        total_implied_prob = sum(implied_probs)
        
        # Normalize to sum to 1.0 (True Probability)
        true_probs = [p / total_implied_prob for p in implied_probs]
        return true_probs

    def calculate_ev(self, odds: float, true_prob: float) -> float:
        """
        Calculate Expected Value %
        EV = (Probability * Odds) - 1
        """
        return ((true_prob * odds) - 1) * 100

    def find_value_bets(self, odds_dict: Dict[str, Dict[str, float]], sharp_bookie: str = None) -> List[ArbitrageOpportunity]:
        """
        Find Value Bets by comparing odds against a Sharp Bookmaker.
        """
        opportunities = []
        sharp_bookie = sharp_bookie or settings.SHARP_BOOKMAKER
        
        # Check if Sharp Bookie exists in the data
        if sharp_bookie not in odds_dict:
            return [] # Cannot calculate EV without a sharp reference
            
        sharp_odds = odds_dict[sharp_bookie]
        
        # We need a complete set of outcomes from the Sharp to calculate True Probability
        # For now, let's assume if it has outcomes, they are a complete set for that valid market type
        # Or we can reuse our schema detection logic.
        
        outcomes_list = list(sharp_odds.keys())
        odds_values = [sharp_odds[o] for o in outcomes_list]
        
        if not odds_values:
            return []
            
        true_probs = self.calculate_true_probs(odds_values)
        true_prob_map = dict(zip(outcomes_list, true_probs))
        
        # Now check all other bookmakers for value
        for bm_name, bm_odds in odds_dict.items():
            if bm_name == sharp_bookie:
                continue
                
            for outcome, odds in bm_odds.items():
                if outcome in true_prob_map:
                    true_prob = true_prob_map[outcome]
                    ev = self.calculate_ev(odds, true_prob)
                    
                    if ev >= settings.MIN_EV_THRESHOLD:
                        # Found a Value Bet!
                        
                        # Format as an "Opportunity" object, but with special structure
                        # Since it's a single bet, stake allocation is 100% on this outcome.
                        
                        stakes = {f"{bm_name}|{outcome}": settings.MAX_STAKE} 
                        if settings.ROUND_STAKES:
                             stakes[f"{bm_name}|{outcome}"] = float(settings.ROUNDING_BASE * round(settings.MAX_STAKE/settings.ROUNDING_BASE))

                        opp = ArbitrageOpportunity(
                            event_id=0,
                            sport_key="",
                            market_type="value_bet", # Special marker
                            outcomes=[{"bookmaker": bm_name, "outcome": outcome, "odds": odds, "true_prob": round(true_prob, 3)}],
                            profit_percentage=round(ev, 2), # Using EV as the profit metric
                            stake_allocations=stakes,
                            total_investment=stakes[f"{bm_name}|{outcome}"],
                            guaranteed_return=0 # NOT guaranteed
                        )
                        opportunities.append(opp)
                        
        return opportunities