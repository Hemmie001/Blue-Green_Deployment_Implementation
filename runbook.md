## 📘 Runbook: Observability & Alerting for Blue/Green Deployments (Stage 3)

This runbook serves as the first point of reference for operators responding to alerts from the `alert_watcher` service posted to Slack. The primary goal is to **restore service health** and **investigate the root cause** of the failure.

### 1. Alert Type: ⚠️ AUTO-FAILOVER DETECTED

| Field | Description | Operator Action |
| :--- | :--- | :--- |
| **Trigger** | Nginx detected the primary pool (e.g., Blue) as unhealthy (5xx or timeout) and successfully switched all traffic to the designated backup pool (e.g., Green). | **1. Acknowledge Alert:** Confirm receipt in Slack. **2. Isolate:** Immediately check the health status and container logs of the *failed* pool (`docker inspect app_blue`, `docker logs app_blue`). **3. Investigate Cause:** Check recent deployment/config changes. Was it a transient error, or a fatal crash? **4. Resolution:** If the issue is transient, manually switch back (`./switch_pool.sh blue`). If the issue is persistent, leave traffic on Green and begin the process to rebuild and replace the Blue container. |
| **Color** | Orange/Yellow | **Priority:** **P1** (Critical - Service is degraded, but traffic is flowing). |

### 2. Alert Type: 🔥 HIGH ERROR RATE (>X% 5XX)

| Field | Description | Operator Action |
| :--- | :--- | :--- |
| **Trigger** | The rolling average of 5xx errors (server-side errors) has exceeded the configured threshold ($ERROR\_RATE\_THRESHOLD%) over the last $WINDOW\_SIZE requests. The active pool is still attempting to serve traffic. | **1. Log Inspection:** Check detailed Nginx and application logs for the currently *active* pool (e.g., `docker logs app_green`) for stack traces, resource errors (OOM), or database connection failures. **2. Resource Check:** Inspect host-level metrics (CPU, Memory, Disk I/O) on the active application container's host. **3. Mitigation:** If the error rate is sustained and affecting users, execute a manual pool toggle as a **temporary fix** to shift traffic away from the failing service (e.g., `./switch_pool.sh blue`). **4. Post-Mitigation:** Continue detailed debugging on the newly isolated, failing service. |
| **Color** | Red | **Priority:** **P2** (High - Service is partially failing and requires immediate intervention). |

### 3. Alert Suppression (Planned Maintenance Mode)

To prevent noise during planned deployments, tests, or manual toggles:

* **Action:** Before running any planned destabilizing activity, temporarily set `ALERT_COOLDOWN_SEC=3600` (1 hour) in your local `.env` file and restart the `alert_watcher` service (`docker-compose restart alert_watcher`).
* **Restore:** After testing is complete, restore the default cooldown (300 seconds) and restart the `alert_watcher` to re-enable live monitoring.

---

This completes the Stage 3 implementation. You now have the full set of files to populate your GitHub repository and begin verification. 

Would you like me to generate the optional `DECISION.md` for this stage, or are you ready to proceed with verification and submission preparation?
