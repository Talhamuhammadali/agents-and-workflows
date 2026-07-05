---
spec: 02
title: WorkloadPlan Agent (base-harness ReAct agent)
status: draft / PoC
depends_on: [spec-01-crd-operator]
built_on: agentic_patterns/base (build_agent)
---

# Spec 02 — `WorkloadPlan` Agent

Build **after** spec 01. Once the CRD + operator exist, the agent's job is small:
**author a `WorkloadPlan`, read its status, report.** All the "smarts" (reading
AWS, typing intent, mapping ALB→nginx) live here, agent-side — the operator stays
dumb.

## Mental model

The seam is the CR: the **agent owns `spec`**, the **operator owns `status`**.
The agent declares desired state (Gate 1 pydantic → submit CR), then polls
`status.phase` until `Ready`. It never writes status; the operator never calls
the agent. Migration and provisioning are the *same* agent flow — they differ
only in where the desired components come from.

## Goals

1. A new agent under `agentic_patterns/k8s_agent/` built on `build_agent`, reusing
   the base toolset, with a `k8s` **skill** that unlocks a narrow, typed tool set.
2. **Gate 1**: a pydantic `PlanModel` the `declare_plan` tool validates before
   submitting the CR. `ValidationError` → repair message to the LLM (via
   `tool_reply`), no cluster round-trip.
3. Both persona flows work end-to-end against the spec-01 operator on minikube.

## Non-goals (PoC)

- Redis escalation stream (operator side is spec-01 non-goal too). `check_escalations`
  is a **polling tool**, stubbed now, wired later.
- Approval-gate blocking (personas are `required: false`).
- Raw-AWS source adapters (boto3). Source = **EKS** (already-k8s objects).

---

## Directory shape (mirror `general_agent`)

```
agentic_patterns/k8s_agent/
  agent.py      # K8S_AGENT_BUILDER = build_agent(TOOLS, K8sAgentState, K8sAgentContext)
  state.py      # K8sAgentState / K8sAgentContext (extend base)
  prompts.py    # system prompt
agentic_patterns/shared/
  k8s_tools.py                # new tools, registered into TOOLS_BY_NAME
  skills/k8s/SKILL.md         # gates the k8s tools + carries the mapping table
```

`K8sAgentContext` adds the two cluster **roles** (not a bare context string):

```python
@dataclass
class K8sAgentContext(BaseAgentContext):
    source_context: str | None = None   # SOURCE role: read-only (EKS)
    target_context: str = "minikube"    # TARGET role: write CR + read status
    target_namespace: str = "default"
```

`K8sAgentState` adds `plan_name: NotRequired[str]` (the CR under management this run).

---

## Tools (unlocked by the `k8s` skill)

| Tool | Role | Does |
|---|---|---|
| `discover_source(namespace)` | SOURCE (read-only) | List native objects on EKS; write `inventory.md` to workspace. `get/list` only. |
| `declare_plan(name, components)` | TARGET | **Gate 1** validate → build `WorkloadPlan` → server-side apply the ONE CR. Idempotent (re-apply = update). |
| `get_plan_status(name)` | TARGET | Read `status.phase`, `readyCount`, `children[]`. The poll loop. |
| `describe(role, ref)` | either | Composite: GET object (spec/status/conditions) + Events for its uid. |
| `logs(role, pod, previous=False)` | either | Pod log subresource. `previous=True` for crashloop; how the agent reads Persona B's benchmark output. |
| `check_escalations()` | — | **Stub** for PoC (returns empty). Later: poll operator's Redis stream. |

Plus base tools the skill also unlocks: `Read`/`Write`/`Edit` (the `inventory.md`
artifact), `Todos` (one per component), `Ask` (ambiguous mappings). **Not** `bash`
— structured surface only, so every write is Gate-1 validated.

### Kube client abstraction

One helper resolves a **role** → kubeconfig context → client. `SOURCE` is
read-only by construction (only `get/list` wrappers exposed); `TARGET` can write
the CR and read status. This is the single seam where AWS-vs-minikube (and, later,
a second target) is config, not code.

---

## Gate 1 — `PlanModel` (pydantic)

Mirrors the CRD shape but is the agent's **decision vocabulary**, not the CR:

```python
class Component(BaseModel):
    name: str
    manifest: dict                       # a real k8s object (apiVersion+kind+...)
    source_ref: str | None = None        # migrate: where it came from
    accepted_losses: list[str] = []      # migrate: declared lossy mappings

class PlanModel(BaseModel):
    intent: Literal["migrate", "provision"]
    components: list[Component] = Field(min_length=1)
    # validators: unique names; each manifest has apiVersion+kind;
    #             kind ∈ operator's grantable set (else fail fast, agent-legible)
```

`declare_plan` translates `PlanModel` → the CR (`accepted_losses`/`source_ref`
become annotations on the component so the loss is **declared in the CR**, not
just in chat), then applies it.

---

## The mapping table (migration intelligence)

Lives in `skills/k8s/SKILL.md` so it's injected when the skill loads. Hybrid:
**table for the known, LLM for the novel, `Ask` for the ambiguous.**

| Source (AWS/EKS) | Target (minikube) | Note |
|---|---|---|
| ALB / NLB Ingress | nginx Ingress | drops WAF/ACM cert; host preserved → `accepted_losses` |
| Service `LoadBalancer` | `NodePort` | no cloud LB locally |
| EBS PVC (`gp3`) | `standard` / hostPath PVC | storage class differs |
| Secrets Manager ref | k8s `Secret` | value must be supplied/re-created |
| IAM role (IRSA) | *(none)* | → `Ask`: how to grant equivalent access |

Unlisted/ambiguous → `Ask` the user; write the answer into `accepted_losses`.

---

## Flows (from `personas.md`)

**Persona A — migrate:** `discover_source` → write `inventory.md` → map via table
(ALB→nginx recorded as accepted loss) → `declare_plan(intent="migrate", ...)` →
poll `get_plan_status` until `Ready` → report (incl. accepted losses).

**Persona B — provision:** capture intent → `declare_plan(intent="provision", ...)`
with a vLLM `Deployment` + a benchmark `Job` as components → poll until `Ready`
(Job `succeeded`) → `logs(target, <bench-pod>)` to read tok/s + p95 → report.

---

## Milestones (build in this order)

1. **Scaffold.** New dir + `build_agent` wiring + empty `k8s` skill; agent boots,
   loads skill, sees the tools.
2. **`declare_plan` (Gate 1 → CR).** Hardcode a provision `PlanModel`; validate;
   apply; confirm the operator (spec 01) reconciles it. *(proves the seam)*
3. **`get_plan_status` poll loop** → agent reports `Ready`.
4. **Persona B end-to-end** (all agent-authored, incl. reading benchmark logs).
5. **`discover_source` + mapping table** → Persona A end-to-end.
6. **`check_escalations` stub** in the loop (returns empty) — placeholder for the
   Redis wiring later.

**Acceptance:** from a natural-language prompt, the agent drives each persona to
a healthy plan and reports — with zero hand-written CRs (spec 01's acceptance used
hand-written ones; here the agent authors them).
