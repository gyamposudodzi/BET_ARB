import aiohttp
import asyncio
from typing import List, Dict, Optional
from loguru import logger
from config.settings import settings

class TheOddsAPI:
    def __init__(self):
        self.api_key = settings.THE_ODDS_API_KEY
        self.base_url = "https://api.the-odds-api.com/v4"
        self.session: Optional[aiohttp.ClientSession] = None
        self.regions = "us"  # us, uk, eu, au
        self.markets = "h2h"  # h2h, spreads, totals
        self.odds_format = "decimal"
    
    async def initialize(self):
        """Initialize HTTP session"""
        if not self.api_key:
            logger.warning("The Odds API key not configured")
            return False
        
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": "ArbitrageBot/1.0"
            }
        )
        
        # Test API key
        if await self.test_api_key():
            logger.info("✅ The Odds API initialized successfully")
            return True
        else:
            logger.error("❌ Failed to initialize The Odds API")
            return False
    
    async def test_api_key(self) -> bool:
        """Test if API key is valid"""
        if not self.session:
            return False
        
        try:
            url = f"{self.base_url}/sports"
            params = {"apiKey": self.api_key}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"API key valid, {len(data)} sports available")
                    return True
                else:
                    logger.error(f"API key test failed: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"API key test error: {e}")
            return False
    
    async def get_sports(self) -> List[Dict]:
        """Get list of available sports"""
        if not self.session:
            return []
        
        try:
            url = f"{self.base_url}/sports"
            params = {"apiKey": self.api_key}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to get sports: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error getting sports: {e}")
            return []
    
    async def get_odds(self, sport_key: str, regions: str = None) -> List[Dict]:
        """
        Get odds for a specific sport
        Returns list of events with odds from multiple bookmakers
        """
        if not self.session:
            logger.warning("API not initialized")
            return []
        
        try:
            url = f"{self.base_url}/sports/{sport_key}/odds"
            params = {
                "apiKey": self.api_key,
                "regions": regions or self.regions,
                "markets": self.markets,
                "oddsFormat": self.odds_format,
            }
            
            logger.debug(f"Fetching odds for {sport_key}...")
            
            async with self.session.get(url, params=params, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Check remaining requests
                    remaining = response.headers.get("x-requests-remaining", "Unknown")
                    used = response.headers.get("x-requests-used", "Unknown")
                    logger.debug(f"API usage: {used} used, {remaining} remaining")
                    
                    logger.info(f"Retrieved {len(data)} events for {sport_key}")
                    return data
                else:
                    logger.error(f"Failed to get odds for {sport_key}: {response.status}")
                    return []
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching odds for {sport_key}")
            return []
        except Exception as e:
            logger.error(f"Error getting odds for {sport_key}: {e}")
            return []
    
    async def get_odds_multiple_sports(self, sport_keys: List[str]) -> Dict[str, List[Dict]]:
        """Get odds for multiple sports concurrently"""
        tasks = [self.get_odds(sport_key) for sport_key in sport_keys]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        odds_data = {}
        for sport_key, result in zip(sport_keys, results):
            if isinstance(result, Exception):
                logger.error(f"Error getting odds for {sport_key}: {result}")
                odds_data[sport_key] = []
            else:
                odds_data[sport_key] = result
        
        return odds_data
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    def get_test_data(self, sport_key: str) -> List[Dict]:
        """Generate test data for development when API is not available"""
        import random
        from datetime import datetime, timedelta
        
        test_bookmakers = ["pinnacle", "bet365", "draftkings", "fanduel", "betway"]
        test_teams = {
            "basketball_nba": [
                ("Los Angeles Lakers", "Boston Celtics"),
                ("Golden State Warriors", "Brooklyn Nets"),
                ("Chicago Bulls", "Miami Heat"),
            ],
            "soccer_epl": [
                ("Arsenal", "Chelsea"),
                ("Liverpool", "Manchester City"),
                ("Manchester United", "Tottenham"),
            ],
            "americanfootball_nfl": [
                ("New England Patriots", "Kansas City Chiefs"),
                ("Green Bay Packers", "Tampa Bay Buccaneers"),
                ("Dallas Cowboys", "San Francisco 49ers"),
            ],
        }
        
        teams = test_teams.get(sport_key, [("Team A", "Team B")])
        
        events = []
        for i, (home, away) in enumerate(teams):
            bookmakers = []
            
            for bm in random.sample(test_bookmakers, 3):  # Random 3 bookmakers
                # Generate realistic odds with slight variations
                base_home = 1.8 + random.random() * 0.4
                base_away = 1.8 + random.random() * 0.4
                
                # Add some arbitrage opportunities occasionally
                if random.random() < 0.3:  # 30% chance of arbitrage opportunity
                    base_home *= 0.95  # Slightly lower
                    base_away *= 0.95  # Slightly lower
                
                bookmakers.append({
                    "key": bm,
                    "markets": [{
                        "key": "h2h",
                        "outcomes": [
                            {"name": home, "price": round(base_home, 2)},
                            {"name": away, "price": round(base_away, 2)}
                        ]
                    }]
                })
            
            events.append({
                "id": f"test_{sport_key}_{i}",
                "sport_key": sport_key,
                "commence_time": (datetime.utcnow() + timedelta(hours=i*3)).isoformat(),
                "home_team": home,
                "away_team": away,
                "bookmakers": bookmakers
            })
        
        return events