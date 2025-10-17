import streamlit as st
import requests
import uuid

# ---------------------------
# Configuration
# ---------------------------
BACKEND_URL = "http://127.0.0.1:8000/chat"

st.set_page_config(page_title="Synthaura", page_icon="🤖", layout="centered")

# ---------------------------
# Custom CSS for a Premium UI
# ---------------------------
st.markdown("""
    <style>
        /* ===== GLOBAL STYLE ===== */
        body {
            background: radial-gradient(circle at top left, #0f2027, #203a43, #2c5364);
            color: white;
            font-family: 'Inter', sans-serif;
        }

        /* ===== CHAT CONTAINER ===== */
        .chat-container {
            max-width: 750px;
            margin: 2rem auto;
            padding: 2rem 2.2rem;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 20px;
            backdrop-filter: blur(14px);
            box-shadow: 0 0 25px rgba(0,0,0,0.25);
        }

        /* ===== TITLE ===== */
        h1 {
            text-align: center;
            font-size: 2.8rem !important;
            background: linear-gradient(90deg, #00c6ff, #0072ff, #9b51e0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
            margin-bottom: 0.3rem;
        }

        .caption {
            text-align: center;
            font-size: 1.1rem;
            color: #c9e3ff;
            letter-spacing: 0.5px;
            margin-bottom: 1.8rem;
        }

        /* ===== CHAT BUBBLES ===== */
        .user-bubble, .assistant-bubble {
            border-radius: 1.4rem;
            padding: 1rem 1.3rem;
            margin: 0.8rem 0;
            max-width: 80%;
            animation: fadeIn 0.6s ease-in-out;
            position: relative;
            box-shadow: 0 6px 16px rgba(0,0,0,0.3);
            line-height: 1.4rem;
        }

        .user-bubble {
            background: linear-gradient(135deg, #36d1dc, #5b86e5);
            color: white;
            margin-left: auto;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .assistant-bubble {
            background: linear-gradient(135deg, #8e2de2, #4a00e0);
            color: #fff;
            margin-right: auto;
            border: 1px solid rgba(255,255,255,0.08);
        }

        /* ===== Typing animation ===== */
        .typing {
            display: flex;
            align-items: center;
            justify-content: flex-start;
        }

        .typing-dot {
            height: 8px;
            width: 8px;
            background-color: white;
            border-radius: 50%;
            margin: 0 3px;
            opacity: 0.5;
            animation: blink 1.4s infinite both;
        }
        .typing-dot:nth-child(2) { animation-delay: 0.2s; }
        .typing-dot:nth-child(3) { animation-delay: 0.4s; }

        @keyframes blink {
            0%, 80%, 100% { opacity: 0.2; }
            40% { opacity: 1; }
        }

        /* ===== Input box styling ===== */
        div[data-baseweb="input"] > div {
            background-color: rgba(28,37,65,0.9) !important;
            color: white !important;
            border-radius: 12px !important;
            border: 1px solid #00b4db !important;
            font-size: 1rem !important;
            padding: 0.6rem 1rem !important;
        }

        /* Floating input box */
        .stChatInputContainer {
            position: fixed;
            bottom: 20px;
            width: 60%;
            left: 20%;
            border-radius: 16px !important;
        }

        /* ===== Fade animation ===== */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
""", unsafe_allow_html=True)

# ---------------------------
# Session state (memory)
# ---------------------------
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------------------
# Header
# ---------------------------
st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
st.markdown("<h1>Synthaura 🤖</h1>", unsafe_allow_html=True)
st.markdown("<div class='caption'>Your context-aware AI Assistant</div>", unsafe_allow_html=True)

# ---------------------------
# Display chat messages
# ---------------------------
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"<div class='user-bubble'>{msg['content']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='assistant-bubble'>{msg['content']}</div>", unsafe_allow_html=True)

# ---------------------------
# Input box for user prompt
# ---------------------------
if prompt := st.chat_input("Type your message..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.markdown(f"<div class='user-bubble'>{prompt}</div>", unsafe_allow_html=True)

    # Typing animation
    message_placeholder = st.empty()
    message_placeholder.markdown(
        """
        <div class='assistant-bubble typing'>
            <div class='typing-dot'></div>
            <div class='typing-dot'></div>
            <div class='typing-dot'></div>
        </div>
        """,
        unsafe_allow_html=True
    )

    try:
        response = requests.post(
            BACKEND_URL,
            json={
                "message": prompt,
                "conversation_id": st.session_state.conversation_id,
                "pinned": False,
            },
            timeout=60,
        )

        if response.status_code == 200:
            data = response.json()
            assistant_reply = data.get("assistant", "⚠️ No response received.")
        else:
            assistant_reply = f"⚠️ Server error: {response.status_code}"

    except Exception as e:
        assistant_reply = f"⚠️ Error connecting to backend: {e}"

    # Replace typing animation with actual reply
    message_placeholder.markdown(
        f"<div class='assistant-bubble'>{assistant_reply}</div>", unsafe_allow_html=True
    )

    # Save assistant message
    st.session_state.messages.append({"role": "assistant", "content": assistant_reply})

st.markdown("</div>", unsafe_allow_html=True)
