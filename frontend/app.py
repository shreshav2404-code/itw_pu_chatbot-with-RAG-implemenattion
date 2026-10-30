"""PU Assist – Streamlit chat page for students.

Runs in a Docker container (Data Lab / Portainer, no GPU) and sends every question to the backend API
served by notebook 03 on the GPU.  Settings come from environment variables:
  BACKEND_URL      address of notebook 03's API, e.g. http://10.0.0.12:8000
  PU_API_KEY       the key printed by notebook 03
  REQUEST_TIMEOUT  seconds to wait for an answer (default 300)
"""
import os
import uuid

import requests
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.environ.get("PU_API_KEY", "")
TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "300"))
HEADERS = {"X-API-Key": API_KEY}
AVATAR = "🎓"

st.set_page_config(page_title="PU Assist", page_icon=AVATAR, layout="centered")

ss = st.session_state
ss.setdefault("session_id", uuid.uuid4().hex)   # one chat history per browser tab on the backend
ss.setdefault("messages", [])
ss.setdefault("voice_key", 0)                   # bumping it clears the voice recorder


# ---------------------------------------------------------------- backend calls
@st.cache_data(ttl=15, show_spinner=False)
def backend_health():
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"status": "offline", "error": str(e)}


def ask_backend(question, image=None, audio=None):
    files = {}
    if image is not None:
        files["image"] = (image.name or "image.jpg", image.getvalue(), image.type or "image/jpeg")
    if audio is not None:
        files["audio"] = (audio.name or "voice.wav", audio.getvalue(), audio.type or "audio/wav")
    r = requests.post(f"{BACKEND_URL}/ask", headers=HEADERS, timeout=TIMEOUT,
                      data={"question": question, "session_id": ss.session_id}, files=files or None)
    if r.status_code == 401:
        raise RuntimeError("This page's PU_API_KEY does not match the backend's API key.")
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail", r.text)
        except ValueError:
            detail = r.text
        raise RuntimeError(f"{detail} (error {r.status_code})")
    return r.json()


def reset_backend():
    try:
        requests.post(f"{BACKEND_URL}/reset", headers=HEADERS, data={"session_id": ss.session_id}, timeout=10)
    except requests.RequestException:
        pass


# ---------------------------------------------------------------- rendering
def show_message(m):
    if m["role"] == "user":
        with st.chat_message("user"):
            st.markdown(m["text"] or "_(voice question)_")
            if m.get("image"):
                st.image(m["image"], width=220)
            if m.get("voice"):
                st.caption("🎤 voice note")
        return
    with st.chat_message("assistant", avatar=AVATAR):
        if m.get("error"):
            st.error(m["error"])
            return
        if m.get("heard"):
            st.caption(f"🎤 Heard: “{m['heard']}”")
        st.markdown(m["text"])
        sources = m.get("sources") or []
        shown = [s for s in sources if s["cited"]] or sources
        if shown:
            with st.expander(f"Sources ({len(shown)})"):
                for s in shown:
                    title = f"[{s['title']}]({s['url']})" if s.get("url") else s["title"]
                    st.markdown(f"**[{s['n']}]** {title}  \n<small>{s['kind']}</small>", unsafe_allow_html=True)
        if m.get("timings"):
            st.caption("⏱ " + " · ".join(f"{k} {v}s" for k, v in m["timings"].items() if v))


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.title(f"{AVATAR} PU Assist")
    st.caption("Presidency University help desk")
    health = backend_health()
    if health.get("status") == "ok":
        st.success(f"Online · {health.get('chunks', 0):,} document chunks")
        if health.get("busy"):
            st.info("Answering another student right now – your question will wait in the queue.")
    else:
        st.error("The answer server is offline.")
        st.caption("The GPU notebook (03_backend_api) must be running.")

    if st.button("🗑 New conversation"):
        reset_backend()
        ss.session_id, ss.messages = uuid.uuid4().hex, []
        st.rerun()

    st.divider()
    st.subheader("🎤 Ask by voice")
    st.caption("English, Hindi, Kannada and more.")
    voice = st.audio_input("Record your question", key=f"voice_{ss.voice_key}")
    send_voice = st.button("Ask with this recording", disabled=voice is None)

    st.divider()
    st.caption("Answers come from official university documents and list their sources. "
               "Always confirm fees, dates and deadlines with the latest official notice.")


# ---------------------------------------------------------------- main chat
st.title("PU Assist")
st.caption("Ask about exams, attendance, fees, scholarships, programmes or the campus. "
           "Attach a photo of a notice or timetable with the 📎 button.")

for m in ss.messages:
    show_message(m)

prompt = st.chat_input("Type your question…", accept_file=True, file_type=["jpg", "jpeg", "png", "webp"])

question = image = audio = None
if prompt:
    question = (prompt.text or "").strip()
    image = prompt.files[0] if prompt.files else None
    if not question and image is not None:
        question = "What does this mean for me?"
elif send_voice and voice is not None:
    question, audio = "", voice

if question is not None and (question or audio is not None):
    user_msg = {"role": "user", "text": question, "voice": audio is not None,
                "image": image.getvalue() if image is not None else None}
    ss.messages.append(user_msg)
    show_message(user_msg)
    with st.chat_message("assistant", avatar=AVATAR):
        with st.spinner("Thinking… (usually 10–40 seconds)"):
            try:
                r = ask_backend(question, image, audio)
                reply = {"role": "assistant", "text": r["answer"], "sources": r["sources"], "timings": r["timings"],
                         "heard": r["question"] if r.get("heard") else None}
            except requests.ConnectionError:
                reply = {"role": "assistant", "error": "The answer server is offline. "
                                                       "(The GPU notebook 03_backend_api must be running.)"}
            except requests.Timeout:
                reply = {"role": "assistant", "error": "The answer took too long. Please try again."}
            except Exception as e:
                reply = {"role": "assistant", "error": str(e)}
    ss.messages.append(reply)
    if audio is not None:
        ss.voice_key += 1
    st.rerun()
