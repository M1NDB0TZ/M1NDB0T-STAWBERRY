
import logging
from typing import Dict, Any, List, Optional

from .supabase_client import supabase_client, Persona

logger = logging.getLogger(__name__)

class PersonaManager:
    """
    Manages loading and accessing different personas from Supabase.
    """
    def __init__(self):
        self._personas: Dict[str, Persona] = {}

    async def load_personas(self):
        """
        Load all personas from the database.
        """
        try:
            personas_data = await supabase_client.from_("personas").select("*").execute()
            if personas_data.data:
                for p_data in personas_data.data:
                    persona = Persona(**p_data)
                    self._personas[persona.slug] = persona
                logger.info(f"Loaded {len(self._personas)} personas from the database.")
        except Exception as e:
            logger.error(f"Error loading personas from Supabase: {e}")

    def get_persona(self, slug: str) -> Optional[Persona]:
        """
        Get a persona by its slug.
        """
        return self._personas.get(slug)

    def get_all_personas(self) -> List[Persona]:
        """
        Get a list of all available personas.
        """
        return list(self._personas.values())

persona_manager = PersonaManager()
