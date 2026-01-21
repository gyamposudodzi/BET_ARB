from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import event
from config.settings import settings
import os

# Create data directory if it doesn't exist
os.makedirs(settings.DATA_DIR, exist_ok=True)

engine_kwargs = {
    "echo": False,  # Set to True for SQL debugging
}

# SQLite-specific async config
if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {
        "check_same_thread": False,
        "timeout": 30,
    }
else:
    # For Postgres / MySQL in the future
    engine_kwargs.update(
        pool_size=10,
        max_overflow=20,
    )

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)



# Configure SQLite for better performance
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragmas(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=-2000")  # 2MB cache
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_session() -> AsyncSession:
    """Get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """Initialize database tables"""
    from database.models import Base
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print(f"✅ Database initialized: {settings.DATABASE_URL}")
    
    # Add default data
    await add_default_data()

async def add_default_data():
    """Add default bookmakers and sports"""
    from database.models import Bookmaker, Sport
    from database.crud import CRUD
    
    async for session in get_session():
        crud = CRUD(session)
        
        # Add default bookmakers
        bookmakers = [
            Bookmaker(name="pinnacle", display_name="Pinnacle", is_active=True),
            Bookmaker(name="bet365", display_name="Bet365", is_active=True),
            Bookmaker(name="draftkings", display_name="DraftKings", is_active=True),
            Bookmaker(name="fanduel", display_name="FanDuel", is_active=True),
            Bookmaker(name="betway", display_name="Betway", is_active=True),
        ]
        
        for bm in bookmakers:
            existing = await crud.get_bookmaker_by_name(bm.name)
            if not existing:
                session.add(bm)
        
        # Add default sports
        sports = [
            Sport(name="NBA Basketball", key="basketball_nba", active=True, priority=1),
            Sport(name="English Premier League", key="soccer_epl", active=True, priority=2),
            Sport(name="NFL Football", key="americanfootball_nfl", active=True, priority=3),
            Sport(name="MLB Baseball", key="baseball_mlb", active=True, priority=4),
            Sport(name="Tennis", key="tennis", active=True, priority=5),
        ]
        
        for sport in sports:
            existing = await crud.get_sport_by_key(sport.key)
            if not existing:
                session.add(sport)
        
        await session.commit()
        print("✅ Added default bookmakers and sports")
        break

async def get_db_stats():
    """Get database statistics"""
    from database.models import Bookmaker, Sport, Event, Opportunity, Odds
    
    async for session in get_session():
        stats = {}
        
        # Count records
        for model, name in [
            (Bookmaker, "bookmakers"),
            (Sport, "sports"),
            (Event, "events"),
            (Odds, "odds"),
            (Opportunity, "opportunities"),
        ]:
            from sqlalchemy import select, func
            result = await session.execute(select(func.count()).select_from(model))
            stats[name] = result.scalar()
        
        # Get database file size
        db_path = settings.DATA_DIR / "arbitrage.db"
        if db_path.exists():
            size_bytes = db_path.stat().st_size
            stats["db_size_mb"] = round(size_bytes / (1024 * 1024), 2)
        
        return stats