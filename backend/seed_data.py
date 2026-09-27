from agent import retain_incident_resolution

def seed_memories():
    print("Seeding initial historical incident memories into Hindsight...")
    
    retain_incident_resolution(
        service_name="payment-service",
        error_message="OperationalError: max connections reached for role 'pg_user'",
        root_cause="Stripe webhook traffic spike leaked DB connections due to missing connection pooling timeout.",
        fix_applied="Increased pool_size in SQLAlchemy engine and restarted billing worker pods.",
        runbook_cmd="kubectl scale deployment/payment-worker --replicas=0 && kubectl scale deployment/payment-worker --replicas=4"
    )

    retain_incident_resolution(
        service_name="auth-service",
        error_message="Redis::CommandError: OOM command not allowed when used memory > 'maxmemory'",
        root_cause="Session JWT revocation cache had missing TTL expiry policy.",
        fix_applied="Applied allkeys-lru eviction policy and flushed expired session tokens.",
        runbook_cmd="redis-cli CONFIG SET maxmemory-policy allkeys-lru"
    )
    
    print("Seeding complete! Hindsight is primed with baseline incidents.")

if __name__ == "__main__":
    seed_memories()