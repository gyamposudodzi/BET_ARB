import asyncpg
import asyncio
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    def create_database_if_not_exists(self):
        """Create database if it doesn't exist"""
        try:
            # Connect to default postgres database to create our database
            conn = psycopg2.connect(
                host=settings.db_host,
                port=settings.db_port,
                user=settings.db_user,
                password=settings.db_password,
                database="postgres"  # Connect to default postgres database
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (settings.db_name,))
            exists = cursor.fetchone()
            
            if not exists:
                logger.info(f"Creating database '{settings.db_name}'...")
                cursor.execute(sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(settings.db_name)
                ))
                logger.info(f"✅ Database '{settings.db_name}' created successfully")
            else:
                logger.info(f"Database '{settings.db_name}' already exists")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Failed to create database: {e}")
            raise
    
    async def connect(self):
        """Create database connection pool"""
        try:
            # First, ensure database exists
            self.create_database_if_not_exists()
            
            # Now connect to our database
            self.pool = await asyncpg.create_pool(
                dsn=settings.database_url,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            logger.info("✅ Database connection established")
            
            # Initialize tables
            await self.init_tables()
            
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
    
    async def init_tables(self):
        """Initialize database tables"""
        sql_commands = [
            """
            CREATE TABLE IF NOT EXISTS bookmakers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) UNIQUE NOT NULL,
                base_url VARCHAR(255),
                reliability_score FLOAT DEFAULT 1.0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS events (
                id SERIAL PRIMARY KEY,
                event_id VARCHAR(100) UNIQUE NOT NULL,
                sport VARCHAR(50) NOT NULL,
                league VARCHAR(100) NOT NULL,
                home_team VARCHAR(100) NOT NULL,
                away_team VARCHAR(100) NOT NULL,
                start_time TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS odds (
                id SERIAL PRIMARY KEY,
                bookmaker_id INTEGER REFERENCES bookmakers(id),
                event_id VARCHAR(100) REFERENCES events(event_id),
                market VARCHAR(50) NOT NULL,
                outcome VARCHAR(50) NOT NULL,
                odds DECIMAL(8, 3) NOT NULL,
                timestamp TIMESTAMP DEFAULT NOW(),
                UNIQUE(bookmaker_id, event_id, market, outcome)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
                id SERIAL PRIMARY KEY,
                event_id VARCHAR(100) REFERENCES events(event_id),
                market VARCHAR(50) NOT NULL,
                margin DECIMAL(5, 2) NOT NULL,
                bookmaker_combination JSONB NOT NULL,
                odds_combination JSONB NOT NULL,
                detected_at TIMESTAMP DEFAULT NOW(),
                expires_at TIMESTAMP,
                is_expired BOOLEAN DEFAULT FALSE
            )
            """,
            """
            -- Insert default bookmakers
            INSERT INTO bookmakers (name, reliability_score) 
            VALUES 
                ('Bet365', 1.0),
                ('WilliamHill', 1.0),
                ('Pinnacle', 1.0),
                ('Betfair', 1.0)
            ON CONFLICT (name) DO NOTHING;
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_odds_timestamp ON odds(timestamp);
            CREATE INDEX IF NOT EXISTS idx_arbitrage_detected ON arbitrage_opportunities(detected_at);
            CREATE INDEX IF NOT EXISTS idx_arbitrage_expired ON arbitrage_opportunities(is_expired);
            """
        ]
        
        try:
            async with self.pool.acquire() as connection:
                for sql in sql_commands:
                    await connection.execute(sql)
            logger.info("✅ Database tables initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize tables: {e}")
            raise
    
    async def insert_odds(self, odds_data: List[Dict[str, Any]]):
        """Insert odds data into database"""
        if not self.pool:
            await self.connect()
        
        try:
            async with self.pool.acquire() as connection:
                # First, ensure bookmaker exists
                for odds in odds_data:
                    # Insert/update bookmaker
                    await connection.execute("""
                        INSERT INTO bookmakers (name, updated_at)
                        VALUES ($1, NOW())
                        ON CONFLICT (name) DO UPDATE
                        SET updated_at = NOW()
                    """, odds['bookmaker'])
                    
                    # Get bookmaker ID
                    result = await connection.fetchrow(
                        "SELECT id FROM bookmakers WHERE name = $1",
                        odds['bookmaker']
                    )
                    bookmaker_id = result['id']
                    
                    # Insert odds
                    await connection.execute("""
                        INSERT INTO odds (bookmaker_id, event_id, market, outcome, odds, timestamp)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (bookmaker_id, event_id, market, outcome) 
                        DO UPDATE SET odds = EXCLUDED.odds, timestamp = EXCLUDED.timestamp
                    """, bookmaker_id, odds['event_id'], odds['market'], 
                        odds['outcome'], odds['odds'], odds['timestamp'])
            
            logger.debug(f"Inserted/updated {len(odds_data)} odds entries")
            
        except Exception as e:
            logger.error(f"Failed to insert odds: {e}")
    
    async def insert_arbitrage(self, arbitrage_data: Dict[str, Any]):
        """Insert arbitrage opportunity into database"""
        if not self.pool:
            await self.connect()
        
        try:
            async with self.pool.acquire() as connection:
                await connection.execute("""
                    INSERT INTO arbitrage_opportunities 
                    (event_id, market, margin, bookmaker_combination, odds_combination, expires_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, 
                arbitrage_data['event_id'],
                arbitrage_data['market'],
                arbitrage_data['margin'],
                arbitrage_data['bookmaker_combination'],
                arbitrage_data['odds_combination'],
                arbitrage_data.get('expires_at')
                )
                
                logger.info(f"✅ Arbitrage opportunity saved: {arbitrage_data['event_id']}")
                
        except Exception as e:
            logger.error(f"Failed to insert arbitrage: {e}")
    
    async def close(self):
        """Close database connection"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection closed")

# Global database instance
db = Database()