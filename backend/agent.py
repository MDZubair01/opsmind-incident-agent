import os
from dotenv import load_dotenv
from hindsight_client import Hindsight
from groq import Groq

load_dotenv()

HINDSIGHT_API_KEY = os.getenv("HINDSIGHT_API_KEY")
HINDSIGHT_BASE_URL = os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
BANK_ID = os.getenv("BANK_ID", "opsmind-sre-production")

# Initialize clients
hindsight = Hindsight(base_url=HINDSIGHT_BASE_URL)
groq_client = Groq(api_key=GROQ_API_KEY)


def recall_incident_context(service_name: str, error_message: str):
    """Queries Hindsight memory for similar historical incidents."""
    query = f"Service: {service_name} Outage: {error_message}"
    try:
        results = hindsight.recall(bank_id=BANK_ID, query=query)
        if not results:
            return []
        return [r.text if hasattr(r, 'text') else str(r) for r in results]
    except Exception as e:
        print(f"Error querying Hindsight: {e}")
        return []


def retain_incident_resolution(service_name: str, error_message: str, root_cause: str, fix_applied: str, runbook_cmd: str):
    """Pushes a verified incident fix into Hindsight so the agent learns over time."""
    memory_content = (
        f"[POST-MORTEM] Service: {service_name} | "
        f"Error: {error_message} | "
        f"Root Cause: {root_cause} | "
        f"Resolution: {fix_applied} | "
        f"Runbook: {runbook_cmd}"
    )
    return hindsight.retain(
        bank_id=BANK_ID,
        content=memory_content,
        context="sre_incident_postmortem"
    )


def diagnose_incident(service_name: str, error_message: str, stack_trace: str):
    """Synthesizes incoming alert logs with Hindsight memory using Groq."""
    past_memories = recall_incident_context(service_name, error_message)
    memory_block = "\n".join(past_memories) if past_memories else "NO RELEVANT PAST INCIDENTS FOUND IN MEMORY."

    system_prompt = """You are OpsMind, an autonomous SRE Incident Agent. 
Your goal is to reduce MTTR (Mean Time to Resolution) during critical production alerts.
Analyze the incoming outage alongside past historical memories from Hindsight.
Be concise, actionable, and state clear runbook commands."""

    user_prompt = f"""
CURRENT PRODUCTION ALERT:
- Service: {service_name}
- Error: {error_message}
- Raw Stack Trace: {stack_trace}

RECALLED SRE HISTORICAL MEMORY (from Hindsight):
{memory_block}

Respond in the following strict format:
### 1. Root Cause Analysis
[1-2 sentences on what failed]

### 2. Historical Match Status
[State whether this was matched from Hindsight memory or is a novel incident]

### 3. Immediate Runbook Fix
```bash
[Exact shell/kubectl/SQL command to execute]