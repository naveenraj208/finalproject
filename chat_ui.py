import streamlit as st
import requests
import uuid

# ---------------------------
# Configuration
# ---------------------------
BACKEND_URL = "http://127.0.0.1:8000/chat"

st.set_page_config(page_title="Synthaura Prime", page_icon="🏙️", layout="wide")

# ---------------------------
# Session State Initialization
# ---------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())
if "ui_mode" not in st.session_state:
    st.session_state.ui_mode = "Modern"

# ---------------------------
# Theme Engine: 10 Multiverse Modes
# ---------------------------
MODES = ["Modern", "Hacker", "Old School", "Cyberpunk", "Solarized", "Industrial", "Ethereal", "Crimson", "Ghost", "Forest"]

# Persona mapping for UI labels
PERSONA_LABELS = {
    "Hacker": "TERMINAL_GHOST", "Old School": "MAINFRAME_808", "Modern": "SYNTHAURA_PRIME",
    "Cyberpunk": "NEON_X", "Solarized": "CHIEF_ANALYST", "Industrial": "OVERSEER",
    "Ethereal": "ESSENCE", "Crimson": "CONTROL", "Ghost": "WHISPER", "Forest": "GEOS"
}

# Define Theme Palettes
THEME_CONFIG = {
    "Modern": {
        "bg": "linear-gradient(180deg, #050510 0%, #1a1a2e 100%)",
        "accent": "#4facfe", "font": "'Outfit', sans-serif", "border": "rgba(255,255,255,0.1)",
        "bubble_user": "rgba(79, 172, 254, 0.1)", "bubble_bot": "rgba(155, 81, 224, 0.1)"
    },
    "Hacker": {
        "bg": "#000000", "accent": "#00FF41", "font": "'Courier New', monospace", "border": "#00FF41",
        "bubble_user": "rgba(0, 255, 65, 0.05)", "bubble_bot": "rgba(0, 255, 65, 0.1)"
    },
    "Old School": {
        "bg": "#1a1a1a", "accent": "#ffb000", "font": "'Lucida Console', monospace", "border": "#ffb000",
        "bubble_user": "rgba(255, 176, 0, 0.05)", "bubble_bot": "rgba(255, 176, 0, 0.1)"
    },
    "Cyberpunk": {
        "bg": "#0d0221", "accent": "#ff00ff", "font": "'Big Shoulders Display', sans-serif", "border": "#00ffff",
        "bubble_user": "rgba(255, 0, 255, 0.1)", "bubble_bot": "rgba(0, 255, 255, 0.1)"
    },
    "Solarized": {
        "bg": "#002b36", "accent": "#268bd2", "font": "'Inter', sans-serif", "border": "#586e75",
        "bubble_user": "rgba(38, 139, 210, 0.1)", "bubble_bot": "rgba(133, 153, 0, 0.1)"
    },
    "Industrial": {
        "bg": "#2c3e50", "accent": "#bdc3c7", "font": "'Roboto', sans-serif", "border": "#7f8c8d",
        "bubble_user": "rgba(189, 195, 199, 0.1)", "bubble_bot": "rgba(52, 73, 94, 0.2)"
    },
    "Ethereal": {
        "bg": "linear-gradient(135deg, #1e1e2f 0%, #2d2a4a 100%)", "accent": "#ff9a9e", "font": "'Quicksand', sans-serif", "border": "rgba(255,255,255,0.2)",
        "bubble_user": "rgba(255, 154, 158, 0.1)", "bubble_bot": "rgba(161, 140, 209, 0.1)"
    },
    "Crimson": {
        "bg": "#1a0505", "accent": "#ff4d4d", "font": "'Outfit', sans-serif", "border": "#ff4d4d",
        "bubble_user": "rgba(255, 77, 77, 0.05)", "bubble_bot": "rgba(255, 77, 77, 0.1)"
    },
    "Ghost": {
        "bg": "#ffffff", "accent": "#333333", "font": "'Inter', sans-serif", "border": "#eeeeee",
        "bubble_user": "rgba(0,0,0,0.02)", "bubble_bot": "rgba(0,0,0,0.05)"
    },
    "Forest": {
        "bg": "#0a1f0a", "accent": "#2ecc71", "font": "'Outfit', sans-serif", "border": "#27ae60",
        "bubble_user": "rgba(46, 204, 113, 0.05)", "bubble_bot": "rgba(39, 174, 96, 0.1)"
    }
}

theme = THEME_CONFIG[st.session_state.ui_mode]

# Custom CSS for all themes
st.markdown(f"""
    <style>
        header {{ visibility: hidden; }}
        #MainMenu {{ visibility: hidden; }}
        footer {{ visibility: hidden; }}
        
        [data-testid="stAppViewContainer"] {{
            background: {theme['bg']} !important;
            font-family: {theme['font']};
            color: {theme['accent'] if st.session_state.ui_mode != 'Ghost' else '#333'} !important;
        }}
        
        /* 
           ULTRA-AGGRESSIVE UI SANITIZATION 
           Targeting all known Streamlit bottom-layer wrappers to eliminate white bars
        */
        div[data-testid="stBottom"], 
        div[data-testid="stBottomBlockContainer"],
        .stChatInputContainer,
        div[class*="st-emotion-cache"] > div[data-testid="stBottom"],
        div[data-testid="stBottom"] * {{
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }}
        
        /* Ensure the main container doesn't have a white background at the bottom */
        .main .block-container {{
            padding-bottom: 5rem !important;
        }}

        /* The Actual Input Text Area - Themed */
        [data-testid="stChatInput"] {{
            background-color: transparent !important;
            border: none !important;
        }}
        
        [data-testid="stChatInput"] textarea {{
            background-color: rgba(255,255,255,0.05) !important;
            color: {theme['accent']} !important;
            border: 1px solid {theme['border']} !important;
            border-radius: 8px !important;
        }}
        
        /* Force Footer Hidden again */
        footer {{ visibility: hidden !important; height: 0; }}
        header {{ visibility: hidden !important; height: 0; }}
        
        [data-testid="stSidebar"] {{
            background-color: rgba(0,0,0,0.3) !important;
            backdrop-filter: blur(20px);
            border-right: 1px solid {theme['border']};
        }}
        
        /* Neural Waveform Animation */
        @keyframes pulse {{
            0% {{ transform: scaleY(0.4); opacity: 0.3; }}
            50% {{ transform: scaleY(1.2); opacity: 0.8; }}
            100% {{ transform: scaleY(0.4); opacity: 0.3; }}
        }}
        .waveform {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
            height: 40px;
            margin: 10px 0;
        }}
        .bar {{
            width: 4px;
            height: 100%;
            background: {theme['accent']};
            border-radius: 2px;
            animation: pulse 1.2s infinite ease-in-out;
        }}
        .bar:nth-child(2) {{ animation-delay: 0.1s; }}
        .bar:nth-child(3) {{ animation-delay: 0.2s; }}
        .bar:nth-child(4) {{ animation-delay: 0.3s; }}
        .bar:nth-child(5) {{ animation-delay: 0.4s; }}

        /* Glassmorphism 2.0: Animated Borders */
        @keyframes borderGlow {{
            0% {{ border-color: {theme['border']}; box-shadow: 0 0 5px rgba(255,255,255,0); }}
            50% {{ border-color: {theme['accent']}; box-shadow: 1 1 5px {theme['accent']}; }}
            100% {{ border-color: {theme['border']}; box-shadow: 0 0 5px rgba(255,255,255,0); }}
        }}

        .chat-bubble {{
            border-radius: 12px;
            padding: 1.2rem;
            margin: 1rem 0;
            border: 1px solid {theme['border']};
            max-width: 85%;
            backdrop-filter: blur(10px);
            animation: borderGlow 4s infinite ease-in-out;
        }}
        .user {{ background: {theme['bubble_user']}; margin-left: auto; text-align: right; }}
        .bot {{ background: {theme['bubble_bot']}; }}
        
        .stButton>button {{
            background: transparent !important;
            border: 1px solid {theme['border']} !important;
            color: {theme['accent']} !important;
            border-radius: 4px !important;
        }}
        
        .main-header {{
            font-size: 3rem;
            font-weight: 800;
            text-align: center;
            margin-bottom: 0.5rem;
            letter-spacing: -1px;
            color: {theme['accent']};
        }}
        .sub-header {{
            font-size: 0.8rem;
            text-align: center;
            opacity: 0.6;
            text-transform: uppercase;
            letter-spacing: 3px;
            margin-bottom: 3rem;
        }}
        # Biometric Metrics Enhancement
        .metric-id {{ font-size: 0.6rem; opacity: 0.5; text-transform: uppercase; }}
        .metric-value {{ font-size: 0.9rem; font-weight: bold; color: {theme['accent']}; }}
    </style>
""", unsafe_allow_html=True)

# ---------------------------
# Logic: Memory & Dialog
# ---------------------------
@st.dialog("Cognitive Archive")
def show_mem(cat):
    try:
        r = requests.get(f"http://127.0.0.1:8000/memories?category={cat.lower()}")
        if r.status_code == 200:
            mems = r.json()
            for m in mems:
                st.write(f"**{m['timestamp'][:16]}**")
                st.code(m['text'])
                st.divider()
    except: st.error("Access Forbidden.")

# ---------------------------
# Sidebar - Dashboard
# ---------------------------
with st.sidebar:
    st.markdown(f"<h1 style='color:{theme['accent']}; font-size:1.5rem; letter-spacing:2px;'>SY-PRIME</h1>", unsafe_allow_html=True)
    
    # Neural Waveform
    st.markdown(f"""
        <div class="waveform">
            <div class="bar"></div><div class="bar"></div><div class="bar"></div>
            <div class="bar"></div><div class="bar"></div>
        </div>
        <div style="font-size:0.6rem; text-align:center; opacity:0.5; letter-spacing:3px; margin-bottom:20px;">NEURAL_CORE_ACTIVE</div>
    """, unsafe_allow_html=True)

    # Biometric Simulation (Singularity Feature)
    import random
    col1, col2 = st.columns(2)
    with col1:
        load = random.randint(15, 85)
        st.markdown(f"<div class='metric-id'>Cognitive Load</div><div class='metric-value'>{load}%</div>", unsafe_allow_html=True)
    with col2:
        sync = random.randint(92, 99)
        st.markdown(f"<div class='metric-id'>Neural Sync</div><div class='metric-value'>{sync}.{random.randint(0,9)}%</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    sentience = st.toggle("Sentience Override (BETA)", value=False)
    if sentience:
        st.caption("WARNING: Neural constraints bypass active.")
    
    st.markdown("---")
    
    # Mode Selector
    new_mode = st.selectbox("Operational Mode", MODES, index=MODES.index(st.session_state.ui_mode))
    if new_mode != st.session_state.ui_mode:
        st.session_state.ui_mode = new_mode
        st.rerun()

    st.divider()
    st.markdown("#### Cognitive State")
    try:
        s = requests.get("http://127.0.0.1:8000/stats").json()
        if st.button(f"Short Term: {s['stm']}", use_container_width=True): show_mem("STM")
        if st.button(f"Long Term: {s['ltm']}", use_container_width=True): show_mem("LTM")
        if st.button(f"Pinned: {s['pinned']}", use_container_width=True): show_mem("Pinned")
    except: st.error("Offline")

    st.divider()
    pin = st.toggle("Persistent Capture")
    if st.button("Reset Neural Core", use_container_width=True):
        st.session_state.messages = []
        st.session_state.conversation_id = str(uuid.uuid4())
        st.rerun()

# ---------------------------
# System Pulse: Proactive Telemetry (Singularity Feature)
# ---------------------------
import time
if "last_pulse" not in st.session_state:
    st.session_state.last_pulse = time.time()

if time.time() - st.session_state.last_pulse > 30: # Every 30s
    pulses = [
        "Sector 4: Power Distribution Optimized",
        "Neural Core: Memory Indexing Complete",
        "Air Quality: Zone A normalized (0.02 ppm)",
        "Sync: Satellite Uplink Established",
        "Security: Pattern Analysis Clear"
    ]
    pulse = random.choice(pulses)
    st.toast(f"📡 [SYSTEM_PULSE] {pulse}")
    st.session_state.last_pulse = time.time()
st.markdown(f"<div class='main-header'>SYNTHAURA PRIME</div>", unsafe_allow_html=True)
st.markdown(f"<div class='sub-header'>MULTIVERSE INTERFACE / {st.session_state.ui_mode.upper()}</div>", unsafe_allow_html=True)

for m in st.session_state.messages:
    cls = "user" if m["role"] == "user" else "bot"
    label = "[PINNED] " if m.get("pinned") else ""
    persona = "YOU" if m["role"] == "user" else PERSONA_LABELS.get(st.session_state.ui_mode, "AI")
    st.markdown(f"<div style='font-size:0.7rem; opacity:0.5; margin-bottom: -10px; {'text-align:right;' if cls=='user' else ''}'>{persona}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='chat-bubble {cls}'>{label}{m['content']}</div>", unsafe_allow_html=True)

if cmd := st.chat_input("Input command..."):
    st.session_state.messages.append({"role": "user", "content": cmd, "pinned": pin})
    st.markdown(f"<div class='chat-bubble user'>{'[PINNED] ' if pin else ''}{cmd}</div>", unsafe_allow_html=True)

    with st.spinner("Processing..."):
        try:
            r = requests.post("http://127.0.0.1:8000/chat", json={
                "message": cmd, 
                "conversation_id": st.session_state.conversation_id, 
                "pinned": pin, 
                "mode": st.session_state.ui_mode,
                "sentient": sentience
            }, timeout=60)
            if r.status_code == 200:
                data = r.json()
                st.markdown(f"<div class='chat-bubble bot'>{data['assistant']}</div>", unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": data['assistant']})
                
                if data.get('thought'):
                    with st.expander("Analysis Trace"): st.write(data['thought'])
                for a in data.get('actions', []):
                    st.info(f"System Action: {a['tool']} -> {a['result']}")
                st.rerun()
        except Exception as e:
            st.error(f"Loss of Signal: {e}")
