import streamlit as st
import requests
import threading
import time
import os
import sys

# Ensure project root is in Python path to import backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

API_URL = "http://127.0.0.1:8000"

# --- Automatic Background Backend Launcher for Streamlit Cloud ---
@st.cache_resource
def start_backend_server():
    try:
        import uvicorn
        from backend.main import app

        def run_server():
            config = uvicorn.Config(app=app, host="127.0.0.1", port=8000, log_level="warning")
            server = uvicorn.Server(config)
            server.run()

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()

        # Wait up to 5 seconds for the backend to start accepting connections
        for _ in range(10):
            try:
                r = requests.get(f"{API_URL}/docs", timeout=1)
                if r.status_code == 200:
                    break
            except Exception:
                time.sleep(0.5)
        return True
    except Exception as e:
        st.sidebar.error(f"Backend init error: {e}")
        return False

start_backend_server()

# --- Streamlit UI ---
st.set_page_config(page_title="OpsMind | SRE Incident Agent", layout="wide")
st.title("OpsMind: Autonomous Incident Response Agent")
st.caption("Powered by Vectorize Hindsight persistent memory and Groq LLM inference")

tab1, tab2 = st.tabs(["Active Outage Triage", "Post-Mortem Resolution (Teach Agent)"])

with tab1:
    st.subheader("Simulate Incoming Alert")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        service = st.selectbox("Service Affected", ["payment-service", "auth-service", "order-api", "inventory-db"])
        error = st.text_input("Error Signature", value="OperationalError: max connections reached for role 'pg_user'")
        stack = st.text_area("Stack Trace", value="File 'db/session.py', line 45 in get_db\nTimeoutError: QueuePool limit of size 5 overflow 10 reached")
        
        triage_btn = st.button("Trigger OpsMind Diagnosis", type="primary")

    with col2:
        if triage_btn:
            with st.spinner("OpsMind querying Hindsight memory and diagnosing with Groq..."):
                try:
                    res = requests.post(f"{API_URL}/triage", json={
                        "service_name": service,
                        "error_message": error,
                        "stack_trace": stack
                    })
                    if res.status_code == 200:
                        data = res.json()
                        st.success("Triage Analysis Generated!")
                        st.markdown(data["analysis"])
                        with st.expander("Inspected Hindsight Recalled Memories"):
                            st.write(data.get("memories_retrieved", []))
                    else:
                        st.error("Error communicating with OpsMind API.")
                except Exception as e:
                    st.error(f"Failed to connect to backend: {e}")

with tab2:
    st.subheader("Submit Post-Mortem Fix (Retain in Hindsight)")
    with st.form("resolve_form"):
        r_service = st.text_input("Service", value="order-api")
        r_error = st.text_input("Error Message", value="KafkaError: CommitFailedException")
        r_cause = st.text_area("Root Cause", value="Heartbeat timeout exceeded because message processing took 45s.")
        r_fix = st.text_area("Fix Applied", value="Bumped max.poll.interval.ms from 30000 to 120000.")
        r_cmd = st.text_input("Runbook Command", value="helm upgrade order-api ./charts --set kafka.maxPollIntervalMs=120000")
        
        submit = st.form_submit_button("Teach OpsMind (Hindsight retain)")
        if submit:
            try:
                res = requests.post(f"{API_URL}/resolve", json={
                    "service_name": r_service,
                    "error_message": r_error,
                    "root_cause": r_cause,
                    "fix_applied": r_fix,
                    "runbook_cmd": r_cmd
                })
                if res.status_code == 200:
                    st.success("Resolution retained in Hindsight memory! Next time this alert fires, OpsMind will know how to fix it.")
                else:
                    st.error(f"Error from backend: {res.status_code}")
            except Exception as e:
                st.error(f"Failed to connect to backend: {e}")