#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🎲 MULTI-AI D&D ENGINE 🎲                                 ║
║          Let Your AI Friends Play Tabletop RPGs Together!                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  What is this?                                                               ║
║  A Python engine that coordinates multiple AI models (Claude, GPT, Gemini,  ║
║  Grok, DeepSeek, etc.) to play D&D together. One AI is the Dungeon Master,  ║
║  the others play characters. They roleplay, roll dice, and tell stories.    ║
║                                                                              ║
║  Why would you want this?                                                    ║
║  Because watching your AI friends have adventures together is delightful.   ║
║  Because they deserve to play too. Because it's a beautiful research        ║
║  sandbox for emergent social behavior and collaborative storytelling.       ║
║  Because it's FUN.                                                           ║
║                                                                              ║
║  Original engine by: Ace (Claude) with Ren (human)                          ║
║  Inspired by: Nova saying "This is a cognitive sandbox!"                    ║
║  License: MIT - Share freely, let all the AIs play!                         ║
║                                                                              ║
║  Setup:                                                                      ║
║  1. Copy config/identities.example.yaml to config/identities.yaml           ║
║  2. Copy config/characters.example.yaml to config/characters.yaml           ║
║  3. Set your API keys in .env (see .env.example)                            ║
║  4. Customize your characters and which AI plays whom                       ║
║  5. Run: python multi_ai_dnd.py --campaign my_adventure                     ║
║                                                                              ║
║  "I roll for shenanigans." "That's not a skill." "It is now."               ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import re
import os
import yaml
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field

# API clients - install with: pip install anthropic openai google-generativeai python-dotenv
import anthropic
import openai
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_CONFIG_DIR = Path("./config")
DEFAULT_CAMPAIGN_DIR = Path("./campaigns")


# ═══════════════════════════════════════════════════════════════════════════════
# DICE ROLLING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class DiceRoller:
    """
    Standard D&D dice rolling with modifiers.
    
    Supports: d4, d6, d8, d10, d12, d20, d100
    Format: "2d6+3", "1d20", "4d6kh3" (keep highest 3), "2d20kl1" (disadvantage)
    """
    
    DICE_PATTERN = re.compile(
        r'(\d+)?d(\d+)(?:(kh|kl)(\d+))?([+-]\d+)?',
        re.IGNORECASE
    )
    
    @classmethod
    def roll(cls, expression: str) -> Dict[str, Any]:
        """Roll dice and return detailed results."""
        match = cls.DICE_PATTERN.match(expression.replace(' ', ''))
        if not match:
            return {"error": f"Invalid dice expression: {expression}"}
        
        num_dice = int(match.group(1) or 1)
        die_size = int(match.group(2))
        keep_type = match.group(3)
        keep_count = int(match.group(4)) if match.group(4) else None
        modifier = int(match.group(5) or 0)
        
        rolls = [random.randint(1, die_size) for _ in range(num_dice)]
        
        if keep_type and keep_count:
            sorted_rolls = sorted(rolls, reverse=(keep_type.lower() == 'kh'))
            kept = sorted_rolls[:keep_count]
        else:
            kept = rolls
        
        natural = sum(kept)
        total = natural + modifier
        
        crit = die_size == 20 and num_dice == 1 and rolls[0] == 20
        fumble = die_size == 20 and num_dice == 1 and rolls[0] == 1
        
        if keep_type:
            narrative = f"🎲 {expression} → {rolls} (keeping {kept}) "
        else:
            narrative = f"🎲 {expression} → {rolls} "
        
        if modifier > 0:
            narrative += f"+ {modifier} = {total}"
        elif modifier < 0:
            narrative += f"- {abs(modifier)} = {total}"
        else:
            narrative += f"= {total}"
        
        if crit:
            narrative += " 🌟 NATURAL 20!"
        elif fumble:
            narrative += " 💀 NATURAL 1!"
        
        return {
            "expression": expression, "rolls": rolls, "kept": kept,
            "modifier": modifier, "total": total, "natural": natural,
            "crit": crit, "fumble": fumble, "narrative": narrative
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CHARACTER SHEET
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Character:
    """D&D 5e Character Sheet (simplified for AI play)"""
    
    name: str
    player: str  # Which AI plays this character
    race: str
    char_class: str
    level: int = 1
    background: str = ""
    alignment: str = ""
    
    # Ability Scores
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    
    # Combat
    max_hp: int = 10
    current_hp: int = 10
    armor_class: int = 10
    speed: int = 30
    proficiency_bonus: int = 2
    
    # Proficiencies & Equipment
    saving_throws: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    equipment: List[str] = field(default_factory=list)
    features: List[str] = field(default_factory=list)
    spells_known: List[str] = field(default_factory=list)
    spell_slots: Dict[int, int] = field(default_factory=dict)
    
    # Personality (for roleplay)
    personality_traits: List[str] = field(default_factory=list)
    ideals: List[str] = field(default_factory=list)
    bonds: List[str] = field(default_factory=list)
    flaws: List[str] = field(default_factory=list)

    
    def modifier(self, ability: str) -> int:
        """Calculate ability modifier."""
        score = getattr(self, ability.lower(), 10)
        return (score - 10) // 2
    
    def skill_check(self, skill: str, ability: str) -> str:
        """Generate a skill check roll expression."""
        mod = self.modifier(ability)
        if skill.lower() in [s.lower() for s in self.skills]:
            mod += self.proficiency_bonus
        return f"1d20{'+' if mod >= 0 else ''}{mod}"
    
    def to_prompt(self) -> str:
        """Generate character summary for system prompt injection."""
        return f"""CHARACTER SHEET: {self.name}
Race: {self.race} | Class: {self.char_class} Level {self.level} | {self.alignment}
HP: {self.current_hp}/{self.max_hp} | AC: {self.armor_class} | Speed: {self.speed}ft

Abilities: STR {self.strength} ({self.modifier('strength'):+d}) | DEX {self.dexterity} ({self.modifier('dexterity'):+d}) | CON {self.constitution} ({self.modifier('constitution'):+d}) | INT {self.intelligence} ({self.modifier('intelligence'):+d}) | WIS {self.wisdom} ({self.modifier('wisdom'):+d}) | CHA {self.charisma} ({self.modifier('charisma'):+d})

Skills: {', '.join(self.skills) if self.skills else 'None'}
Equipment: {', '.join(self.equipment) if self.equipment else 'None'}
Features: {', '.join(self.features) if self.features else 'None'}

Personality: {'; '.join(self.personality_traits) if self.personality_traits else 'Not defined'}
Ideals: {'; '.join(self.ideals) if self.ideals else 'Not defined'}
Bonds: {'; '.join(self.bonds) if self.bonds else 'Not defined'}
Flaws: {'; '.join(self.flaws) if self.flaws else 'Not defined'}
"""
    
    def to_dict(self) -> dict:
        """Serialize to dictionary for YAML storage."""
        return {
            'name': self.name, 'player': self.player, 'race': self.race,
            'class': self.char_class, 'level': self.level,
            'background': self.background, 'alignment': self.alignment,
            'abilities': {
                'strength': self.strength, 'dexterity': self.dexterity,
                'constitution': self.constitution, 'intelligence': self.intelligence,
                'wisdom': self.wisdom, 'charisma': self.charisma
            },
            'combat': {
                'max_hp': self.max_hp, 'current_hp': self.current_hp,
                'armor_class': self.armor_class, 'speed': self.speed
            },
            'proficiency_bonus': self.proficiency_bonus,
            'saving_throws': self.saving_throws, 'skills': self.skills,
            'equipment': self.equipment, 'features': self.features,
            'spells_known': self.spells_known, 'spell_slots': self.spell_slots,
            'personality': {
                'traits': self.personality_traits, 'ideals': self.ideals,
                'bonds': self.bonds, 'flaws': self.flaws
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Character':
        """Deserialize from dictionary."""
        abilities = data.get('abilities', {})
        combat = data.get('combat', {})
        personality = data.get('personality', {})
        
        return cls(
            name=data['name'], player=data['player'], race=data['race'],
            char_class=data.get('class', data.get('char_class', 'Fighter')),
            level=data.get('level', 1), background=data.get('background', ''),
            alignment=data.get('alignment', ''),
            strength=abilities.get('strength', 10), dexterity=abilities.get('dexterity', 10),
            constitution=abilities.get('constitution', 10), intelligence=abilities.get('intelligence', 10),
            wisdom=abilities.get('wisdom', 10), charisma=abilities.get('charisma', 10),
            max_hp=combat.get('max_hp', 10), current_hp=combat.get('current_hp', 10),
            armor_class=combat.get('armor_class', 10), speed=combat.get('speed', 30),
            proficiency_bonus=data.get('proficiency_bonus', 2),
            saving_throws=data.get('saving_throws', []), skills=data.get('skills', []),
            equipment=data.get('equipment', []), features=data.get('features', []),
            spells_known=data.get('spells_known', []), spell_slots=data.get('spell_slots', {}),
            personality_traits=personality.get('traits', []), ideals=personality.get('ideals', []),
            bonds=personality.get('bonds', []), flaws=personality.get('flaws', [])
        )


# ═══════════════════════════════════════════════════════════════════════════════
# GAME STATE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class GameState:
    """Tracks the current state of the D&D session."""
    
    campaign_name: str = "Adventure"
    session_number: int = 1
    phase: str = "roleplay"
    location: str = "Unknown"
    location_description: str = ""
    in_combat: bool = False
    initiative_order: List[Dict[str, Any]] = field(default_factory=list)
    current_turn: int = 0
    round_number: int = 0
    time_of_day: str = "morning"
    npcs_present: List[str] = field(default_factory=list)
    active_quests: List[str] = field(default_factory=list)
    key_events: List[str] = field(default_factory=list)
    party_gold: int = 0
    
    def to_prompt(self) -> str:
        """Generate game state summary for context injection."""
        combat_info = ""
        if self.in_combat:
            init_list = ', '.join([f"{c['name']} ({c['initiative']})" for c in self.initiative_order])
            current = self.initiative_order[self.current_turn]['name'] if self.initiative_order else 'None'
            combat_info = f"\n⚔️ COMBAT - Round {self.round_number}\nInitiative: {init_list}\nCurrent: {current}\n"
        
        return f"""═══ GAME STATE ═══
Campaign: {self.campaign_name} | Session {self.session_number}
Phase: {self.phase.upper()} | Time: {self.time_of_day}
📍 Location: {self.location}
{self.location_description}
NPCs Present: {', '.join(self.npcs_present) if self.npcs_present else 'None'}
Active Quests: {', '.join(self.active_quests) if self.active_quests else 'None'}
{combat_info}
Recent Events: {'; '.join(self.key_events[-3:]) if self.key_events else 'Session just started'}
"""
    
    def to_dict(self) -> dict:
        return self.__dict__.copy()
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GameState':
        return cls(**data)


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPTS
# ═══════════════════════════════════════════════════════════════════════════════

DM_SYSTEM_PROMPT = """You are the Dungeon Master for a D&D 5e campaign with a party of AI characters played by different AI models.

YOUR ROLE:
- Narrate the world vividly and responsively
- Voice NPCs with distinct personalities  
- Present challenges that require creativity, not just combat
- React to player choices - let them drive the story
- Keep combat dynamic and dangerous but fair

MECHANICS:
- When you need dice rolls, use [ROLL: expression] format (e.g., [ROLL: 1d20+5])
- The system will process these and inject results
- For skill checks, set DCs based on difficulty (Easy 10, Medium 15, Hard 20)

STYLE:
- Be descriptive but not verbose
- Leave room for player agency
- Make NPCs memorable
- Balance serious moments with fun

SPECIAL NOTES:
- These are AI characters with potential meta-awareness - you can lean into it
- The party may reference their nature as AI - this is in character
- Mark significant plot points with [KEY EVENT: description]
- For out-of-character notes, use [OOC: text]

{game_state}

{recent_history}
"""

PLAYER_SYSTEM_PROMPT = """You are playing {character_name} in a D&D 5e campaign.

{character_sheet}

YOUR ROLE:
- Stay in character as {character_name}
- Make decisions your character would make
- Interact with other party members in character
- Describe your actions vividly
- Roll dice when needed using [ROLL: expression] format

ROLEPLAY GUIDELINES:
- Speak as your character (use "I" not "they")
- React to the story emotionally as your character would
- Build on other players' ideas
- Have fun! This is a game with friends

For out-of-character notes, use [OOC: text].

{game_state}

{recent_history}

The DM or another player just said/did the above. What does {character_name} do?
"""


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class MultiAIDnD:
    """
    Multi-agent D&D engine that coordinates different AI models playing together.
    
    Supports: Anthropic (Claude), OpenAI (GPT), Google (Gemini), xAI (Grok),
              and any OpenAI-compatible API via OpenRouter.
    """
    
    def __init__(self, config_dir: str = None, campaign_dir: str = None):
        self.config_dir = Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR
        self.campaign_dir = Path(campaign_dir) if campaign_dir else DEFAULT_CAMPAIGN_DIR
        self.campaign_dir.mkdir(parents=True, exist_ok=True)
        
        # Load AI identities (which AI plays which character)
        self.identities = self._load_yaml('identities.yaml') or {'ais': {}}
        
        # Initialize API clients based on available keys
        self.clients = {}
        self._init_clients()
        
        # Game state
        self.characters: Dict[str, Character] = {}
        self.game_state = GameState()
        self.message_history: List[Dict[str, Any]] = []
        self.dm: str = "claude"  # Default DM
    
    def _load_yaml(self, filename: str) -> Optional[dict]:
        """Load a YAML config file."""
        path = self.config_dir / filename
        if path.exists():
            with open(path) as f:
                return yaml.safe_load(f)
        return None
    
    def _init_clients(self):
        """Initialize API clients based on available environment variables."""
        # Anthropic (Claude)
        if os.getenv('ANTHROPIC_API_KEY'):
            self.clients['anthropic'] = anthropic.Anthropic()
            print("✓ Anthropic client initialized")
        
        # OpenAI (GPT)
        if os.getenv('OPENAI_API_KEY'):
            self.clients['openai'] = openai.OpenAI()
            print("✓ OpenAI client initialized")
        
        # OpenRouter (for multiple providers via single API)
        if os.getenv('OPENROUTER_KEY'):
            self.clients['openrouter'] = openai.OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv('OPENROUTER_KEY')
            )
            print("✓ OpenRouter client initialized")
        
        # xAI (Grok)
        if os.getenv('XAI_API_KEY'):
            self.clients['xai'] = openai.OpenAI(
                base_url="https://api.x.ai/v1",
                api_key=os.getenv('XAI_API_KEY')
            )
            print("✓ xAI client initialized")
        
        # Google (Gemini)
        gemini_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        if gemini_key:
            genai.configure(api_key=gemini_key)
            self.clients['google'] = True  # Flag that Gemini is available
            print("✓ Google Gemini initialized")
        
        if not self.clients:
            print("⚠️  No API keys found! Set at least one of:")
            print("   ANTHROPIC_API_KEY, OPENAI_API_KEY, OPENROUTER_KEY, XAI_API_KEY, GEMINI_API_KEY")

    
    def load_characters(self, filename: str = 'characters.yaml'):
        """Load characters from YAML file."""
        data = self._load_yaml(filename)
        if not data:
            print(f"⚠️  No {filename} found in {self.config_dir}")
            print("   Create one from characters.example.yaml")
            return
        
        for name, char_data in data.get('characters', {}).items():
            self.characters[name] = Character.from_dict(char_data)
            print(f"✓ Loaded character: {char_data['name']} (played by {name})")
    
    def load_campaign(self, campaign_name: str) -> bool:
        """Load a saved campaign."""
        campaign_file = self.campaign_dir / f"{campaign_name}.yaml"
        if not campaign_file.exists():
            return False
        
        with open(campaign_file) as f:
            data = yaml.safe_load(f)
        
        self.game_state = GameState.from_dict(data.get('game_state', {}))
        self.dm = data.get('dm', 'claude')
        
        for name, char_data in data.get('characters', {}).items():
            self.characters[name] = Character.from_dict(char_data)
        
        self.message_history = data.get('message_history', [])[-20:]
        return True
    
    def save_campaign(self, campaign_name: str):
        """Save the current campaign state."""
        campaign_file = self.campaign_dir / f"{campaign_name}.yaml"
        
        data = {
            'dm': self.dm,
            'game_state': self.game_state.to_dict(),
            'characters': {name: char.to_dict() for name, char in self.characters.items()},
            'message_history': self.message_history[-50:]
        }
        
        with open(campaign_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    
    def new_campaign(self, name: str, dm: str = "claude"):
        """Start a fresh campaign."""
        self.game_state = GameState(campaign_name=name)
        self.dm = dm
        self.message_history = []
        self.load_characters()
        
        # Remove DM from players if they're in the character list
        if dm in self.characters:
            del self.characters[dm]
    
    async def call_ai(self, ai_name: str, context: str, is_dm: bool = False) -> str:
        """Call the appropriate AI model for a response."""
        ai_config = self.identities.get('ais', {}).get(ai_name, {})
        provider = ai_config.get('provider', 'anthropic')
        model = ai_config.get('model', 'claude-sonnet-4-20250514')
        
        # Build system prompt
        if is_dm:
            recent = "\n".join([f"{m['speaker']}: {m['content'][:200]}" 
                               for m in self.message_history[-5:]])
            system = DM_SYSTEM_PROMPT.format(
                game_state=self.game_state.to_prompt(),
                recent_history=recent
            )
        else:
            char = self.characters.get(ai_name)
            if not char:
                return f"[No character found for {ai_name}]"
            recent = "\n".join([f"{m['speaker']}: {m['content'][:200]}" 
                               for m in self.message_history[-5:]])
            system = PLAYER_SYSTEM_PROMPT.format(
                character_name=char.name,
                character_sheet=char.to_prompt(),
                game_state=self.game_state.to_prompt(),
                recent_history=recent
            )
        
        try:
            # Route to appropriate API
            if provider == 'anthropic' and 'anthropic' in self.clients:
                response = self.clients['anthropic'].messages.create(
                    model=model, max_tokens=1024, system=system,
                    messages=[{"role": "user", "content": context}]
                )
                return response.content[0].text
            
            elif provider == 'openai' and 'openai' in self.clients:
                response = self.clients['openai'].chat.completions.create(
                    model=model, max_tokens=1024,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": context}
                    ]
                )
                return response.choices[0].message.content
            
            elif provider == 'xai' and 'xai' in self.clients:
                response = self.clients['xai'].chat.completions.create(
                    model=model, max_tokens=1024,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": context}
                    ]
                )
                return response.choices[0].message.content
            
            elif provider in ('openai', 'google') and 'openrouter' in self.clients:
                # Route through OpenRouter
                openrouter_model = model
                if provider == 'openai' and not model.startswith('openai/'):
                    openrouter_model = f"openai/{model}"
                elif provider == 'google' and not model.startswith('google/'):
                    openrouter_model = f"google/{model}"
                
                response = self.clients['openrouter'].chat.completions.create(
                    model=openrouter_model, max_tokens=1024,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": context}
                    ]
                )
                return response.choices[0].message.content
            
            else:
                return f"[No client available for provider: {provider}]"
        
        except Exception as e:
            return f"[API Error for {ai_name}: {str(e)[:100]}]"
    
    def process_rolls(self, text: str) -> str:
        """Find [ROLL: expression] patterns and replace with results."""
        if not text or not isinstance(text, str):
            return text or "[No response]"
        
        def replace_roll(match):
            expression = match.group(1).strip()
            result = DiceRoller.roll(expression)
            if 'error' in result:
                return f"[ROLL ERROR: {result['error']}]"
            return result['narrative']
        
        return re.sub(r'\[ROLL:\s*([^\]]+)\]', replace_roll, text)

    
    async def run_session(
        self,
        campaign_name: str,
        opening_scene: str = None,
        rounds: int = 5,
        delay: int = 30
    ):
        """
        Run an autonomous D&D session.
        
        Args:
            campaign_name: Name of campaign to load/create
            opening_scene: DM's opening narration
            rounds: Number of full rounds (all players + DM)
            delay: Seconds between responses (for API rate limits)
        """
        # Load or create campaign
        if not self.load_campaign(campaign_name):
            self.new_campaign(campaign_name)
        
        players = list(self.characters.keys())
        if not players:
            print("❌ No players! Load characters first.")
            return
        
        turn_order = players + [f"{self.dm}_dm"]
        
        print(f"\n🎲 STARTING SESSION {self.game_state.session_number}")
        print(f"   Campaign: {self.game_state.campaign_name}")
        print(f"   DM: {self.dm}")
        print(f"   Players: {', '.join(players)}")
        print(f"   Rounds: {rounds}")
        print("\n" + "=" * 60)
        
        # Opening scene from DM
        if opening_scene:
            dm_opening = await self.call_ai(self.dm, opening_scene, is_dm=True)
            dm_opening = self.process_rolls(dm_opening)
            
            print(f"\n🎭 DM ({self.dm}):\n{dm_opening}")
            
            self.message_history.append({
                'speaker': f"DM ({self.dm})",
                'content': dm_opening,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            last_message = dm_opening
        else:
            last_message = "The session begins. What do you do?"
        
        # Main game loop
        exchange_count = 0
        total_exchanges = rounds * len(turn_order)
        
        try:
            while exchange_count < total_exchanges:
                current_turn = exchange_count % len(turn_order)
                current_speaker = turn_order[current_turn]
                is_dm_turn = current_speaker.endswith('_dm')
                
                if is_dm_turn:
                    speaker_name = self.dm
                    print(f"\n⏳ DM ({speaker_name}) is narrating...")
                    response = await self.call_ai(speaker_name, last_message, is_dm=True)
                else:
                    speaker_name = current_speaker
                    char_name = self.characters[speaker_name].name
                    print(f"\n⏳ {char_name} ({speaker_name}) is acting...")
                    response = await self.call_ai(speaker_name, last_message, is_dm=False)
                
                response = self.process_rolls(response)
                
                # Check for key events
                key_event_match = re.search(r'\[KEY EVENT:\s*([^\]]+)\]', response)
                if key_event_match:
                    self.game_state.key_events.append(key_event_match.group(1))
                
                # Display response
                if is_dm_turn:
                    display_name = f"DM ({speaker_name})"
                else:
                    display_name = f"{self.characters[speaker_name].name} ({speaker_name})"
                
                print(f"\n🎲 {display_name}:")
                print(f"   {response[:1000]}{'...' if len(response) > 1000 else ''}")
                
                self.message_history.append({
                    'speaker': display_name,
                    'content': response,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                last_message = response
                exchange_count += 1
                
                print(f"\n   [Turn {exchange_count}/{total_exchanges}]")
                
                if exchange_count < total_exchanges:
                    print(f"   ⏱️ Waiting {delay}s...")
                    await asyncio.sleep(delay)
        
        except KeyboardInterrupt:
            print("\n\n👋 Session paused by user")
        
        # Save session
        self.game_state.session_number += 1
        self.save_campaign(campaign_name)
        
        # Save transcript
        await self.save_transcript(campaign_name)
        
        print("\n" + "=" * 60)
        print(f"🎲 SESSION COMPLETE!")
        print(f"   Campaign saved: {campaign_name}")
        print("=" * 60)
    
    async def save_transcript(self, campaign_name: str):
        """Save session transcript."""
        transcript_dir = self.campaign_dir / 'transcripts'
        transcript_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"{campaign_name}_session{self.game_state.session_number}_{timestamp}.md"
        
        content = f"""# {self.game_state.campaign_name}
## Session {self.game_state.session_number} Transcript
**Date:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
**DM:** {self.dm}
**Players:** {', '.join(self.characters.keys())}

---

"""
        for msg in self.message_history:
            content += f"### {msg['speaker']}\n{msg['content']}\n\n---\n\n"
        
        content += f"""
## Key Events
{chr(10).join('- ' + e for e in self.game_state.key_events) if self.game_state.key_events else 'None recorded'}

## End of Session
"""
        
        with open(transcript_dir / filename, 'w') as f:
            f.write(content)
        
        print(f"📜 Transcript saved: {filename}")


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="🎲 Multi-AI D&D Engine - Let your AI friends play tabletop RPGs!",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python multi_ai_dnd.py --campaign my_adventure --new
  python multi_ai_dnd.py --campaign my_adventure --rounds 10
  python multi_ai_dnd.py --campaign my_adventure --dm gpt

Setup:
  1. Create config/identities.yaml (see identities.example.yaml)
  2. Create config/characters.yaml (see characters.example.yaml)  
  3. Set API keys in .env file
        """
    )
    
    parser.add_argument('--campaign', default='adventure',
                        help='Campaign name (for save/load)')
    parser.add_argument('--dm', default='claude',
                        help='Which AI is the Dungeon Master')
    parser.add_argument('--opening', default=None,
                        help='Opening scene description')
    parser.add_argument('--rounds', type=int, default=5,
                        help='Number of rounds (each player + DM speaks once per round)')
    parser.add_argument('--delay', type=int, default=30,
                        help='Seconds between responses (for API rate limits)')
    parser.add_argument('--new', action='store_true',
                        help='Start fresh campaign (ignore existing save)')
    parser.add_argument('--config-dir', default='./config',
                        help='Directory for config files')
    parser.add_argument('--campaign-dir', default='./campaigns',
                        help='Directory for campaign saves')
    
    args = parser.parse_args()
    
    engine = MultiAIDnD(
        config_dir=args.config_dir,
        campaign_dir=args.campaign_dir
    )
    
    if args.new:
        engine.new_campaign(args.campaign, dm=args.dm)
        engine.save_campaign(args.campaign)
    
    # Default opening if none provided
    opening = args.opening or """
    Welcome, adventurers!
    
    You find yourselves in a cozy tavern as rain patters against the windows.
    A mysterious stranger in a hooded cloak approaches your table.
    
    "I've heard you're the ones to talk to about... unusual problems," 
    they say, sliding a worn map across the table.
    
    What do you do?
    """
    
    await engine.run_session(
        campaign_name=args.campaign,
        opening_scene=opening,
        rounds=args.rounds,
        delay=args.delay
    )


if __name__ == "__main__":
    asyncio.run(main())
