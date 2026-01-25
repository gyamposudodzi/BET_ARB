import asyncio
from typing import List, Dict, Optional
from loguru import logger
from datetime import datetime, timedelta

from core.calculations import ArbitrageCalculator, ArbitrageOpportunity
from database.crud import CRUD
from database.models import Odds

class ArbitrageDetector:
    def __init__(self):
        self.calculator = ArbitrageCalculator()
    
    async def scan_market(self, market_id: int, crud: CRUD) -> List[ArbitrageOpportunity]:
        """Scan a specific market for arbitrage opportunities"""
        # Get latest odds for this market
        odds_records = await crud.get_latest_odds_for_market(market_id)
        
        if len(odds_records) < 2:
            return []
        
        # Organize odds by bookmaker and outcome
        odds_dict = {}
        for odds_record in odds_records:
            bookmaker_name = await self._get_bookmaker_name(crud, odds_record.bookmaker_id)
            if bookmaker_name not in odds_dict:
                odds_dict[bookmaker_name] = {}
            odds_dict[bookmaker_name][odds_record.outcome] = odds_record.price
        
        # Find arbitrage opportunities
        opportunities = self.calculator.find_arbitrage_combinations(odds_dict)
        
        # Add metadata to opportunities
        for opp in opportunities:
            opp.event_id = await self._get_event_id_from_market(crud, market_id)
            opp.sport_key = await self._get_sport_from_market(crud, market_id)
        
        return opportunities
    
    async def _get_bookmaker_name(self, crud: CRUD, bookmaker_id: int) -> str:
        """Get bookmaker name from ID"""
        # In a real implementation, cache this or get from database
        return f"bookmaker_{bookmaker_id}"
    
    async def _get_event_id_from_market(self, crud: CRUD, market_id: int) -> int:
        """Get event ID from market ID"""
        # Placeholder - would query database
        return 1
    
    async def _get_sport_from_market(self, crud: CRUD, market_id: int) -> str:
        """Get sport key from market ID"""
        # Placeholder
        return "basketball_nba"
    
    async def process_api_data(self, api_data: List[Dict]) -> List[ArbitrageOpportunity]:
        """Process raw API data to find arbitrage"""
        opportunities = []
        from core.market_mapper import MarketMapper
        mapper = MarketMapper()
        
        for event in api_data:
            # Group odds by NORMALIZED market type
            # { "h2h": { "bookie1": {...}, "bookie2": {...} }, "totals": ... }
            market_odds_groups = {}
            
            for bookmaker in event.get("bookmakers", []):
                bm_key = bookmaker.get("key", "")
                
                for market in bookmaker.get("markets", []):
                    raw_market_key = market.get("key")
                    normalized_key = mapper.normalize_market_key(raw_market_key)
                    
                    if normalized_key not in market_odds_groups:
                        market_odds_groups[normalized_key] = {}
                        
                    if bm_key not in market_odds_groups[normalized_key]:
                        market_odds_groups[normalized_key][bm_key] = {}
                    
                    for outcome in market.get("outcomes", []):
                        raw_outcome_name = outcome.get("name", "")
                        outcome_name = mapper.standardize_outcome_name(raw_outcome_name, normalized_key)
                        price = outcome.get("price", 0)
                        market_odds_groups[normalized_key][bm_key][outcome_name] = price
            
            # Find arbitrage for EACH normalized market group
            for market_type, odds_dict in market_odds_groups.items():
                # We currently only support h2h calculations in the calculator 
                # (though logic is generic, we want to be careful).
                # The updated calculator supports n-way, so it should handle anything provided
                # the schema matching logic finds a set.
                
                event_opportunities = self.calculator.find_arbitrage_combinations(odds_dict)
                
                for opp in event_opportunities:
                    opp.event_id = event.get("id", 0)
                    opp.sport_key = event.get("sport_key", "")
                    opp.market_type = market_type # Use the normalized key
                    opportunities.append(opp)
        
        return opportunities