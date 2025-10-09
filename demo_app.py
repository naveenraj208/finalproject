# demo_app.py
import streamlit as st
import requests
import json

API = "http://127.0.0.1:8000"

st.title("Adaptive Context-Aware Memory Framework 💡")

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None

# Create or reuse conversation
if st.session_state.conversation_id is None:
    if st.button("Start New Conversation"):
        res = requests.post(f"{API}/conversations", json={"title": "Demo Chat"})
        st.session_state.conversation_id = res.json()["id"]
        st.success(f"Conversation created: {st.session_state.conversation_id}")
else:
    st.info(f"Conversation ID: {st.session_state.conversation_id}")

# Add message
with st.form("msg_form"):
    sender = st.selectbox("Sender", ["user", "assistant"])
    content = st.text_area("Message")
    importance = st.slider("Importance", 0.0, 1.0, 0.5)
    pinned = st.checkbox("Pinned?")
    submit = st.form_submit_button("Add Message")

if submit and content:
    body = {
        "conversation_id": st.session_state.conversation_id,
        "sender": sender,
        "content": content,
        "importance": importance,
        "pinned": pinned
    }
    res = requests.post(f"{API}/messages", json=body)
    st.success("Message added!")

# Show conversation
if st.session_state.conversation_id:
    res = requests.get(f"{API}/conversations/{st.session_state.conversation_id}/messages")
    msgs = res.json()
    for m in msgs:
        st.markdown(f"**{m['sender']}**: {m['content']} _(priority {m['priority']:.2f})_")

# Prompt building
if st.button("Build Optimized Prompt"):
    q = st.text_input("Optional retrieval query (blank for none)")
    params = {"token_budget": 1024}
    if q:
        params["query"] = q
    res = requests.get(f"{API}/conversations/{st.session_state.conversation_id}/prompt", params=params)
    data = res.json()
    st.subheader("Adaptive Prompt")
    st.text_area("Prompt Text", data["raw_prompt_text"], height=300)
    st.write(f"Total tokens: {data['total_tokens']}")

# Semantic retrieval
query = st.text_input("Semantic Search Query")
if st.button("Retrieve"):
    res = requests.get(f"{API}/conversations/{st.session_state.conversation_id}/retrieve", params={"query": query})
    for r in res.json():
        st.markdown(f"🔍 **Match** ({r['priority']:.2f}): {r['content']}")
