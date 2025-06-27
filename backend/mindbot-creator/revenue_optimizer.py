"""
Revenue optimization system for MindBot personas
Handles pricing, ads, subscriptions, and user value optimization
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class RevenueStrategy(str, Enum):
    """Different revenue optimization strategies"""
    FREEMIUM = "freemium"           # Free tier with premium upgrades
    AD_SUPPORTED = "ad_supported"    # Free with ads, paid to remove
    SUBSCRIPTION = "subscription"    # Recurring subscription model
    USAGE_BASED = "usage_based"      # Pay per use/minute
    HYBRID = "hybrid"                # Combination of strategies

class UserSegment(str, Enum):
    """User segments for targeted pricing"""
    NEW = "new"                      # New users
    CASUAL = "casual"                # Infrequent users
    REGULAR = "regular"              # Regular users
    POWER = "power"                  # Heavy users
    BUSINESS = "business"            # Business/professional users
    EDUCATIONAL = "educational"      # Educational users
    ENTERPRISE = "enterprise"        # Enterprise customers

@dataclass
class PricingTier:
    """Pricing tier configuration"""
    id: str
    name: str
    price_monthly: float
    price_yearly: float
    features: List[str]
    personas_included: List[str]
    custom_personas_allowed: int
    ad_free: bool
    priority_support: bool
    advanced_analytics: bool
    max_daily_minutes: Optional[int] = None
    
    def get_monthly_price_display(self) -> str:
        """Get formatted monthly price"""
        return f"${self.price_monthly:.2f}/month"
    
    def get_yearly_price_display(self) -> str:
        """Get formatted yearly price with savings"""
        monthly_equivalent = self.price_yearly / 12
        savings = (self.price_monthly * 12) - self.price_yearly
        savings_percent = (savings / (self.price_monthly * 12)) * 100
        
        return f"${self.price_yearly:.2f}/year (${monthly_equivalent:.2f}/mo, save ${savings:.2f} or {savings_percent:.0f}%)"

class RevenueOptimizer:
    """Revenue optimization system for MindBot"""
    
    def __init__(self):
        self.pricing_tiers = self._initialize_pricing_tiers()
        self.ad_config = self._initialize_ad_config()
        self.user_segments = {}
        self.conversion_strategies = {}
        self.revenue_metrics = {
            "total_revenue": 0.0,
            "subscription_revenue": 0.0,
            "time_card_revenue": 0.0,
            "ad_revenue": 0.0,
            "custom_persona_revenue": 0.0
        }
    
    def _initialize_pricing_tiers(self) -> Dict[str, PricingTier]:
        """Initialize pricing tiers"""
        return {
            "free": PricingTier(
                id="free",
                name="Free",
                price_monthly=0.0,
                price_yearly=0.0,
                features=[
                    "Access to basic personas",
                    "Ad-supported sessions",
                    "Standard voice quality",
                    "Basic analytics"
                ],
                personas_included=["mindbot", "professor_oak", "sizzle", "zen_master"],
                custom_personas_allowed=0,
                ad_free=False,
                priority_support=False,
                advanced_analytics=False,
                max_daily_minutes=60
            ),
            "premium": PricingTier(
                id="premium",
                name="Premium",
                price_monthly=19.99,
                price_yearly=199.99,
                features=[
                    "Access to all personas",
                    "Ad-free experience",
                    "Premium voice quality",
                    "Create up to 3 custom personas",
                    "Priority support",
                    "Advanced analytics"
                ],
                personas_included=["mindbot", "professor_oak", "sizzle", "zen_master", 
                                  "blaze", "pixel", "deal_closer", "code_wizard"],
                custom_personas_allowed=3,
                ad_free=True,
                priority_support=True,
                advanced_analytics=True
            ),
            "exclusive": PricingTier(
                id="exclusive",
                name="Exclusive",
                price_monthly=49.99,
                price_yearly=499.99,
                features=[
                    "Access to all personas including exclusive ones",
                    "Ad-free experience",
                    "Highest voice quality",
                    "Unlimited custom personas",
                    "Priority support with dedicated account manager",
                    "Advanced analytics and insights",
                    "Early access to new personas",
                    "Custom voice options"
                ],
                personas_included=["*"],  # All personas
                custom_personas_allowed=999,  # Unlimited
                ad_free=True,
                priority_support=True,
                advanced_analytics=True
            )
        }
    
    def _initialize_ad_config(self) -> Dict[str, Any]:
        """Initialize ad configuration"""
        return {
            "ad_types": {
                "banner": {
                    "display_time": 10,  # seconds
                    "revenue_per_view": 0.01,
                    "revenue_per_click": 0.05
                },
                "video": {
                    "display_time": 15,  # seconds
                    "revenue_per_view": 0.05,
                    "revenue_per_completion": 0.15
                },
                "sponsored_message": {
                    "display_time": 5,  # seconds
                    "revenue_per_view": 0.02,
                    "revenue_per_interaction": 0.10
                }
            },
            "ad_frequency": {
                "free_tier": 3,  # Every 3 interactions
                "reduced_tier": 6  # Every 6 interactions
            },
            "reward_options": {
                "watch_ad_for_time": {
                    "ad_length": 30,  # seconds
                    "time_reward": 5  # minutes
                },
                "watch_ad_for_discount": {
                    "ad_length": 15,  # seconds
                    "discount_percent": 50  # 50% off next session
                }
            }
        }
    
    async def get_user_segment(self, user_id: str) -> UserSegment:
        """Determine user segment based on behavior"""
        # In production, analyze user behavior from database
        # For now, return default segment
        return UserSegment.CASUAL
    
    async def get_optimal_pricing(self, user_id: str, persona_slug: str) -> Dict[str, Any]:
        """Get optimal pricing for user and persona"""
        user_segment = await self.get_user_segment(user_id)
        
        # Base pricing
        base_price = 10.0  # $10/hour
        
        # Segment adjustments
        segment_multipliers = {
            UserSegment.NEW: 0.8,        # 20% discount for new users
            UserSegment.CASUAL: 1.0,     # Standard pricing
            UserSegment.REGULAR: 0.9,    # 10% discount for regular users
            UserSegment.POWER: 0.85,     # 15% discount for power users
            UserSegment.BUSINESS: 1.2,   # 20% premium for business users
            UserSegment.EDUCATIONAL: 0.7, # 30% discount for educational
            UserSegment.ENTERPRISE: 1.5  # 50% premium for enterprise
        }
        
        # Apply segment multiplier
        adjusted_price = base_price * segment_multipliers.get(user_segment, 1.0)
        
        # Persona-specific adjustments would be applied here
        
        return {
            "base_price_per_hour": base_price,
            "adjusted_price_per_hour": adjusted_price,
            "user_segment": user_segment.value,
            "available_discounts": self._get_available_discounts(user_id, user_segment),
            "subscription_recommendation": self._get_subscription_recommendation(user_id, user_segment)
        }
    
    def _get_available_discounts(self, user_id: str, segment: UserSegment) -> List[Dict[str, Any]]:
        """Get available discounts for user"""
        discounts = []
        
        # New user discount
        if segment == UserSegment.NEW:
            discounts.append({
                "id": "new_user_discount",
                "name": "New User Special",
                "description": "50% off your first time card purchase",
                "discount_percent": 50,
                "expires_in_days": 7
            })
        
        # Volume discount
        if segment in [UserSegment.REGULAR, UserSegment.POWER]:
            discounts.append({
                "id": "volume_discount",
                "name": "Regular User Discount",
                "description": "15% off when you purchase 10+ hours",
                "discount_percent": 15,
                "minimum_purchase_hours": 10
            })
        
        # Educational discount
        if segment == UserSegment.EDUCATIONAL:
            discounts.append({
                "id": "edu_discount",
                "name": "Educational Discount",
                "description": "30% off for educational use",
                "discount_percent": 30
            })
        
        return discounts
    
    def _get_subscription_recommendation(self, user_id: str, segment: UserSegment) -> Dict[str, Any]:
        """Get personalized subscription recommendation"""
        if segment == UserSegment.NEW or segment == UserSegment.CASUAL:
            return {
                "recommended_tier": "premium",
                "reason": "Unlock all personas and remove ads",
                "savings_estimate": "$15/month compared to pay-as-you-go"
            }
        elif segment == UserSegment.REGULAR or segment == UserSegment.POWER:
            return {
                "recommended_tier": "exclusive",
                "reason": "Unlimited custom personas and highest quality",
                "savings_estimate": "$30/month compared to premium tier usage"
            }
        elif segment == UserSegment.BUSINESS or segment == UserSegment.ENTERPRISE:
            return {
                "recommended_tier": "enterprise_contact",
                "reason": "Custom enterprise plan for your organization",
                "contact_email": "enterprise@mindbot.ai"
            }
        else:
            return {
                "recommended_tier": "premium",
                "reason": "Best value for most users",
                "savings_estimate": "$10/month compared to pay-as-you-go"
            }
    
    async def track_revenue_event(self, event_type: str, user_id: str, amount: float, metadata: Dict[str, Any] = None):
        """Track revenue event for analytics"""
        event = {
            "event_type": event_type,
            "user_id": user_id,
            "amount": amount,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        # Update revenue metrics
        self.revenue_metrics["total_revenue"] += amount
        
        if event_type == "subscription_payment":
            self.revenue_metrics["subscription_revenue"] += amount
        elif event_type == "time_card_purchase":
            self.revenue_metrics["time_card_revenue"] += amount
        elif event_type == "ad_revenue":
            self.revenue_metrics["ad_revenue"] += amount
        elif event_type == "custom_persona_creation":
            self.revenue_metrics["custom_persona_revenue"] += amount
        
        # In production, store in database
        logger.info(f"Revenue event: {event}")
    
    async def get_revenue_metrics(self, period: str = "month") -> Dict[str, Any]:
        """Get revenue metrics for specified period"""
        # In production, calculate from database
        return self.revenue_metrics
    
    async def get_conversion_recommendations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get personalized conversion recommendations for user"""
        user_segment = await self.get_user_segment(user_id)
        
        recommendations = []
        
        if user_segment == UserSegment.NEW:
            recommendations.append({
                "type": "first_purchase",
                "title": "Try your first time card",
                "description": "Get 50% off your first time card purchase",
                "action": "Purchase with discount",
                "discount_code": "FIRSTTIME50"
            })
        
        if user_segment == UserSegment.CASUAL:
            recommendations.append({
                "type": "subscription_upsell",
                "title": "Upgrade to Premium",
                "description": "Unlimited access to all personas for one low monthly price",
                "action": "See Premium benefits",
                "highlight": True
            })
        
        if user_segment == UserSegment.REGULAR:
            recommendations.append({
                "type": "bulk_purchase",
                "title": "Save with bulk purchase",
                "description": "Buy 10 hours and save 15%",
                "action": "See bulk options",
                "discount_code": "BULK15"
            })
        
        return recommendations
    
    async def get_ad_configuration(self, user_id: str, user_tier: str) -> Dict[str, Any]:
        """Get ad configuration for user"""
        if user_tier != "free":
            return {"ads_enabled": False}
        
        # For free tier users
        return {
            "ads_enabled": True,
            "ad_frequency": self.ad_config["ad_frequency"]["free_tier"],
            "ad_types": list(self.ad_config["ad_types"].keys()),
            "reward_options": self.ad_config["reward_options"]
        }
    
    async def calculate_lifetime_value(self, user_id: str) -> Dict[str, Any]:
        """Calculate customer lifetime value"""
        # In production, analyze user's purchase history
        return {
            "current_ltv": 127.50,
            "projected_ltv": 350.00,
            "retention_probability": 0.85,
            "recommended_actions": [
                "Offer premium upgrade",
                "Suggest bulk time purchase",
                "Highlight exclusive personas"
            ]
        }

# Global instance
revenue_optimizer = RevenueOptimizer()