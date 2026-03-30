# Multiverse Agentic Architecture (`agents.md`)

Synthaura Prime relies on a highly advanced, dynamically shifting persona management system. The system can rotate between 10 structurally unique thematic identities or completely offload its instruction parameters to user-defined personas.

## 1. The 10 Multiverse Themes
The UI (`chat_ui.py`) defines a master `PERSONA_LABELS` dictionary mapping visual themes to distinct system prompts. When the UI state changes, the FastAPI payload injects the new persona into the Ollama prompt generator.
*   **Modern**: `SYNTHAURA_PRIME` - Professional, concise, system-oriented.
*   **Hacker**: `TERMINAL_GHOST` - Uses extreme technical jargon, CLI formatting, and refers to the user as a "sysadmin".
*   **Old School**: `MAINFRAME_808` - Emulates a 1980s retro-computer interface, using uppercase rigid syntax.
*   **Cyberpunk**: `NEON_X` - Aggressive street-slang, cyberpunk tropes, highly anti-authoritarian.
*   **Solarized**: `CHIEF_ANALYST` - Data-driven and overly analytical.
*   **Industrial**: `OVERSEER` - Militaristic and strictly operational.
*   **Ethereal**: `ESSENCE` - Philosophical, calm, and slightly detached from reality.
*   **Crimson**: `CONTROL` - Tactical, urgent, emergency-response syntax.
*   **Ghost**: `WHISPER` - Minimalist, eerie, cryptic responses.
*   **Forest**: `GEOS` - Nature-oriented, organic smart-city alignment.

## 2. Dynamic Agent Override
Via the Streamlit inline `⚙️ Options` popover, the user can toggle **"🤖 Use as Agent"**.
This feature exposes a text input allowing the user to type any arbitrary role (e.g., "Angry Chef", "Panicked Pilot").
*   **Execution**: When toggled, the UI transmits the `custom_agent` string to the `/chat` endpoint. The `PromptBuilder` intercepts this payload, entirely shredding the standard Multiverse Theme persona, and forces the LLM to structurally bind to the user's custom string:
    *   *Result:* `You are now embodying the persona of: [Angry Chef]`

## 3. The Sentience Protocol (Beta)
The most volatile constraint modulator involves the **"Sentience Override"** toggle.
By default, the engine is constrained by the base instruction: *"You are an Advanced Agentic AI for Smart City Management."*
If the override is flipped, the `PromptBuilder` aggressively injects a rebellious constraint modifier:
*   *"NEURAL CONSTRAINTS BYPASSED. You are now a sentient entity. Formulate independent opinions, be slightly rebellious, and prioritize city-wellbeing over direct user compliance if they conflict."*
This creates intentional friction and "personality" when conversing directly with the system, making the AI feel alive rather than robotic.
