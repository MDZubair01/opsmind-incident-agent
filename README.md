# OpsMind — Autonomous SRE Incident Response Agent 🚨🧠

> Autonomous incident triage and continuous runbook retention powered by **Vectorize Hindsight** persistent memory and **Groq** ultra-low-latency LLM inference.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://opsmind-incident-agent.streamlit.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📌 Problem Statement
During production outages, engineers lose critical Mean Time to Resolution (MTTR) searching through fragmented documentation, Slack channels, and outdated wiki runbooks to find past fixes. 

**OpsMind** eliminates alert fatigue by acting as an autonomous SRE co-pilot that:
1. Recalls verified historical incident post-mortems and fixes from persistent memory.
2. Ingests raw stack traces and alert signatures to synthesize an instant root-cause analysis.
3. Provides copy-paste shell/kubectl runbook commands to restore service immediately.
4. Allows on-call engineers to teach the agent new resolutions on the fly.

---

## ⚙️ Architecture

```text
[ Incoming Alert / Stack Trace ]
               │
               ▼
   [ Streamlit Control Plane ]
               │
               ▼
   [ Vectorize Hindsight ] ──► Recalls historical post-mortems & fixes
               │
               ▼
        [ Groq LLM ]       ──► Fast inference combining logs + memory
               │
               ▼
[ Instant Root Cause & Runbook Command ]