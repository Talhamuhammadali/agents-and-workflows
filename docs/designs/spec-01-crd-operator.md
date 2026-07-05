---
spec: 01
title: WorkloadPlan CRD + Kopf Operator
status: draft / PoC
depends_on: []
blocks: [spec-02-agent]
target_cluster: local minikube
---

# Spec 01 — `WorkloadPlan` CRD + Kopf Operator

Build the **ownership ledger** first. The agent (spec 02) is easy once this
exists, because the agent's whole job becomes "author a `WorkloadPlan` and read
its status."

## Mental model

The operator is **not** an apply tool. It is a durable, queryable answer to:
*"what does this agent session own, and is it healthy?"* `kubectl` can see the
resources but can't tell you they belong to one session, can't delete them as a
unit, and can't self-heal them. The CR is the **root of an ownership tree**;
owner-refs propagate that ownership (and attribution labels) to every child.

For the PoC the operator is deliberately **`kubectl apply` + own + watch + heal**.
Intelligence (reading AWS, typing intent, mapping ALB→nginx) lives agent-side.
Every component is a raw manifest the operator *adopts* — which is exactly what
lets 3rd-party CRs slot in later as additive **health adapters**, with no schema
change.

## Goals

1. A single namespaced CRD, `WorkloadPlan`, whose `spec.components[]` is a list
   of named raw manifests.
2. A Kopf operator that, per plan: applies each component, stamps an owner-ref +
   attribution labels, watches health, and aggregates one `status.phase`.
3. Single-point cleanup: delete the CR → cascade-GC removes every child.
4. Survive operator restart (`on.resume` re-adopts) and heal deleted children.

## Non-goals (PoC)

- Gate 1 (pydantic) — that's agent-side, spec 02.
- Approval gates, Redis escalation stream, multi-cluster/AWS target.
- Per-kind least-privilege RBAC (PoC uses one namespaced role; see RBAC note).
- `resultDigest` in status — benchmark numbers are read from Job logs by the agent.

---

## The CRD

Group `poc.local`, version `v1alpha1`, kind `WorkloadPlan`, plural
`workloadplans`, short name `wp`. Namespaced.

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: workloadplans.poc.local
spec:
  group: poc.local
  scope: Namespaced
  names:
    kind: WorkloadPlan
    plural: workloadplans
    singular: workloadplan
    shortNames: [wp]
  versions:
    - name: v1alpha1
      served: true
      storage: true
      subresources:
        status: {}
      additionalPrinterColumns:
        - { name: Phase, type: string, jsonPath: .status.phase }
        - { name: Children, type: integer, jsonPath: .status.readyCount }
        - { name: Age, type: date, jsonPath: .metadata.creationTimestamp }
      schema:
        openAPIV3Schema:
          type: object
          required: [spec]
          properties:
            spec:
              type: object
              required: [components]
              properties:
                intent:                       # attribution label ONLY, not a branch
                  type: string
                  enum: [migrate, provision]
                components:
                  type: array
                  minItems: 1
                  x-kubernetes-list-type: map # enforces unique name + SSA merge per item
                  x-kubernetes-list-map-keys: [name]
                  items:
                    type: object
                    required: [name, manifest]
                    properties:
                      name: { type: string }
                      manifest:
                        type: object
                        required: [apiVersion, kind]   # Gate 2: every component is a real object
                        x-kubernetes-preserve-unknown-fields: true
                        properties:
                          apiVersion: { type: string }
                          kind: { type: string }
            status:
              type: object
              x-kubernetes-preserve-unknown-fields: true
              properties:
                phase:
                  type: string
                  enum: [Pending, Ready, Failed]
                observedGeneration: { type: integer }
                readyCount: { type: integer }
                children:
                  type: array
                  items:
                    type: object
                    properties:
                      name:  { type: string }
                      kind:  { type: string }
                      ready: { type: boolean }
                      note:  { type: string }   # short reason, not a log dump
                conditions:
                  type: array
                  items:
                    type: object
                    properties:
                      type:    { type: string }
                      status:  { type: string }
                      reason:  { type: string }
                      message: { type: string }
```

**Gate 2 (server-side) buys, for free:**
- `list-type: map` on `name` → duplicate component names rejected by the API.
- `required: [apiVersion, kind]` on `manifest` → no malformed component reaches a handler.
- `status` subresource → the operator writes status without bumping `metadata.generation`.

## Attribution labels

Stamp on the CR at creation and copy onto **every** child in the reconcile loop:

```
poc.local/plan       = <cr name>
poc.local/session    = <agent session id>
poc.local/owner      = <requesting user>
poc.local/component  = <component name>   # child only
```

This is what makes the ledger *queryable by who/what*:
`kubectl get all -l poc.local/session=<id>`.

---

## Kopf handlers

Give responsibilities; you write the bodies.

| Handler | Responsibility |
|---|---|
| `@kopf.on.create` / `@kopf.on.update` | Reconcile. For each `spec.components[]`: `kopf.adopt(manifest)` (owner-ref), add attribution labels, **server-side apply** it. Record `{name, kind, ready:false}` in `status.children`. Idempotent — re-apply is a no-op. |
| `@kopf.on.resume` | On operator boot, re-adopt every existing plan and restart its health timer. Closes the orphan gap after crash/redeploy. |
| `@kopf.on.delete` | **Do nothing.** Owner-refs + cascade-GC delete children. Do not hand-roll cleanup. (Handler exists only to log.) |
| `@kopf.timer(interval=...)` | Health sweep per plan: run each child's **health adapter**, update `status.children[].ready`, recompute `phase` + `readyCount`. |
| `@kopf.daemon` (optional) | Watch child events for faster failure surfacing; not required for PoC. |

**Self-heal:** the reconcile logic is desired-state driven. If a health sweep
finds a child missing, re-apply it (recreate from `spec`). Do not wait for the
next `on.update`.

### Health adapters (the evolution seam)

A dict `kind -> is_ready(obj) -> (bool, note)`. Seed the PoC set; 3rd-party
integrations are *only* new entries here — never schema changes.

| Kind | Ready when |
|---|---|
| `Deployment` | `status.readyReplicas == spec.replicas` |
| `Job` | `status.succeeded >= 1` (complete); `Failed` if `status.failed > backoffLimit` |
| `Service`, `ConfigMap`, `Secret` | exists (apply succeeded) |
| `Pod` | `status.phase == Running` and all containers ready |
| *(unknown kind)* | applied successfully → `ready:true`, `note: "no health adapter"` |

### Phase aggregation

```
phase = Failed   if any child adapter reports failed
      = Ready    if every child is ready (Deployments healthy AND Jobs complete)
      = Pending  otherwise
```

**Escalation = status-as-queue (no Redis for the PoC).** When `phase: Failed`,
also write a `conditions[]` entry (`type: NeedsAttention`, `reason`, short
`message`) naming the offending child. That condition *is* the escalation channel
the agent's polling tool reads (spec 02).

**Decision — push vs. poll:** a notification webhook (operator POSTs "plan
failed" to an agent endpoint) was considered and **deferred**. Push would require
the agent to run a stable HTTP endpoint and give the operator an outbound
dependency (retries/buffering if the agent is down — which is what a Redis stream
would absorb). For the PoC, **polling status-as-queue** is enough and keeps the
operator fire-and-forget. Webhook/Redis push is the documented later swap, not
PoC scope.

Keep `status` a **digest**: last-known per-child ready + a short `note`. Never
write raw logs/events into status (1.5 MB ceiling; high-churn writes cause watch
storms — and with one CR aggregating N children, this CR is the hotspot).

---

## RBAC

Operator ServiceAccount needs, in its namespace:
- `workloadplans` + `workloadplans/status`: `get,list,watch,patch,update`.
- The child kinds it applies: `create,get,list,watch,patch,delete`.

**Note the tension:** "adopt any manifest" fights least-privilege — the operator
can only manage kinds its role grants. PoC: one namespaced role covering the
expected kinds (Deployment, Service, ConfigMap, Secret, Job, Pod). Production:
narrow per allowed kind, and reject components whose kind isn't grantable.

---

## Milestones (build in this order)

1. **CRD applies.** `kubectl apply` the CRD; create a hand-written `WorkloadPlan`
   with two components. It's accepted; status empty. *(validates Gate 2)*
2. **Reconcile applies children.** `on.create` applies both components with
   owner-refs + labels; `status.children` populated. `kubectl get wp` shows them.
3. **Health + phase.** Timer flips `phase` `Pending → Ready` when children are up.
4. **Cascade cleanup.** `kubectl delete wp <name>` removes all children.
5. **Resume.** Restart the operator pod → `on.resume` re-adopts, timers restart,
   no orphans.
6. **Self-heal.** `kubectl delete` one child → operator recreates it.

**Acceptance:** hand-author the Persona A (migrate) and Persona B (provision)
`WorkloadPlan`s from `personas.md`; both reach `phase: Ready` and clean up fully
via a single CR delete. (Persona B's benchmark `Job` reaching `succeeded` is what
makes its plan `Ready`.)

## Validation & TDD strategy

You can't red-green-refactor against a live cluster — the loop is minutes long
and the assertions are *eventual* ("children appear eventually"). So TDD lives in
the **pure core**, not the cluster. Same brain/hands split as the architecture,
one level down:

> Split the operator into a pure **brain** (decision functions) and a thin
> **hands** (Kopf handlers that only do I/O). TDD the brain classically at
> millisecond speed. Integration-test the hands against a cluster with polling
> assertions. A handler should be ~10 lines: parse → call pure fns → apply/patch
> → write status. Any branching logic belongs in a pure function with a test.

### Three test layers

| Layer | Cluster? | Speed | Style |
|---|---|---|---|
| **Pure logic** (phase aggregation, health adapters, child building, status digest) | no | ms | **classic red-green TDD** |
| **CRD schema / CEL** (Gate 2 accepts good, rejects bad) | API server | s | outside-in: write the reject-test first, then the CEL |
| **Reconcile behavior** (children appear, owner-refs, phase flips, cascade, resume, heal) | yes | min | acceptance tests as executable specs; polling assertions |

### Pure-function extraction list (the TDD targets)

None of these touch Kubernetes — dicts in, values out:

```python
compute_phase(children) -> "Pending" | "Ready" | "Failed"
is_ready(kind, obj) -> (bool, note)        # one per health adapter
build_child(component, owner_meta) -> dict # stamps owner-ref + attribution labels
plan_status_digest(children) -> dict       # the status written back
```

Example red-green (write the tests first):

```python
def test_phase_ready_when_all_ready():   assert compute_phase([{"ready":True},{"ready":True}]) == "Ready"
def test_phase_failed_if_any_failed():   assert compute_phase([{"ready":True},{"ready":False,"failed":True}]) == "Failed"
def test_phase_pending_while_converging():assert compute_phase([{"ready":True},{"ready":False}]) == "Pending"
```

### Integration layer — keep it non-flaky

- **Kopf handlers are async fns** — call them directly with a **fake k8s client** and
  assert *what they tried to apply* (owner-ref present? labels stamped?) with no
  cluster. Pulls most "hands" testing into the fast loop.
- **Never `sleep`.** Assert eventual state with poll-until-timeout:
  `wait_until(lambda: get_children(plan), timeout=30, interval=1)`.
- **Test cluster:** minikube (have it) or **kind** (ephemeral, CI-friendly).
- **Mark the slow layer** so the TDD loop stays fast:
  `@pytest.mark.integration` → default `pytest` runs pure + fake-client only
  (sub-second); `pytest -m integration` runs the cluster tests.

### Milestones → test mapping (outside-in)

Each milestone is a failing acceptance test driven to green; the logic inside is
TDD'd as pure units first.

1. CRD applies / rejects bad specs → **CEL tests** (apply YAML, assert reject *first*).
2. Reconcile applies children → `build_child` (pure TDD) + one integration poll for owner-refs/labels.
3. Health + phase → `compute_phase` + `is_ready` (pure TDD) + integration "phase → Ready".
4. Cascade cleanup → owner-ref-stamped assertion (unit) + one integration "delete CR → children gone".
5. Resume / 6. Self-heal → integration only (restart / delete-child, poll for re-adopt / recreate).

### Dev deps to add

`kopf`, `kubernetes`, `pytest-asyncio` (async handlers), + kind-or-minikube for the
`integration` marker. Fits the existing `pytest` / `tests/` layout.

### The judgment call

For each thing a handler does, ask: **decision (pure → TDD) or side effect (I/O →
integration)?** Get that split right and TDD falls out; get it wrong and you'll be
testing logic through a cluster (slow, flaky).

## Open questions

- Timer interval vs. daemon-watch for health — start with a timer; revisit if
  status lags.
- Should an unknown-kind component (no health adapter) count toward `Ready`, or
  hold the plan `Pending`? PoC: count as ready with a `note`. Flag if that hides
  failures.
