from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func, desc
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json

from database.models import Bookmaker, Sport, Event, Market, Odds, Opportunity, Alert
from config.settings import settings

class CRUD:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # Bookmaker operations
    async def get_bookmaker_by_name(self, name: str) -> Optional[Bookmaker]:
        stmt = select(Bookmaker).where(Bookmaker.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_active_bookmakers(self) -> List[Bookmaker]:
        stmt = select(Bookmaker).where(Bookmaker.is_active == True).order_by(Bookmaker.name)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    # Sport operations
    async def get_sport_by_key(self, key: str) -> Optional[Sport]:
        stmt = select(Sport).where(Sport.key == key)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_active_sports(self) -> List[Sport]:
        stmt = select(Sport).where(Sport.active == True).order_by(Sport.priority.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def update_sport_last_scan(self, sport_id: int):
        stmt = update(Sport).where(Sport.id == sport_id).values(
            last_scan=datetime.utcnow()
        )
        await self.session.execute(stmt)
        await self.session.commit()
    
    # Event operations
    async def get_or_create_event(self, sport_id: int, external_id: str, **kwargs) -> Event:
        """Get existing event or create new one"""
        stmt = select(Event).where(
            Event.sport_id == sport_id,
            Event.external_id == external_id
        )
        result = await self.session.execute(stmt)
        event = result.scalar_one_or_none()
        
        if event:
            # Update existing event
            for key, value in kwargs.items():
                if hasattr(event, key):
                    setattr(event, key, value)
            event.last_updated = datetime.utcnow()
        else:
            # Create new event
            event = Event(
                sport_id=sport_id,
                external_id=external_id,
                **kwargs
            )
            self.session.add(event)
        
        await self.session.commit()
        await self.session.refresh(event)
        return event
    
    # Odds operations
    async def update_odds(self, market_id: int, bookmaker_id: int, outcome: str, price: float) -> Odds:
        """Update or create odds record"""
        stmt = select(Odds).where(
            Odds.market_id == market_id,
            Odds.bookmaker_id == bookmaker_id,
            Odds.outcome == outcome
        )
        result = await self.session.execute(stmt)
        odds = result.scalar_one_or_none()
        
        if odds:
            odds.price = price
            odds.last_updated = datetime.utcnow()
        else:
            odds = Odds(
                market_id=market_id,
                bookmaker_id=bookmaker_id,
                outcome=outcome,
                price=price
            )
            self.session.add(odds)
        
        await self.session.commit()
        return odds
    
    async def get_latest_odds_for_market(self, market_id: int) -> List[Odds]:
        """Get latest odds for a market"""
        stmt = select(Odds).where(
            Odds.market_id == market_id,
            Odds.last_updated >= datetime.utcnow() - timedelta(minutes=5)
        ).order_by(Odds.bookmaker_id, Odds.outcome)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    # Opportunity operations
    async def create_opportunity(self, data: Dict) -> Opportunity:
        """Create a new arbitrage opportunity"""
        opportunity = Opportunity(**data)
        self.session.add(opportunity)
        await self.session.commit()
        await self.session.refresh(opportunity)
        return opportunity
    
    async def get_recent_opportunities(self, limit: int = 20) -> List[Opportunity]:
        stmt = select(Opportunity).order_by(desc(Opportunity.detected_at)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_active_opportunities(self) -> List[Opportunity]:
        stmt = select(Opportunity).where(
            Opportunity.status == "detected",
            Opportunity.expiry_time > datetime.utcnow(),
            Opportunity.profit_percentage >= settings.MIN_PROFIT_THRESHOLD
        ).order_by(desc(Opportunity.profit_percentage))
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    # Alert operations
    async def create_alert(self, level: str, category: str, message: str, data: Dict = None) -> Alert:
        alert = Alert(
            level=level,
            category=category,
            message=message,
            data=data or {}
        )
        self.session.add(alert)
        await self.session.commit()
        await self.session.refresh(alert)
        return alert
    
    async def mark_alert_sent(self, alert_id: int):
        stmt = update(Alert).where(Alert.id == alert_id).values(
            sent_to_telegram=True,
            sent_at=datetime.utcnow()
        )
        await self.session.execute(stmt)
        await self.session.commit()
    
    # Statistics
    async def get_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        from sqlalchemy import func
        
        stats = {}
        
        # Count opportunities today
        today = datetime.utcnow().date()
        start_of_day = datetime.combine(today, datetime.min.time())
        
        stmt = select(func.count(Opportunity.id)).where(
            Opportunity.detected_at >= start_of_day
        )
        result = await self.session.execute(stmt)
        stats["opportunities_today"] = result.scalar() or 0
        
        # Count total opportunities
        stmt = select(func.count(Opportunity.id))
        result = await self.session.execute(stmt)
        stats["total_opportunities"] = result.scalar() or 0
        
        # Average profit today
        stmt = select(func.avg(Opportunity.profit_percentage)).where(
            Opportunity.detected_at >= start_of_day
        )
        result = await self.session.execute(stmt)
        stats["avg_profit_today"] = round(result.scalar() or 0, 2)
        
        # Count bookmakers and sports
        stmt = select(func.count(Bookmaker.id)).where(Bookmaker.is_active == True)
        result = await self.session.execute(stmt)
        stats["active_bookmakers"] = result.scalar() or 0
        
        stmt = select(func.count(Sport.id)).where(Sport.active == True)
        result = await self.session.execute(stmt)
        stats["active_sports"] = result.scalar() or 0
        
        return stats