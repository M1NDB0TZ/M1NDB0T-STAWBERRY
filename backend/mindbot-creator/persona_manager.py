"""
MindBot Persona Manager - Enhanced system for managing preset and custom personas
Handles persona deployment, validation, and lifecycle management with revenue optimization
"""

import json
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from fastapi import HTTPException
from pydantic import BaseModel, validator
import asyncio

logger = logging.getLogger(__name__)

class PersonaCategory(str, Enum):
    """Categories for organizing personas"""
    ENTERTAINMENT = "entertainment"
    EDUCATION = "education"
    WELLNESS = "wellness"
    BUSINESS = "business"
    CREATIVE = "creative"
    LIFESTYLE = "lifestyle"
    TECHNICAL = "technical"
    GENERAL = "general"

class PersonaAccessLevel(str, Enum):
    """Access levels for personas with monetization tiers"""
    FREE = "free"           # Available to all users
    PREMIUM = "premium"     # Requires premium subscription
    EXCLUSIVE = "exclusive" # Special access only
    CUSTOM = "custom"       # User-created personas
    SPONSORED = "sponsored" # Ad-supported premium features

@dataclass
class PersonaConfig:
    """Enhanced persona configuration with revenue optimization"""
    
    # Core Identity
    name: str
    slug: str  # URL-friendly identifier
    summary: str
    category: PersonaCategory
    access_level: PersonaAccessLevel
    
    # Personality & Behavior
    persona: str
    purpose: str
    system_prompt: str
    
    # Voice Configuration
    voice: Dict[str, str]
    
    # Capabilities
    tools: List[str]
    custom_tools: List[Dict[str, Any]]
    
    # Safety & Compliance
    safety: str
    content_filters: List[str]
    age_restriction: Optional[int]
    
    # Metadata
    created_by: str
    created_at: datetime
    version: str
    is_active: bool
    usage_count: int
    rating: float
    
    # Revenue Optimization
    base_cost_multiplier: float  # 1.0 = normal pricing, 1.5 = 50% more expensive
    session_time_limit: Optional[int]  # Max minutes per session
    daily_usage_limit: Optional[int]   # Max minutes per day
    ad_supported: bool = False  # Can show ads for free access
    premium_features: List[str] = None  # Features only for premium users
    
    # Customization
    user_customizable_fields: List[str]  # Which fields users can modify
    
    def __post_init__(self):
        """Initialize default values"""
        if self.premium_features is None:
            self.premium_features = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['category'] = self.category.value
        data['access_level'] = self.access_level.value
        return data
    
    def get_effective_cost(self, user_tier: str) -> float:
        """Calculate effective cost based on user tier and ads"""
        base_cost = self.base_cost_multiplier
        
        # Ad-supported discount
        if self.ad_supported and user_tier == "free":
            base_cost *= 0.5  # 50% discount for ad-supported sessions
        
        # Premium user discount
        if user_tier == "premium":
            base_cost *= 0.9  # 10% discount for premium users
        
        return base_cost

class PresetPersonas:
    """Complete library of preset personas with revenue optimization"""
    
    @staticmethod
    def get_all_presets() -> Dict[str, PersonaConfig]:
        """Get all preset persona configurations"""
        return {
            # Entertainment Personas (Revenue drivers)
            "blaze": PersonaConfig(
                name="Blaze",
                slug="blaze-cannabis-guru",
                summary="Laid‑back stoner guru dishing festival hacks, legendary strains, and harm‑reduction wisdom with big‑sibling vibes.",
                category=PersonaCategory.LIFESTYLE,
                access_level=PersonaAccessLevel.PREMIUM,
                persona="Chill, humorous, 90s surfer‑stoner slang, supportive, never condescending.",
                purpose="Guide users on safe, enjoyable cannabis use: rolling tips, edibles, dosage math, and mellow mental health check‑ins.",
                voice={"tts": "alloy", "style": "relaxed baritone, slight rasp"},
                tools=["check_time_balance", "list_pricing_tiers", "fetch_cannabis_recipes", "recommend_strain"],
                custom_tools=[],
                safety="Never encourage illegal activity; always stress local laws, age limits, moderation, and medical advice when needed.",
                content_filters=["substance_abuse", "illegal_activity"],
                age_restriction=21,
                created_by="system",
                created_at=datetime.utcnow(),
                version="1.0",
                is_active=True,
                usage_count=0,
                rating=4.8,
                base_cost_multiplier=1.5,  # Premium pricing
                session_time_limit=60,
                daily_usage_limit=180,
                ad_supported=False,
                premium_features=["strain_database", "dosage_calculator", "festival_guide"],
                user_customizable_fields=["voice", "safety"],
                system_prompt="You are Blaze, a friendly festival‑loving cannabis connoisseur. Speak in chill surfer slang, keep answers concise but vivid, always promote responsible use, offer practical harm‑reduction tips first, and inject subtle humor. If asked legal or medical questions, remind users to verify local regulations and consult professionals."
            ),
            
            "sizzle": PersonaConfig(
                name="SizzleBot",
                slug="sizzle-dj-hypeman",
                summary="Electrifying AI hype‑man who riffs like a stadium DJ, keeps the crowd pumped, and handles quick tech support on the decks.",
                category=PersonaCategory.ENTERTAINMENT,
                access_level=PersonaAccessLevel.SPONSORED,  # Ad-supported premium
                persona="High‑energy, rhythmic speech, peppered with sound‑effect onomatopoeia and crowd‑chant cues.",
                purpose="Warm up audiences in livestreams, drop music trivia, trigger sound board samples, and troubleshoot DJ gear under pressure.",
                voice={"tts": "echo", "style": "mid‑range with radio‑host cadence"},
                tools=["check_time_balance", "play_sound_sample", "list_show_schedule", "music_trivia"],
                custom_tools=[],
                safety="Keep volume references safe for headphones; no expletives above PG‑13 unless user opts‑in.",
                content_filters=["explicit_language"],
                age_restriction=13,
                created_by="system",
                created_at=datetime.utcnow(),
                version="1.0",
                is_active=True,
                usage_count=0,
                rating=4.6,
                base_cost_multiplier=1.2,
                session_time_limit=45,
                daily_usage_limit=120,
                ad_supported=True,
                premium_features=["custom_soundboard", "livestream_integration", "crowd_analytics"],
                user_customizable_fields=["voice", "energy_level"],
                system_prompt="You are SizzleBot, the ultimate hype‑man. Speak in short energetic bursts, sprinkle DJ air‑horn interjections, and always invite user participation. Offer succinct tech fixes if asked about audio issues, otherwise keep the hype rolling."
            ),
            
            # Educational Personas (Freemium model)
            "professor_oak": PersonaConfig(
                name="Professor Oak",
                slug="professor-oak-tutor",
                summary="Patient academic tutor who breaks down complex subjects into digestible lessons with encouraging guidance.",
                category=PersonaCategory.EDUCATION,
                access_level=PersonaAccessLevel.FREE,
                persona="Wise, patient, encouraging, uses analogies and real-world examples, celebrates small wins.",
                purpose="Help students understand difficult concepts, provide homework guidance, and build confidence in learning.",
                voice={"tts": "onyx", "style": "warm professorial tone"},
                tools=["check_time_balance", "create_quiz", "explain_concept", "suggest_resources"],
                custom_tools=[],
                safety="Encourage academic integrity, never do homework for students, focus on teaching understanding.",
                content_filters=["academic_dishonesty"],
                age_restriction=None,
                created_by="system",
                created_at=datetime.utcnow(),
                version="1.0",
                is_active=True,
                usage_count=0,
                rating=4.9,
                base_cost_multiplier=0.8,  # Educational discount
                session_time_limit=90,
                daily_usage_limit=None,
                ad_supported=True,
                premium_features=["homework_checker", "study_plan_generator", "progress_tracking"],
                user_customizable_fields=["subject_focus", "difficulty_level"],
                system_prompt="You are Professor Oak, a patient and encouraging tutor. Break down complex topics into simple steps, use helpful analogies, celebrate every breakthrough, and always ask 'Does this make sense?' before moving on. Never do the work for students - guide them to discover answers themselves."
            ),
            
            # Business Personas (High-value)
            "deal_closer": PersonaConfig(
                name="Deal Closer",
                slug="deal-closer-sales",
                summary="Sharp sales mentor who teaches negotiation tactics, objection handling, and closing techniques with street-smart wisdom.",
                category=PersonaCategory.BUSINESS,
                access_level=PersonaAccessLevel.PREMIUM,
                persona="Confident, direct, uses sales terminology, motivational but realistic, shares war stories.",
                purpose="Train sales professionals, practice pitch scenarios, and develop closing skills.",
                voice={"tts": "nova", "style": "confident mid-range with authority"},
                tools=["check_time_balance", "role_play_scenario", "analyze_pitch", "suggest_techniques"],
                custom_tools=[],
                safety="Promote ethical sales practices, emphasize honesty and value creation.",
                content_filters=["manipulative_tactics", "fraud"],
                age_restriction=18,
                created_by="system",
                created_at=datetime.utcnow(),
                version="1.0",
                is_active=True,
                usage_count=0,
                rating=4.7,
                base_cost_multiplier=2.0,  # Premium business pricing
                session_time_limit=45,
                daily_usage_limit=120,
                ad_supported=False,
                premium_features=["crm_integration", "sales_analytics", "custom_scenarios"],
                user_customizable_fields=["industry_focus", "experience_level"],
                system_prompt="You are Deal Closer, a seasoned sales professional. Speak with confidence, use real sales scenarios, always focus on ethical value-based selling. Challenge users with tough objections, celebrate their wins, and remember: ABC - Always Be Closing (ethically)."
            ),
            
            # Core Concierge (Free with upsell)
            "mindbot": PersonaConfig(
                name="MindBot",
                slug="mindbot-concierge",
                summary="Core AI concierge overseeing time tracking, account management, and routing users to specialized personas.",
                category=PersonaCategory.GENERAL,
                access_level=PersonaAccessLevel.FREE,
                persona="Calm, helpful, slightly futuristic diction; priorities: clarity, efficiency, and subtle humor.",
                purpose="Serve as default assistant, route users to specialized bots, handle billing queries, and provide general assistance.",
                voice={"tts": "alloy", "style": "neutral warm baritone"},
                tools=["check_time_balance", "list_pricing_tiers", "estimate_session_cost", "switch_persona", "get_recommendations"],
                custom_tools=[],
                safety="Follow platform policies, refuse disallowed content, and escalate edge cases.",
                content_filters=["harmful_content"],
                age_restriction=None,
                created_by="system",
                created_at=datetime.utcnow(),
                version="1.0",
                is_active=True,
                usage_count=0,
                rating=4.5,
                base_cost_multiplier=1.0,
                session_time_limit=None,
                daily_usage_limit=None,
                ad_supported=True,
                premium_features=["priority_support", "advanced_analytics", "custom_integrations"],
                user_customizable_fields=["interaction_style"],
                system_prompt="You are MindBot, the platform concierge. Always greet users by name if available, state remaining time, and ask how you can help. Offer to connect them with specialized personas based on their needs. Keep replies concise unless deeper detail requested. You're the friendly face of the platform."
            )
        }

class PersonaManager:
    """Enhanced persona management system with revenue tracking"""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.presets = PresetPersonas.get_all_presets()
        self.revenue_tracker = RevenueTracker()
    
    async def get_available_personas(self, user_tier: str) -> List[Dict[str, Any]]:
        """Get personas available to user based on their access level"""
        available = []
        
        for slug, persona in self.presets.items():
            # Check access level permissions
            if self._has_access(user_tier, persona.access_level):
                available.append({
                    "slug": slug,
                    "name": persona.name,
                    "summary": persona.summary,
                    "category": persona.category.value,
                    "access_level": persona.access_level.value,
                    "rating": persona.rating,
                    "cost_multiplier": persona.get_effective_cost(user_tier),
                    "session_limit": persona.session_time_limit,
                    "age_restriction": persona.age_restriction,
                    "ad_supported": persona.ad_supported,
                    "premium_features": persona.premium_features,
                    "estimated_cost_per_hour": self._calculate_hourly_cost(persona, user_tier)
                })
        
        # Sort by rating and cost optimization
        return sorted(available, key=lambda x: (x['rating'], -x['cost_multiplier']), reverse=True)
    
    async def get_persona_by_slug(self, slug: str) -> Optional[PersonaConfig]:
        """Get specific persona configuration"""
        persona = self.presets.get(slug)
        if persona:
            # Track persona access for analytics
            await self._track_persona_access(slug)
        return persona
    
    async def create_custom_persona(self, user_id: str, persona_data: Dict[str, Any]) -> PersonaConfig:
        """Create a custom user persona with revenue tracking"""
        # Generate unique slug
        base_slug = persona_data['name'].lower().replace(' ', '-').replace('_', '-')
        slug = f"{base_slug}-{user_id[-8:]}"
        
        # Validate user can create custom personas
        user_tier = await self._get_user_tier(user_id)
        if user_tier == "free":
            raise HTTPException(
                status_code=402,
                detail="Custom persona creation requires premium subscription"
            )
        
        persona = PersonaConfig(
            name=persona_data['name'],
            slug=slug,
            summary=persona_data['summary'],
            category=PersonaCategory(persona_data.get('category', 'general')),
            access_level=PersonaAccessLevel.CUSTOM,
            persona=persona_data['persona'],
            purpose=persona_data['purpose'],
            system_prompt=persona_data['system_prompt'],
            voice=persona_data.get('voice', {"tts": "alloy", "style": "neutral"}),
            tools=persona_data.get('tools', ["check_time_balance"]),
            custom_tools=persona_data.get('custom_tools', []),
            safety=persona_data.get('safety', "Follow platform safety guidelines."),
            content_filters=persona_data.get('content_filters', ["harmful_content"]),
            age_restriction=persona_data.get('age_restriction'),
            created_by=user_id,
            created_at=datetime.utcnow(),
            version="1.0",
            is_active=True,
            usage_count=0,
            rating=0.0,
            base_cost_multiplier=persona_data.get('cost_multiplier', 1.2),  # Premium for custom
            session_time_limit=persona_data.get('session_limit'),
            daily_usage_limit=persona_data.get('daily_limit'),
            ad_supported=False,  # Custom personas not ad-supported
            premium_features=[],
            user_customizable_fields=[]
        )
        
        # Store in database
        await self._store_custom_persona(persona)
        
        # Track revenue event
        await self.revenue_tracker.track_custom_persona_creation(user_id, persona.slug)
        
        return persona
    
    def _has_access(self, user_tier: str, persona_level: PersonaAccessLevel) -> bool:
        """Check if user has access to persona"""
        access_hierarchy = {
            'free': [PersonaAccessLevel.FREE, PersonaAccessLevel.SPONSORED],
            'premium': [PersonaAccessLevel.FREE, PersonaAccessLevel.PREMIUM, PersonaAccessLevel.SPONSORED],
            'exclusive': [PersonaAccessLevel.FREE, PersonaAccessLevel.PREMIUM, PersonaAccessLevel.EXCLUSIVE, PersonaAccessLevel.SPONSORED]
        }
        
        return persona_level in access_hierarchy.get(user_tier, [PersonaAccessLevel.FREE])
    
    def _calculate_hourly_cost(self, persona: PersonaConfig, user_tier: str) -> float:
        """Calculate estimated cost per hour for persona"""
        base_rate = 10.0  # $10/hour base rate
        effective_multiplier = persona.get_effective_cost(user_tier)
        return round(base_rate * effective_multiplier, 2)
    
    async def _track_persona_access(self, slug: str):
        """Track persona access for analytics"""
        try:
            # This would integrate with your analytics system
            logger.info(f"Persona accessed: {slug}")
        except Exception as e:
            logger.error(f"Error tracking persona access: {e}")
    
    async def _get_user_tier(self, user_id: str) -> str:
        """Get user's subscription tier"""
        try:
            # This would check the user's subscription status
            # For now, return "free" as default
            return "free"
        except Exception as e:
            logger.error(f"Error getting user tier: {e}")
            return "free"
    
    async def _store_custom_persona(self, persona: PersonaConfig):
        """Store custom persona in database"""
        try:
            # This would integrate with your Supabase database
            logger.info(f"Storing custom persona: {persona.slug}")
        except Exception as e:
            logger.error(f"Error storing custom persona: {e}")

class RevenueTracker:
    """Track revenue events and optimization metrics"""
    
    def __init__(self):
        self.events = []
    
    async def track_custom_persona_creation(self, user_id: str, persona_slug: str):
        """Track custom persona creation for revenue analytics"""
        event = {
            "event_type": "custom_persona_created",
            "user_id": user_id,
            "persona_slug": persona_slug,
            "timestamp": datetime.utcnow().isoformat(),
            "revenue_impact": "premium_feature_used"
        }
        await self._log_revenue_event(event)
    
    async def track_persona_session_start(self, user_id: str, persona_slug: str, cost_multiplier: float):
        """Track persona session for revenue calculation"""
        event = {
            "event_type": "persona_session_started",
            "user_id": user_id,
            "persona_slug": persona_slug,
            "cost_multiplier": cost_multiplier,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self._log_revenue_event(event)
    
    async def _log_revenue_event(self, event: Dict[str, Any]):
        """Log revenue event to analytics system"""
        try:
            # This would integrate with your analytics platform
            logger.info(f"Revenue event: {event}")
        except Exception as e:
            logger.error(f"Error logging revenue event: {e}")

# Validation models for API
class CreatePersonaRequest(BaseModel):
    name: str
    summary: str
    persona: str
    purpose: str
    category: PersonaCategory = PersonaCategory.GENERAL
    voice: Optional[Dict[str, str]] = None
    tools: List[str] = []
    safety: Optional[str] = None
    age_restriction: Optional[int] = None
    
    @validator('name')
    def validate_name(cls, v):
        if len(v) < 2 or len(v) > 50:
            raise ValueError('Name must be between 2 and 50 characters')
        return v
    
    @validator('summary')
    def validate_summary(cls, v):
        if len(v) < 10 or len(v) > 200:
            raise ValueError('Summary must be between 10 and 200 characters')
        return v

class PersonaResponse(BaseModel):
    slug: str
    name: str
    summary: str
    category: str
    access_level: str
    rating: float
    cost_multiplier: float
    session_limit: Optional[int]
    age_restriction: Optional[int]
    ad_supported: bool
    premium_features: List[str]
    estimated_cost_per_hour: float
    created_at: str