from typing import Dict, List, Optional, Set

class MarketMapper:
    """
    Standardizes market names and types across different bookmakers
    to allow cross-market arbitrage detection.
    """
    
    # Standard Market Keys
    H2H = "h2h"
    TOTALS = "totals"
    SPREADS = "spreads"
    
    def __init__(self):
        # Maps API market keys to internal standard keys
        self._market_alias_map = {
            "h2h": self.H2H,
            "h2h_lay": self.H2H,  # Exchange lay bets can map here (advanced)
            "moneyline": self.H2H,
            "match_winner": self.H2H,
            "1x2": self.H2H,
            
            "spreads": self.SPREADS,
            "handicap": self.SPREADS,
            "asian_handicap": self.SPREADS,
            
            "totals": self.TOTALS,
            "over_under": self.TOTALS,
        }

    def normalize_market_key(self, api_market_key: str) -> str:
        """
        Convert various API market keys to a standard internal key.
        e.g. 'moneyline' -> 'h2h'
        """
        return self._market_alias_map.get(api_market_key.lower(), api_market_key.lower())

    def get_equivalent_markets(self, market_key: str) -> Set[str]:
        """
        Get all API keys that map to the same internal market.
        Useful for querying multiple keys from the API.
        """
        normalized = self.normalize_market_key(market_key)
        return {k for k, v in self._market_alias_map.items() if v == normalized}

    def standardize_outcome_name(self, outcome_name: str, market_type: str) -> str:
        """
        Standardize outcome names for easier matching.
        e.g. 'Under 2.5 Goals' -> 'under 2.5'
        """
        name = outcome_name.lower().strip()
        
        # Remove common prefixes/suffixes
        name = name.replace("over ", "o").replace("under ", "u")
        name = name.replace("goals", "").strip()
        
        # Normalize Draw synonyms
        if name in ["tie", "the draw", "draw (x)"]:
            name = "draw"
            
        return name
