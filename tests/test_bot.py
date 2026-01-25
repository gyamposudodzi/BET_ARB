#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def test_database():
    """Test database connection"""
    print("🔍 Testing database...")
    
    try:
        from database.session import init_db, get_db_stats
        
        # Initialize database
        await init_db()
        
        # Get stats
        stats = await get_db_stats()
        print(f"✅ Database OK: {stats}")
        
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

async def test_calculations():
    """Test arbitrage calculations"""
    print("\n🔍 Testing calculations...")
    
    try:
        from core.calculations import ArbitrageCalculator
        
        calculator = ArbitrageCalculator(min_profit=0.5)
        
        # Test case 1: Clear arbitrage
        outcomes = [
            (2.10, "pinnacle", "home"),
            (2.10, "bet365", "away")
        ]
        
        result = calculator.calculate_arbitrage(outcomes)
        
        if result:
            print(f"✅ Arbitrage detected: {result.profit_percentage}% profit")
        else:
            print("❌ Failed to detect arbitrage")
            return False
        
        # Test case 2: No arbitrage
        outcomes = [
            (1.50, "pinnacle", "home"),
            (2.50, "bet365", "away")
        ]
        
        result = calculator.calculate_arbitrage(outcomes)
        
        if not result:
            print("✅ Correctly identified no arbitrage")
        else:
            print("❌ Incorrectly found arbitrage")
            return False
        
        print("✅ Calculations test passed")
        return True
        
    except Exception as e:
        print(f"❌ Calculations test failed: {e}")
        return False

async def test_telegram():
    """Test Telegram connectivity"""
    print("\n🔍 Testing Telegram...")
    
    try:
        from config.settings import settings
        
        if not settings.TELEGRAM_BOT_TOKEN:
            print("⚠️ Telegram token not set (skipping)")
            return True
        
        from alerts.telegram_bot import TelegramAlertBot
        bot = TelegramAlertBot()
        
        if await bot.initialize():
            print("✅ Telegram bot connected")
            await bot.close()
            return True
        else:
            print("❌ Failed to connect Telegram")
            return False
            
    except Exception as e:
        print(f"❌ Telegram test failed: {e}")
        return False

async def test_odds_api():
    """Test Odds API connectivity"""
    print("\n🔍 Testing Odds API...")
    
    try:
        from config.settings import settings
        
        if not settings.THE_ODDS_API_KEY:
            print("⚠️ Odds API key not set (skipping)")
            return True
        
        from data_collection.odds_api import TheOddsAPI
        api = TheOddsAPI()
        
        if await api.initialize():
            sports = await api.get_sports()
            if sports:
                print(f"✅ Odds API connected: {len(sports)} sports available")
                await api.close()
                return True
            else:
                print("❌ No sports data returned")
                return False
        else:
            print("❌ Failed to connect to Odds API")
            return False
            
    except Exception as e:
        print(f"❌ Odds API test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🧪 Arbitrage Bot Test Suite")
    print("=" * 50)
    
    tests = [
        ("Database", test_database),
        ("Calculations", test_calculations),
        ("Telegram", test_telegram),
        ("Odds API", test_odds_api),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            success = await test_func()
            if success:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 All tests passed! Ready to run:")
        print("  python main.py")
    else:
        print("\n⚠️ Some tests failed. Check configuration.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())