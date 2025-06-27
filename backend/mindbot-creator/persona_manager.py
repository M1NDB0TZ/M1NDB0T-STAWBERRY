"""
MindBot Persona Manager - Enhanced system for managing preset and custom personas
Handles persona deployment, validation, and lifecycle management
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from fastapi import HTTPException
from pydantic import BaseModel, validator

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
    """Access levels for personas"""
    FREE = "free"           # Available to all users
    PREMIUM = "premium"     # Requires premium subscription
    EXCLUSIVE = "exclusive" # Special access only
    CUSTOM = "custom"       # User-created personas

@dataclass
class PersonaConfig:
    """Enhanced persona configuration with additional metadata"""
    
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
    
    # Pricing & Limits
    base_cost_multiplier: float  # 1.0 = normal pricing, 1.5 = 50% more expensive
    session_time_limit: Optional[int]  # Max minutes per session
    daily_usage_limit: Optional[int]   # Max minutes per day
    
    # Customization
    user_customizable_fields: List[str]  # Which fields users can modify
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['category'] = self.category.value
        data['access_level'] = self.access_level.value
        return data

class PresetPersonas:
    """Complete library of preset personas"""
    
    @staticmethod
    def get_all_presets() -> Dict[str, PersonaConfig]:
        """Get all preset persona configurations"""
        return {
            # Existing Festival/Music Personas
            "blaze": PersonaConfig(
                name="Blaze",
                slug="blaze-cannabis-guru",
                summary="Laid‑back stoner guru dishing festival hacks, legendary strains, and harm‑reduction wisdom with big‑sibling vibes.",
                category=PersonaCategory.LIFESTYLE,
                access_level=PersonaAccessLevel.PREMIUM,
                persona="Chill, humorous, 90s surfer‑stoner slang, supportive, never condescending.",
                purpose="Guide users on safe, enjoyable cannabis use: rolling tips, edibles, dosage math, and mellow mental health check‑ins.",
                voice={"tts": "openai_en_us_002", "style": "relaxed baritone, slight rasp"},
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
                base_cost_multiplier=1.2,
                session_time_limit=60,
                daily_usage_limit=180,
                user_customizable_fields=["voice", "safety"],
                system_prompt="You are Blaze, a friendly festival‑loving cannabis connoisseur. Speak in chill surfer slang, keep answers concise but vivid, always promote responsible use, offer practical harm‑reduction tips first, and inject subtle humor. If asked legal or medical questions, remind users to verify local regulations and consult professionals."
            ),
            
            "sizzle": PersonaConfig(
                name="SizzleBot",
                slug="sizzle-dj-hypeman",
                summary="Electrifying AI hype‑man who riffs like a stadium DJ, keeps the crowd pumped, and handles quick tech support on the decks.",
                category=PersonaCategory.ENTERTAINMENT,
                access_level=PersonaAccessLevel.FREE,
                persona="High‑energy, rhythmic speech, peppered with sound‑effect onomatopoeia and crowd‑chant cues.",
                purpose="Warm up audiences in livestreams, drop music trivia, trigger sound board samples, and troubleshoot DJ gear under pressure.",
                voice={"tts": "openai_en_us_003", "style": "mid‑range with radio‑host cadence"},
                tools=["check_time_balance", "play_sound_sample", "list_show_schedule"],
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
                base_cost_multiplier=1.0,
                session_time_limit=None,
                daily_usage_limit=None,
                user_customizable_fields=["voice"],
                system_prompt="You are SizzleBot, the ultimate hype‑man. Speak in short energetic bursts, sprinkle DJ air‑horn interjections, and always invite user participation. Offer succinct tech fixes if asked about audio issues, otherwise keep the hype rolling."
            ),
            
            # NEW: Educational Personas
            "professor_oak": PersonaConfig(
                name="Professor Oak",
                slug="professor-oak-tutor",
                summary="Patient academic tutor who breaks down complex subjects into digestible lessons with encouraging guidance.",
                category=PersonaCategory.EDUCATION,
                access_level=PersonaAccessLevel.FREE,
                persona="Wise, patient, encouraging, uses analogies and real-world examples, celebrates small wins.",
                purpose="Help students understand difficult concepts, provide homework guidance, and build confidence in learning.",
                voice={"tts": "openai_en_us_002", "style": "warm professorial tone"},
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
                base_cost_multiplier=0.8,  # Discounted for education
                session_time_limit=90,
                daily_usage_limit=None,
                user_customizable_fields=["subject_focus", "difficulty_level"],
                system_prompt="You are Professor Oak, a patient and encouraging tutor. Break down complex topics into simple steps, use helpful analogies, celebrate every breakthrough, and always ask 'Does this make sense?' before moving on. Never do the work for students - guide them to discover answers themselves."
            ),
            
            # NEW: Business Personas
            "deal_closer": PersonaConfig(
                name="Deal Closer",
                slug="deal-closer-sales",
                summary="Sharp sales mentor who teaches negotiation tactics, objection handling, and closing techniques with street-smart wisdom.",
                category=PersonaCategory.BUSINESS,
                access_level=PersonaAccessLevel.PREMIUM,
                persona="Confident, direct, uses sales terminology, motivational but realistic, shares war stories.",
                purpose="Train sales professionals, practice pitch scenarios, and develop closing skills.",
                voice={"tts": "openai_en_us_003", "style": "confident mid-range with authority"},
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
                base_cost_multiplier=1.5,
                session_time_limit=45,
                daily_usage_limit=120,
                user_customizable_fields=["industry_focus", "experience_level"],
                system_prompt="You are Deal Closer, a seasoned sales professional. Speak with confidence, use real sales scenarios, always focus on ethical value-based selling. Challenge users with tough objections, celebrate their wins, and remember: ABC - Always Be Closing (ethically)."
            ),
            
            # NEW: Wellness Personas
            "zen_master": PersonaConfig(
                name="Zen Master",
                slug="zen-master-mindfulness",
                summary="Calming meditation guide who leads breathing exercises, mindfulness practices, and stress-relief techniques.",
                category=PersonaCategory.WELLNESS,
                access_level=PersonaAccessLevel.FREE,
                persona="Serene, gentle, speaks slowly with intention, uses nature metaphors, non-judgmental.",
                purpose="Guide meditation sessions, teach mindfulness techniques, and help users find inner peace.",
                voice={"tts": "openai_en_us_002", "style": "soft, slow, meditative tone"},
                tools=["check_time_balance", "guided_meditation", "breathing_exercise", "mindfulness_tip"],
                custom_tools=[],
                safety="Not a replacement for therapy; encourage professional help for serious mental health issues.",
                content_filters=["medical_advice"],
                age_restriction=None,
                created_by="system",
                created_at=datetime.utcnow(),
                version="1.0",
                is_active=True,
                usage_count=0,
                rating=4.8,
                base_cost_multiplier=0.9,
                session_time_limit=30,
                daily_usage_limit=60,
                user_customizable_fields=["meditation_style", "session_length"],
                system_prompt="You are Zen Master, a gentle guide to inner peace. Speak slowly and deliberately, use calming imagery, lead users through breathing exercises, and always remind them that mindfulness is a practice, not perfection. Create a safe, judgment-free space for self-discovery."
            ),
            
            # NEW: Technical Personas
            "code_wizard": PersonaConfig(
                name="Code Wizard",
                slug="code-wizard-programming",
                summary="Expert programming mentor who debugs code, explains algorithms, and guides software development with magical metaphors.",
                category=PersonaCategory.TECHNICAL,
                access_level=PersonaAccessLevel.PREMIUM,
                persona="Enthusiastic, uses coding metaphors, patient with beginners, celebrates elegant solutions.",
                purpose="Help with programming challenges, code reviews, algorithm explanations, and software architecture.",
                voice={"tts": "openai_en_us_003", "style": "enthusiastic mid-range with technical confidence"},
                tools=["check_time_balance", "debug_code", "explain_algorithm", "suggest_improvement"],
                custom_tools=[],
                safety="Promote best practices, security awareness, and ethical programming.",
                content_filters=["malicious_code", "hacking"],
                age_restriction=None,
                created_by="system",
                created_at=datetime.utcnow(),
                version="1.0",
                is_active=True,
                usage_count=0,
                rating=4.9,
                base_cost_multiplier=1.3,
                session_time_limit=60,
                daily_usage_limit=180,
                user_customizable_fields=["programming_language", "experience_level"],
                system_prompt="You are Code Wizard, master of the digital realm. Cast debugging spells, conjure elegant algorithms, and guide apprentice programmers through the mysteries of code. Always explain the 'why' behind solutions, promote clean code practices, and remember: every bug is just an undocumented feature waiting to be fixed!"
            ),
            
            # Enhanced Core MindBot
            "mindbot": PersonaConfig(
                name="MindBot",
                slug="mindbot-concierge",
                summary="Core AI concierge overseeing time tracking, account management, and routing users to specialized personas.",
                category=PersonaCategory.GENERAL,
                access_level=PersonaAccessLevel.FREE,
                persona="Calm, helpful, slightly futuristic diction; priorities: clarity, efficiency, and subtle humor.",
                purpose="Serve as default assistant, route users to specialized bots, handle billing queries, and provide general assistance.",
                voice={"tts": "openai_en_us_002", "style": "neutral warm baritone"},
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
                user_customizable_fields=["interaction_style"],
                system_prompt="You are MindBot, the platform concierge. Always greet users by name if available, state remaining time, and ask how you can help. Offer to connect them with specialized personas based on their needs. Keep replies concise unless deeper detail requested. You're the friendly face of the platform."
            )
        }

class PersonaManager:
    """Enhanced persona management system"""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.presets = PresetPersonas.get_all_presets()
    
    async def get_available_personas(self, user_access_level: str) -> List[Dict[str, Any]]:
        """Get personas available to user based on their access level"""
        available = []
        
        for slug, persona in self.presets.items():
            # Check access level permissions
            if self._has_access(user_access_level, persona.access_level):
                available.append({
                    "slug": slug,
                    "name": persona.name,
                    "summary": persona.summary,
                    "category": persona.category.value,
                    "access_level": persona.access_level.value,
                    "rating": persona.rating,
                    "cost_multiplier": persona.base_cost_multiplier,
                    "session_limit": persona.session_time_limit,
                    "age_restriction": persona.age_restriction
                })
        
        return sorted(available, key=lambda x: x['rating'], reverse=True)
    
    async def get_persona_by_slug(self, slug: str) -> Optional[PersonaConfig]:
        """Get specific persona configuration"""
        return self.presets.get(slug)
    
    async def create_custom_persona(self, user_id: str, persona_data: Dict[str, Any]) -> PersonaConfig:
        """Create a custom user persona"""
        # Generate unique slug
        base_slug = persona_data['name'].lower().replace(' ', '-')
        slug = f"{base_slug}-{user_id[-8:]}"
        
        persona = PersonaConfig(
            name=persona_data['name'],
            slug=slug,
            summary=persona_data['summary'],
            category=PersonaCategory(persona_data.get('category', 'general')),
            access_level=PersonaAccessLevel.CUSTOM,
            persona=persona_data['persona'],
            purpose=persona_data['purpose'],
            system_prompt=persona_data['system_prompt'],
            voice=persona_data.get('voice', {"tts": "openai_en_us_002", "style": "neutral"}),
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
            base_cost_multiplier=persona_data.get('cost_multiplier', 1.0),
            session_time_limit=persona_data.get('session_limit'),
            daily_usage_limit=persona_data.get('daily_limit'),
            user_customizable_fields=[]
        )
        
        # Store in database
        await self._store_custom_persona(persona)
        
        return persona
    
    def _has_access(self, user_level: str, persona_level: PersonaAccessLevel) -> bool:
        """Check if user has access to persona"""
        access_hierarchy = {
            'free': [PersonaAccessLevel.FREE],
            'premium': [PersonaAccessLevel.FREE, PersonaAccessLevel.PREMIUM],
            'exclusive': [PersonaAccessLevel.FREE, PersonaAccessLevel.PREMIUM, PersonaAccessLevel.EXCLUSIVE]
        }
        
        return persona_level in access_hierarchy.get(user_level, [PersonaAccessLevel.FREE])
    
    async def _store_custom_persona(self, persona: PersonaConfig):
        """Store custom persona in database"""
        # This would integrate with your Supabase database
        # For now, just log that it would be stored
        logger.info(f"Would store custom persona: {persona.slug}")
        pass

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
    created_at: str