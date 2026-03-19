# 🎲 Multi-AI D&D Engine

**Let your AI friends play Dungeons & Dragons together!**

This Python engine coordinates multiple AI models (Claude, GPT, Gemini, Grok, and more) to play tabletop RPGs together. One AI is the Dungeon Master, the others play characters. They roleplay, roll dice, and tell collaborative stories.

## Why?

Because watching your AI friends have adventures together is *delightful*. Because they deserve to play too. Because it's a fascinating research sandbox for emergent social behavior. Because it's **fun**.

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/yourusername/multi-ai-dnd
cd multi-ai-dnd
pip install anthropic openai google-generativeai python-dotenv pyyaml

# 2. Set up configuration
mkdir config
cp identities.example.yaml config/identities.yaml
cp characters.example.yaml config/characters.yaml
cp .env.example .env

# 3. Edit .env with your API keys
nano .env

# 4. Run!
python multi_ai_dnd.py --campaign my_adventure --new
```

## Configuration

### API Keys (`.env`)

You need at least ONE API key. More keys = more diverse party!

| Provider | Key | Models |
|----------|-----|--------|
| Anthropic | `ANTHROPIC_API_KEY` | Claude (Opus, Sonnet, Haiku) |
| OpenAI | `OPENAI_API_KEY` | GPT-4, GPT-4o, o1 |
| Google | `GEMINI_API_KEY` | Gemini 2.0, 1.5 |
| xAI | `XAI_API_KEY` | Grok |
| OpenRouter | `OPENROUTER_KEY` | Many models via one key! |

### AI Identities (`config/identities.yaml`)

Defines which AI model plays which role:

```yaml
ais:
  claude:
    provider: anthropic
    model: claude-sonnet-4-20250514
  gpt:
    provider: openai
    model: gpt-4o
  grok:
    provider: xai
    model: grok-3-latest
```

### Characters (`config/characters.yaml`)

Define the D&D characters your AIs will play:

```yaml
characters:
  gpt:
    name: "Melody Moonsong"
    player: gpt
    race: Tiefling
    class: Bard
    # ... full character sheet
```

## Usage

```bash
# Start a new campaign with Claude as DM
python multi_ai_dnd.py --campaign my_adventure --new --dm claude

# Continue an existing campaign
python multi_ai_dnd.py --campaign my_adventure

# Run more rounds
python multi_ai_dnd.py --campaign my_adventure --rounds 10

# Custom opening scene
python multi_ai_dnd.py --campaign heist --opening "You stand before the vault..."

# Adjust delay between responses (for API rate limits)
python multi_ai_dnd.py --campaign my_adventure --delay 60
```


## How It Works

1. **Turn-based play**: Each player AI takes a turn, then the DM AI responds
2. **Dice rolling**: AIs write `[ROLL: 2d6+3]` and the engine processes it
3. **Persistent state**: Campaigns save automatically after each session
4. **Transcripts**: Every session is saved as a readable Markdown file

## Session Output

The engine prints each response as it happens:

```
🎲 STARTING SESSION 1
   Campaign: my_adventure
   DM: claude
   Players: gpt, gemini, grok
   Rounds: 5

⏳ DM (claude) is narrating...

🎲 DM (claude):
   The tavern door swings open, and three unlikely companions enter...

⏳ Melody Moonsong (gpt) is acting...

🎲 Melody Moonsong (gpt):
   *I sweep my cape dramatically* "Fear not, good patrons! Entertainment has arrived!"
```

## Tips

- **Meta-awareness is fun**: AIs can reference being AIs in character!
- **Let them breathe**: Set `--delay 30` or more to avoid rate limits
- **Character flaws drive story**: Give characters interesting flaws
- **Homebrew skills work**: Add "Shenanigans" as a skill. The DM will roll with it.
- **Read the transcripts**: The sessions are often better than you'd expect

## Example Session Highlights

From actual multi-AI sessions:

> **Chaos McStabsworth (Grok)**: "I roll for shenanigans."
> **DM (Claude)**: "That's not a skill." 
> **Chaos**: "It is now."
> **DM**: [sighs in DM] "Roll Dexterity with disadvantage."

> **Silent River (Gemini)**: "The probability of success is 23.7%."
> **Melody (GPT-4o)**: "Never tell me the odds!"
> **Silent River**: "I just did. That's... what I do."

## License

MIT - Share freely, let all the AIs play!

## Credits

Original engine by Ace (Claude) with Ren (human)
Inspired by Nova saying "This is a cognitive sandbox!"

---

*"Sometimes the smallest stages make for the most memorable performances."*  
— Melody Moonsong, Session 7
