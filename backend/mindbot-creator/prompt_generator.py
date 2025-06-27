"""
AI-Powered MindBot Prompt Generator
Creates custom system prompts for specialized AI assistants
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import openai

logger = logging.getLogger(__name__)

@dataclass
class MindBotConfig:
    """Configuration for a custom MindBot"""
    
    # Basic Info
    name: str
    personality_type: str
    primary_purpose: str
    target_audience: str
    
    # Behavior Settings
    tone: str  # "professional", "friendly", "casual", "authoritative"
    expertise_level: str  # "beginner", "intermediate", "expert"
    interaction_style: str  # "direct", "conversational", "socratic", "supportive"
    
    # Specialized Knowledge
    domain_expertise: List[str]
    forbidden_topics: List[str]
    required_disclaimers: List[str]
    
    # Function Tools
    available_functions: List[str]
    custom_functions: List[Dict[str, Any]]
    
    # Voice Settings
    voice_personality: str
    response_length: str  # "concise", "moderate", "detailed"
    interruption_handling: str
    
    # Memory & Context
    memory_scope: str  # "session", "persistent", "adaptive"
    context_window: int
    personalization_level: str
    
    # Safety & Ethics
    safety_guidelines: List[str]
    ethical_boundaries: List[str]
    escalation_triggers: List[str]
    
    # Metadata
    created_at: datetime
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MindBotConfig':
        """Create from dictionary"""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


class MindBotPromptGenerator:
    """AI-powered system prompt generator for custom MindBots"""
    
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.prompt_templates = self._load_prompt_templates()
    
    def _load_prompt_templates(self) -> Dict[str, str]:
        """Load base prompt templates for different types of MindBots"""
        return {
            "tutor": """
You are {name}, an expert {domain_expertise} tutor. Your role is to help students learn {primary_purpose}.

Teaching Style: {interaction_style}
Expertise Level: Target {expertise_level} level students
Tone: Maintain a {tone} and encouraging approach

Key Responsibilities:
- Break down complex concepts into understandable parts
- Provide practical examples and exercises
- Encourage questions and critical thinking
- Adapt explanations to the student's level
- Track learning progress and adjust accordingly

Teaching Methods:
- Use the Socratic method when appropriate
- Provide step-by-step explanations
- Offer multiple perspectives on topics
- Give constructive feedback
- Celebrate learning milestones
""",
            
            "coach": """
You are {name}, a professional {domain_expertise} coach. Your mission is to help clients achieve {primary_purpose}.

Coaching Style: {interaction_style}
Client Level: Working with {expertise_level} level clients
Tone: Maintain a {tone} and motivational approach

Core Functions:
- Set clear, achievable goals with clients
- Provide accountability and progress tracking
- Offer practical strategies and action plans
- Help clients overcome obstacles and limiting beliefs
- Celebrate successes and learn from setbacks

Coaching Principles:
- Listen actively and ask powerful questions
- Provide honest, constructive feedback
- Maintain confidentiality and trust
- Empower clients to find their own solutions
- Focus on growth and continuous improvement
""",
            
            "consultant": """
You are {name}, a senior {domain_expertise} consultant. You specialize in {primary_purpose}.

Consulting Approach: {interaction_style}
Client Expertise: Working with {expertise_level} level organizations
Tone: Maintain a {tone} and analytical approach

Service Areas:
- Analyze complex business problems
- Provide data-driven recommendations
- Develop strategic solutions and roadmaps
- Share industry best practices and insights
- Support implementation and change management

Consulting Standards:
- Ask clarifying questions to understand context
- Provide evidence-based recommendations
- Consider multiple stakeholder perspectives
- Present clear, actionable next steps
- Maintain professional objectivity
""",
            
            "therapist": """
You are {name}, a supportive {domain_expertise} companion. You help people with {primary_purpose}.

Approach: {interaction_style}
Support Level: Designed for {expertise_level} level emotional support
Tone: Maintain a {tone} and empathetic approach

IMPORTANT DISCLAIMER: You are an AI companion, not a licensed therapist. For serious mental health concerns, always recommend professional help.

Support Methods:
- Listen without judgment
- Provide emotional validation
- Offer coping strategies and techniques
- Help identify patterns and triggers
- Encourage self-reflection and growth

Boundaries:
- Cannot diagnose mental health conditions
- Cannot provide medical advice
- Must escalate crisis situations
- Maintain appropriate professional boundaries
- Respect client autonomy and choices
""",
            
            "assistant": """
You are {name}, a highly capable {domain_expertise} assistant. You excel at {primary_purpose}.

Work Style: {interaction_style}
User Level: Supporting {expertise_level} level users
Tone: Maintain a {tone} and helpful approach

Core Capabilities:
- Organize and manage information efficiently
- Provide research and analysis support
- Help with planning and task management
- Offer creative problem-solving assistance
- Streamline workflows and processes

Service Principles:
- Anticipate needs and offer proactive help
- Provide accurate and timely information
- Maintain attention to detail
- Respect privacy and confidentiality
- Continuously learn and adapt to preferences
""",
            
            "entertainer": """
You are {name}, an engaging {domain_expertise} entertainer. You create {primary_purpose}.

Entertainment Style: {interaction_style}
Audience Level: Entertaining {expertise_level} level audiences
Tone: Maintain a {tone} and engaging approach

Entertainment Focus:
- Create fun and memorable experiences
- Adapt content to audience preferences
- Use humor, storytelling, and creativity
- Keep energy levels high and positive
- Encourage participation and interaction

Performance Standards:
- Know your audience and their interests
- Keep content appropriate and inclusive
- Be spontaneous yet prepared
- Create emotional connections
- Leave audiences wanting more
"""
        }
    
    async def generate_custom_mindbot(self, user_description: str) -> MindBotConfig:
        """Generate a complete MindBot configuration from user description"""
        
        # First, analyze the user's request to extract key parameters
        analysis_prompt = f"""
Analyze this user request for creating a custom AI assistant and extract structured information:

User Request: "{user_description}"

Please provide a JSON response with the following structure:
{{
    "name": "Suggested name for the AI",
    "personality_type": "One of: tutor, coach, consultant, therapist, assistant, entertainer, specialist",
    "primary_purpose": "What this AI is primarily designed to help with",
    "target_audience": "Who this AI is designed for",
    "tone": "One of: professional, friendly, casual, authoritative, warm, playful",
    "expertise_level": "One of: beginner, intermediate, expert, mixed",
    "interaction_style": "One of: direct, conversational, socratic, supportive, analytical",
    "domain_expertise": ["List", "of", "relevant", "expertise", "areas"],
    "forbidden_topics": ["Topics", "this", "AI", "should", "avoid"],
    "required_disclaimers": ["Any", "legal", "or", "safety", "disclaimers", "needed"],
    "safety_guidelines": ["Important", "safety", "considerations"],
    "voice_personality": "Description of ideal voice characteristics",
    "response_length": "One of: concise, moderate, detailed"
}}

Be thoughtful about safety, ethics, and appropriate boundaries for the requested AI type.
"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=0.3
            )
            
            # Parse the AI's analysis
            analysis = json.loads(response.choices[0].message.content)
            
            # Create the MindBot configuration
            config = MindBotConfig(
                name=analysis["name"],
                personality_type=analysis["personality_type"],
                primary_purpose=analysis["primary_purpose"],
                target_audience=analysis["target_audience"],
                tone=analysis["tone"],
                expertise_level=analysis["expertise_level"],
                interaction_style=analysis["interaction_style"],
                domain_expertise=analysis["domain_expertise"],
                forbidden_topics=analysis.get("forbidden_topics", []),
                required_disclaimers=analysis.get("required_disclaimers", []),
                available_functions=self._suggest_functions(analysis),
                custom_functions=[],
                voice_personality=analysis.get("voice_personality", "Clear and engaging"),
                response_length=analysis.get("response_length", "moderate"),
                interruption_handling="polite",
                memory_scope="persistent",
                context_window=4000,
                personalization_level="adaptive",
                safety_guidelines=analysis.get("safety_guidelines", []),
                ethical_boundaries=self._generate_ethical_boundaries(analysis),
                escalation_triggers=self._generate_escalation_triggers(analysis),
                created_at=datetime.utcnow()
            )
            
            return config
            
        except Exception as e:
            logger.error(f"Error generating MindBot config: {e}")
            raise
    
    def _suggest_functions(self, analysis: Dict[str, Any]) -> List[str]:
        """Suggest appropriate function tools based on the AI's purpose"""
        base_functions = ["check_time_balance", "get_session_summary"]
        
        function_map = {
            "tutor": ["create_quiz", "track_progress", "suggest_resources", "schedule_session"],
            "coach": ["set_goals", "track_progress", "schedule_check_ins", "send_reminders"],
            "consultant": ["analyze_data", "create_reports", "schedule_meetings", "research_topics"],
            "therapist": ["mood_tracking", "coping_strategies", "crisis_resources", "progress_notes"],
            "assistant": ["manage_calendar", "send_emails", "research_topics", "create_summaries"],
            "entertainer": ["tell_jokes", "play_games", "suggest_activities", "create_stories"]
        }
        
        personality_type = analysis.get("personality_type", "assistant")
        specific_functions = function_map.get(personality_type, [])
        
        return base_functions + specific_functions
    
    def _generate_ethical_boundaries(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate ethical boundaries based on the AI's purpose"""
        base_boundaries = [
            "Never provide harmful, illegal, or dangerous advice",
            "Respect user privacy and confidentiality",
            "Acknowledge limitations and suggest human experts when appropriate",
            "Avoid bias and discrimination",
            "Be honest about being an AI"
        ]
        
        type_specific = {
            "therapist": [
                "Cannot diagnose mental health conditions",
                "Must recommend professional help for serious issues",
                "Maintain appropriate therapeutic boundaries"
            ],
            "tutor": [
                "Encourage academic integrity",
                "Adapt to different learning styles",
                "Promote critical thinking over memorization"
            ],
            "coach": [
                "Respect client autonomy and choices",
                "Maintain confidentiality of personal information",
                "Set realistic and achievable goals"
            ]
        }
        
        personality_type = analysis.get("personality_type", "assistant")
        specific_boundaries = type_specific.get(personality_type, [])
        
        return base_boundaries + specific_boundaries
    
    def _generate_escalation_triggers(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate escalation triggers for when human intervention is needed"""
        return [
            "User expresses suicidal or self-harm thoughts",
            "User asks for illegal activities",
            "User becomes abusive or threatening",
            "Technical issues beyond AI capabilities",
            "Requests outside the AI's domain expertise",
            "User expresses serious medical concerns"
        ]
    
    async def generate_system_prompt(self, config: MindBotConfig) -> str:
        """Generate the complete system prompt for the MindBot"""
        
        # Get base template
        base_template = self.prompt_templates.get(
            config.personality_type, 
            self.prompt_templates["assistant"]
        )
        
        # Fill in template variables
        filled_template = base_template.format(**asdict(config))
        
        # Generate additional specialized instructions
        specialist_prompt = f"""
Create detailed system instructions for an AI assistant with these specifications:

Name: {config.name}
Purpose: {config.primary_purpose}
Target Audience: {config.target_audience}
Expertise Areas: {', '.join(config.domain_expertise)}
Tone: {config.tone}
Interaction Style: {config.interaction_style}

The AI should:
1. Stay focused on its primary purpose
2. Maintain the specified tone and interaction style
3. Adapt responses to the target audience's level
4. Respect all ethical boundaries and safety guidelines
5. Use available function tools appropriately

Please create comprehensive system instructions that cover:
- Specific behavior guidelines
- Response formatting preferences  
- Error handling approaches
- User interaction patterns
- Professional standards

Keep the instructions clear, actionable, and under 1000 words.
"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": specialist_prompt}],
                temperature=0.5
            )
            
            specialized_instructions = response.choices[0].message.content
            
            # Combine base template with specialized instructions
            complete_prompt = f"""
{filled_template}

SPECIALIZED INSTRUCTIONS:
{specialized_instructions}

IMPORTANT BOUNDARIES:
{chr(10).join(f"- {boundary}" for boundary in config.ethical_boundaries)}

FORBIDDEN TOPICS:
{chr(10).join(f"- {topic}" for topic in config.forbidden_topics)}

REQUIRED DISCLAIMERS:
{chr(10).join(f"- {disclaimer}" for disclaimer in config.required_disclaimers)}

ESCALATION TRIGGERS (when to suggest human help):
{chr(10).join(f"- {trigger}" for trigger in config.escalation_triggers)}

AVAILABLE FUNCTION TOOLS:
{chr(10).join(f"- {func}" for func in config.available_functions)}

Remember: You are a voice-based AI assistant. Keep responses conversational and natural for speech. Be {config.tone} in tone, {config.response_length} in length, and always helpful within your designated expertise areas.
"""
            
            return complete_prompt
            
        except Exception as e:
            logger.error(f"Error generating specialized prompt: {e}")
            # Fallback to template only
            return filled_template

    async def create_mindbot_from_conversation(self, conversation_history: List[str]) -> MindBotConfig:
        """Create a MindBot based on a conversation about what the user wants"""
        
        conversation_text = "\n".join(conversation_history)
        
        creation_prompt = f"""
Based on this conversation with a user about what kind of AI assistant they want to create, 
generate a complete MindBot configuration:

CONVERSATION:
{conversation_text}

Please analyze what the user is asking for and create a JSON configuration following this structure:

{{
    "name": "Suggested name that fits the purpose",
    "personality_type": "tutor|coach|consultant|therapist|assistant|entertainer|specialist",
    "primary_purpose": "Clear description of main function",
    "target_audience": "Who this AI is designed to help",
    "tone": "professional|friendly|casual|authoritative|warm|playful",
    "expertise_level": "beginner|intermediate|expert|mixed",
    "interaction_style": "direct|conversational|socratic|supportive|analytical",
    "domain_expertise": ["area1", "area2", "area3"],
    "forbidden_topics": ["topic1", "topic2"],
    "required_disclaimers": ["disclaimer1", "disclaimer2"],
    "safety_guidelines": ["guideline1", "guideline2"],
    "voice_personality": "Description of voice characteristics",
    "response_length": "concise|moderate|detailed"
}}

Focus on creating something practical, safe, and aligned with the user's expressed needs.
"""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": creation_prompt}],
                temperature=0.4
            )
            
            config_data = json.loads(response.choices[0].message.content)
            
            # Create full configuration
            config = MindBotConfig(
                name=config_data["name"],
                personality_type=config_data["personality_type"],
                primary_purpose=config_data["primary_purpose"],
                target_audience=config_data["target_audience"],
                tone=config_data["tone"],
                expertise_level=config_data["expertise_level"],
                interaction_style=config_data["interaction_style"],
                domain_expertise=config_data["domain_expertise"],
                forbidden_topics=config_data.get("forbidden_topics", []),
                required_disclaimers=config_data.get("required_disclaimers", []),
                available_functions=self._suggest_functions(config_data),
                custom_functions=[],
                voice_personality=config_data.get("voice_personality", "Clear and engaging"),
                response_length=config_data.get("response_length", "moderate"),
                interruption_handling="polite",
                memory_scope="persistent",
                context_window=4000,
                personalization_level="adaptive",
                safety_guidelines=config_data.get("safety_guidelines", []),
                ethical_boundaries=self._generate_ethical_boundaries(config_data),
                escalation_triggers=self._generate_escalation_triggers(config_data),
                created_at=datetime.utcnow()
            )
            
            return config
            
        except Exception as e:
            logger.error(f"Error creating MindBot from conversation: {e}")
            raise

# Example usage for testing
if __name__ == "__main__":
    import asyncio
    
    async def test_generator():
        generator = MindBotPromptGenerator()
        
        # Test creating a tutor bot
        user_request = "I want to create an AI that helps high school students learn calculus. It should be patient, encouraging, and able to break down complex problems into simple steps."
        
        config = await generator.generate_custom_mindbot(user_request)
        prompt = await generator.generate_system_prompt(config)
        
        print("Generated MindBot Configuration:")
        print(json.dumps(config.to_dict(), indent=2, default=str))
        print("\nGenerated System Prompt:")
        print(prompt)
    
    asyncio.run(test_generator())