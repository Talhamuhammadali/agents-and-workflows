# Agent-Driven Kubernetes Operator — Design

Kopf (Python) operator that an AI agent uses to build, manage, and watch cluster resources. Design phase.

## Intent

An AI agent declares what it needs; the operator materializes it as Kubernetes resources, manages their lifecycle, and watches for failures. Deterministic problems self-heal; ambiguous ones escalate back to the agent. The agent can also read health, events, and logs of what it deployed.

## Flow

```
Agent (LLM)  →  structured tool call
             →  [Gate 1: pydantic]  validate agent output
             →  translate to CR spec (deterministic)
             →  submit CR
             →  [Gate 2: CRD OpenAPI/CEL]  validate cluster state
             →  kopf handler reconciles → child resources (owner-ref'd)
             →  timers/daemons watch health + orphans
             →  status ← digest;  escalation → Redis stream → agent
```

## Two validation gates (not redundant)

| | Gate 1 — pydantic | Gate 2 — CRD OpenAPI + CEL |
|---|---|---|
| Guards | shape of valid **agent output** | shape of valid **cluster state** |
| Runs | in-process, **before** CR is submitted | server-side, at the API server |
| Covers | only the agent's path | every writer (agent, kubectl, drift) |
| On failure | catchable `ValidationError` → repair signal to agent | API rejects the CR |

Both are needed. Gate 1 gives the agent a fast, LLM-legible failure with no round-trip and only exists on the path the agent controls. Gate 2 is the Kubernetes-native contract that holds for anything not written by the agent.

**Keep them separate on purpose.** Do not generate the CRD schema from the pydantic model. The two sets overlap but differ — the pydantic model may carry decision fields that never reach the CR; the CRD carries status/defaulting the agent never touches. Hand-maintain both.

**Divergence = telemetry.** Gate 1 passes but Gate 2 rejects → either the two contracts have drifted or the translation step corrupted a valid spec. Log loudly and route to engineering, not the agent — the LLM can't repair a code defect.

## Lifecycle

- Handlers: `on.create` / `on.update` / `on.delete` / `on.resume`.
- **Owner references are the primary mechanism, not the delete handler.** `kopf.adopt()` on every child → Kubernetes cascade-GC deletes children when the CR is deleted. Don't hand-roll cleanup owner refs already provide.
- Validate/parse with pydantic at the handler boundary; write status with `model_dump(mode="json", by_alias=True, exclude_none=True)` — `mode="json"` is required or datetimes/enums fail to serialize.
- camelCase ↔ snake_case: set `alias_generator=to_camel`, `populate_by_name=True` once on a base model.

## Orphan taxonomy → auto-resolve vs escalate

| Case | Detection | Action |
|---|---|---|
| Child unhealthy (crashloop) | `@kopf.timer`/`daemon`, compare `readyReplicas` | write to status; escalate if persistent |
| Child missing (someone deleted it) | periodic reconcile | **auto:** recreate from desired state |
| Orphan, dead owner | watch child types via `on.event` | **auto:** GC it |
| Zombie (labeled, no live CR) | singleton **sweep** (list by label, diff vs live CRs) | flag/escalate |

Deterministic reconciliation is dumb and mechanical. **Never call the LLM from inside the reconcile loop** — no non-determinism, latency, or cost in a hot path. Only the ambiguous cases escalate.

## Escalation channel

Controller auto-resolves deterministic cases; escalates ambiguous ones by pushing onto a **Redis stream** consumed by an ARQ worker / LangGraph agent. Keeps the controller fire-and-forget; reuses existing buffer-and-replay. (Status-as-queue is the more k8s-native alternative but higher friction given the existing stack.)

**As built (spec-01 PoC):** shipped with the **status-as-queue** path, not Redis — a failed child sets `status.phase = Failed` and adds a `NeedsAttention` condition naming the failed children. The spec-02 agent polls that condition (`check_escalations` is a stub over the same status read for now). Redis remains the intended production channel; the seam is unchanged.

## Observability (agent-visible logs + "describe")

- **"Describe" is a composite**, not an endpoint: GET the object (spec/status/conditions) + **Events API** (`fieldSelector=involvedObject.uid=...`). Events hold the useful signals (FailedScheduling, Unhealthy, BackOff).
- **Logs** = pod log subresource: `GET .../pods/{pod}/log`. Use `previous=true` for crashloop diagnosis (live container is empty), `follow=true` to stream.
- **Both are ephemeral**: events TTL ~1h; pod logs die with the pod. This drives the design:
  - On-demand / ephemeral OK → read-path service with a scoped SA queries the API directly. Operator not involved.
  - Durable ("what happened last Tuesday") → capture before GC via Loki / OTel-logs pipeline (fits air-gapped BYOC, reuses existing OTel collector).
- Operator writes only a **digest** (last N events, health condition) into `.status` — a pointer, never the raw stream (status has ~1.5MB ceiling; high-churn writes cause watch storms).
- **Attribution ("who is using the agent")** is a labeling problem: stamp requesting user/session as a label at CR creation → owner refs propagate it to every child, event, and log query.

## RBAC (least privilege, regulated BYOC)

Read-path SA needs `get` on **`pods/log`** (subresource, separate from `get pods`) + `list`/`watch` on events. Read-only role, distinct from the operator's write role.

## Caveats

- **Kopf is single-active**, not leader-elected HA. Peering prevents split-brain but it's not controller-runtime HA. Fine for PoC/internal; flag if production-critical.
- **Operator downtime creates orphans.** `on.resume` must re-adopt every existing CR and restart its timers/daemons on boot — closes the gap after crash/redeploy.
