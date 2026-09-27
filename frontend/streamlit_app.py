import streamlit as st
import os
import sys

# Ensure root directory is in Python path to import agent.py directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent import diagnose_incident, retain_incident_resolution

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
                    data = diagnose_incident(
                        service_name=service,
                        error_message=error,
                        stack_trace=stack
                    )
                    st.success("Triage Analysis Generated!")
                    st.markdown(data.get("analysis", ""))
                    with st.expander("Inspected Hindsight Recalled Memories"):
                        st.write(data.get("memories_retrieved", []))
                except Exception as e:
                    st.error(f"Execution error: {e}")

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
                res = retain_incident_resolution(
                    service_name=r_service,
                    error_message=r_error,
                    root_cause=r_cause,
                    fix_applied=r_fix,
                    runbook_cmd=r_cmd
                )
                st.success("Resolution retained in Hindsight memory! Next time this alert fires, OpsMind will know how to fix it.")
            except Exception as e:
                st.error(f"Resolution error: {e}")