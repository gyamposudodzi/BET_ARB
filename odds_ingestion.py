import asyncio
import aiohttp
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OddsFetcher:
    def __init__(self):
        self.sources = [
            {
                "name": "Bet365",
                "url": "https://api.example.com/bet365/odds",
                "weight": 1.0
            },
            {
                "name": "WilliamHill",
                "url": "https://api.example.com/williamhill/odds",
                "weight": 1.0
            },
            {
                "name": "Pinnacle",
                "url": "https://api.example.com/pinnacle/odds",
                "weight": 1.0
            },
            {
                "name": "Betfair",
                "url": "https://api.example.com/betfair/odds",
                "weight": 1.0
            }
        ]
        
        # Sample events for simulation
        self.sample_events = [
            {
                "event_id": "epl_mun_ars_20240120",
                "sport": "football",
                "league": "Premier League",
                "home_team": "Manchester United",
                "away_team": "Arsenal",
                "start_time": datetime.now() + timedelta(hours=2)
            },
            {
                "event_id": "epl_mci_liv_20240121",
                "sport": "football",
                "league": "Premier League",
                "home_team": "Manchester City",
                "away_team": "Liverpool",
                "start_time": datetime.now() + timedelta(days=1)
            },
            {
                "event_id": "ucl_rm_bay_20240122",
                "sport": "football",
                "league": "Champions League",
                "home_team": "Real Madrid",
                "away_team": "Bayern Munich",
                "start_time": datetime.now() + timedelta(days=2)
            },
            {
                "event_id": "nba_lal_gsw_20240120",
                "sport": "basketball",
                "league": "NBA",
                "home_team": "Los Angeles Lakers",
                "away_team": "Golden State Warriors",
                "start_time": datetime.now() + timedelta(hours=3)
            }
        ]
    
    async def fetch_from_source(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch odds from a single source"""
        if settings.simulation_mode:
            return self._generate_simulated_odds(source["name"])
        
        # Real API fetching (to be implemented later)
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(source["url"], timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_api_response(data, source["name"])
                    else:
                        logger.warning(f"Failed to fetch from {source['name']}: HTTP {response.status}")
                        return []
            except Exception as e:
                logger.error(f"Error fetching from {source['name']}: {e}")
                return []
    
    def _generate_simulated_odds(self, bookmaker: str) -> List[Dict[str, Any]]:
        """Generate realistic simulated odds for testing"""
        odds_data = []
        
        for event in self.sample_events:
            # Add some randomness to make detection interesting
            base_home = random.uniform(1.8, 2.5)
            base_draw = random.uniform(3.0, 4.0)
            base_away = random.uniform(2.0, 3.5)
            
            # Bookmaker-specific biases
            if bookmaker == "Pinnacle":
                # Pinnacle typically has sharpest odds
                bias = random.uniform(-0.05, 0.05)
            elif bookmaker == "Bet365":
                bias = random.uniform(-0.1, 0.1)
            else:
                bias = random.uniform(-0.15, 0.15)
            
            home_odds = round(base_home + bias, 2)
            draw_odds = round(base_draw + bias, 2)
            away_odds = round(base_away + bias, 2)
            
            # 1X2 market
            for outcome, odds in [("home", home_odds), ("draw", draw_odds), ("away", away_odds)]:
                odds_data.append({
                    "bookmaker": bookmaker,
                    "event_id": event["event_id"],
                    "sport": event["sport"],
                    "league": event["league"],
                    "event": f"{event['home_team']} vs {event['away_team']}",
                    "market": "1X2",
                    "outcome": outcome,
                    "odds": odds,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # Over/Under market for some events
            if event["sport"] == "football":
                over_odds = round(random.uniform(1.8, 2.2), 2)
                under_odds = round(random.uniform(1.7, 2.1), 2)
                
                odds_data.append({
                    "bookmaker": bookmaker,
                    "event_id": event["event_id"],
                    "sport": event["sport"],
                    "league": event["league"],
                    "event": f"{event['home_team']} vs {event['away_team']}",
                    "market": "over_under",
                    "outcome": "over_2.5",
                    "odds": over_odds,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                odds_data.append({
                    "bookmaker": bookmaker,
                    "event_id": event["event_id"],
                    "sport": event["sport"],
                    "league": event["league"],
                    "event": f"{event['home_team']} vs {event['away_team']}",
                    "market": "over_under",
                    "outcome": "under_2.5",
                    "odds": under_odds,
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        return odds_data
    
    def _parse_api_response(self, data: Dict[str, Any], bookmaker: str) -> List[Dict[str, Any]]:
        """Parse real API response (placeholder)"""
        # This will be implemented when we add real bookmaker APIs
        logger.info(f"Parsing real API response from {bookmaker}")
        return []
    
    async def fetch_all(self) -> List[Dict[str, Any]]:
        """Fetch odds from all sources concurrently"""
        logger.info("📡 Fetching odds from all sources...")
        
        tasks = [self.fetch_from_source(source) for source in self.sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_odds = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error from {self.sources[i]['name']}: {result}")
            elif result:
                all_odds.extend(result)
        
        logger.info(f"✅ Fetched {len(all_odds)} odds entries from {len([r for r in results if not isinstance(r, Exception)])} sources")
        return all_odds

# Global fetcher instance
odds_fetcher = OddsFetcher()