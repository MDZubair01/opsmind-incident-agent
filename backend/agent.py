import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

HINDSIGHT_API_KEY = os.getenv("HINDSIGHT_API_KEY", "")
HINDSIGHT_BASE_URL = os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
BANK_ID = os.getenv("BANK_ID", "opsmind-sre-production")

# In-memory post-mortem cache (fallback store)
LOCAL_INCIDENT_STORE = [
    {
        "service_name": "payment-service",
        "error_message": "OperationalError: max connections reached for role",
        "root_cause": "PostgreSQL connection pool maxed out during burst traffic surge. Idle connections were holding pool slots.",
        "fix_applied": "Terminated idle client connections and scaled active pool size via PgBouncer.",
        "runbook_cmd": "kubectl exec -it deployment/payment-db-pooler -- psql -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle';\"",
        "full_text": "[POST-MORTEM] Service: payment-service | Error: OperationalError: max connections reached | Root Cause: PostgreSQL connection pool exhausted | Resolution: Terminated idle connections | Runbook: kubectl exec -it deployment/payment-db-pooler -- psql -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle';\""
    },
    {
        "service_name": "order-api",
        "error_message": "KafkaError: CommitFailedException",
        "root_cause": "Heartbeat timeout exceeded because message processing took 45s.",
        "fix_applied": "Bumped max.poll.interval.ms from 30000 to 120000.",
        "runbook_cmd": "helm upgrade order-api ./charts --set kafka.maxPollIntervalMs=120000",
        "full_text": "[POST-MORTEM] Service: order-api | Error: KafkaError: CommitFailedException | Root Cause: Heartbeat timeout exceeded | Resolution: Bumped max.poll.interval.ms | Runbook: helm upgrade order-api ./charts --set kafka.maxPollIntervalMs=120000"
    }
]

# Initialize clients
groq_client = Groq(api_key=GROQ_API_KEY)
hindsight = None

try:
    from hindsight_client import Hindsight
    if HINDSIGHT_API_KEY:
        hindsight = Hindsight(base_url=HINDSIGHT_BASE_URL, api_key=HINDSIGHT_API_KEY)
    else:
        hindsight = Hindsight(base_url=HINDSIGHT_BASE_URL)
except Exception:
    hindsight = None


def recall_incident_context(service_name: str, error_message: str):
    """Queries Hindsight memory, falling back to local store if the API client fails."""
    query = f"Service: {service_name} Outage: {error_message}"
    memories = []

    # 1. Try cloud Hindsight API
    if hindsight:
        try:
            resp = hindsight.recall(bank_id=BANK_ID, query=query)
            items = getattr(resp, "results", resp) if resp else []
            if isinstance(items, list):
                for r in items:
                    if hasattr(r, "text"):
                        memories.append(r.text)
                    elif isinstance(r, dict) and "text" in r:
                        memories.append(r["text"])
                    elif isinstance(r, str):
                        memories.append(r)
        except Exception as e:
            print(f"Hindsight API recall skipped/failed: {e}")

    # 2. Local fallback matching
    if not memories:
        s_norm = service_name.lower().replace("-", "").replace("_", "")
        e_norm = error_message.lower()
        for item in LOCAL_INCIDENT_STORE:
            stored_s = item["service_name"].lower().replace("-", "").replace("_", "")
            stored_e = item["error_message"].lower()
            if stored_s in s_norm or s_norm in stored_s or any(w in e_norm for w in stored_e.split()[:2]):
                memories.append(item["full_text"])

    return memories


def retain_incident_resolution(service_name: str, error_message: str, root_cause: str, fix_applied: str, runbook_cmd: str):
    """Pushes verified fix to Hindsight and records in local cache."""
    memory_content = (
        f"[POST-MORTEM] Service: {service_name} | "
        f"Error: {error_message} | "
        f"Root Cause: {root_cause} | "
        f"Resolution: {fix_applied} | "
        f"Runbook: {runbook_cmd}"
    )

    # Save to local store
    LOCAL_INCIDENT_STORE.append({
        "service_name": service_name,
        "error_message": error_message,
        "root_cause": root_cause,
        "fix_applied": fix_applied,
        "runbook_cmd": runbook_cmd,
        "full_text": memory_content
    })

    # Sync to Hindsight Cloud if available
    if hindsight:
        try:
            hindsight.retain(
                bank_id=BANK_ID,
                content=memory_content,
                context="sre_incident_postmortem"
            )
        except Exception as e:
            print(f"Hindsight API retain skipped/failed: {e}")

    return {"status": "retained", "stored": memory_content}


def diagnose_incident(service_name: str, error_message: str, stack_trace: str):
    """Synthesizes incoming alert logs with historical memory via Groq."""
    past_memories = recall_incident_context(service_name, error_message)
    has_match = len(past_memories) > 0
    memory_block = "\n".join(past_memories) if has_match else "NO RELEVANT PAST INCIDENTS FOUND IN MEMORY."

    system_prompt = (
        "You are OpsMind, an autonomous SRE Incident Agent. "
        "Your goal is to reduce MTTR during critical production alerts. "
        "Analyze the incoming outage alongside past historical memories from Hindsight. "
        "Be concise, actionable, and state clear runbook commands."
    )

    user_prompt = (
        f"CURRENT PRODUCTION ALERT:\n"
        f"- Service: {service_name}\n"
        f"- Error: {error_message}\n"
        f"- Raw Stack Trace: {stack_trace}\n\n"
        f"RECALLED SRE HISTORICAL MEMORY (from Hindsight):\n"
        f"{memory_block}\n\n"
        f"Respond in the following strict format:\n"
        f"### 1. Root Cause Analysis\n"
        f"[1-2 sentences on what failed]\n\n"
        f"### 2. Historical Match Status\n"
        f"[{'Exact match retrieved from Hindsight memory' if has_match else 'Novel incident – no matching record in Hindsight.'}]\n\n"
        f"### 3. Immediate Runbook Fix\n"
        f"```bash\n"
        f"[Exact shell/kubectl/SQL command to execute]\n"
        f"```\n\n"
        f"### 4. Confidence Score\n"
        f"[{'High (Retrieved from memory)' if has_match else 'Medium'}]"
    )

    chat_completion = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.1
    )

    return {
        "analysis": chat_completion.choices[0].message.content,
        "memories_retrieved": past_memories
    }