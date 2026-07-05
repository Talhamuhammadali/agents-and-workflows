---
title: WorkloadPlan Operator — Follow-Along Walkthrough
audience: someone new to Kubernetes operators
reading_order: top to bottom, with the code open beside you
implements: docs/designs/spec-01-crd-operator.md
---

# WorkloadPlan Operator — a walkthrough from first principles

This is the "understand everything" companion to the code in `workload_operator/`.
Read it top to bottom with the files open. It assumes you know Python but **not**
Kubernetes internals — every k8s idea is introduced before it's used.

By the end you'll understand: what problem this solves, every file we wrote and
why, how the tests prove it works, and how to run the whole thing yourself.

---

## 1. The one-paragraph summary

We built a **Kubernetes operator**: a background program that watches a
**custom resource** we invented (`WorkloadPlan`) and makes the cluster match what
that resource asks for. A `WorkloadPlan` is a single object that lists a bunch of
workloads ("components"). The operator creates each component, marks it as
**owned** by the plan, watches their health, and reports one overall status. Delete
the plan and everything it created disappears with it. That's the whole idea: **one
object you can create, watch, and delete as a unit.**

---

## 2. Kubernetes vocabulary you need first

Skip this if you know it. Otherwise, these seven terms unlock the rest.

- **Resource / object** — a thing in the cluster (a `Pod`, a `Deployment`, a
  `ConfigMap`). You describe the *desired* state in YAML; Kubernetes works to make
  reality match.
- **Kind** — the type of an object: `Deployment`, `Service`, `Job`, etc.
- **Controller** — a loop that watches objects of some kind and drives reality
  toward their desired state. The `Deployment` controller, for example, makes sure
  the right number of `Pod`s exist.
- **Custom Resource Definition (CRD)** — how you *teach the cluster a new kind*.
  Once you apply a CRD, the API server accepts objects of your new kind and stores
  them, exactly like built-in kinds. Our CRD defines the `WorkloadPlan` kind.
- **Operator** — a controller for a *custom* kind. It's just a program using the
  Kubernetes API. Ours is written with **Kopf** (a Python operator framework).
- **Reconcile** — the operator's core verb: "look at the desired state, look at
  reality, make reality match." Reconciling should be **idempotent** — running it
  twice changes nothing the second time.
- **ownerReference + garbage collection (GC)** — you can mark object B as "owned
  by" object A. When A is deleted, Kubernetes' built-in GC automatically deletes B.
  This is how "delete the plan → children vanish" works, and it's **not** our code —
  it's a core cluster feature we opt into by stamping the reference.

Two more that show up later:

- **Server-Side Apply (SSA)** — a way to create-or-update an object in one call
  that's safe to repeat. This is what makes our reconcile idempotent.
- **Finalizer** — a marker on an object that says "don't fully delete me until the
  controller says it's done cleaning up." Kopf adds one automatically so it can run
  our delete handler before the object disappears.

---

## 3. The mental model: an ownership ledger

The design doc (`docs/designs/spec-01-crd-operator.md`) frames the operator as an
**ownership ledger**, and that framing is the key to *why* this exists.

`kubectl` can already list every object in a cluster. So why invent a
`WorkloadPlan`? Because `kubectl` **cannot tell you that a set of objects belongs
together** — that these five objects were all created by one agent session, should
be healthy together, and should be deleted together. The `WorkloadPlan` is the
durable answer to *"what does this session own, and is it healthy?"*

It's the **root of an ownership tree**. Every object it creates points back to it
via an ownerReference (so delete cascades) and carries **attribution labels** (so
you can query "show me everything this session made").

### The brain / hands split

We split the operator into two layers, and this split is the single most important
engineering decision:

- **The brain** (`core.py`) — pure functions. Dicts and typed objects in, values
  out. No cluster calls. This is where every *decision* lives (is this healthy? what
  phase is the plan in? what should the child object look like?).
- **The hands** (`handlers.py`) — the Kopf handlers. They only do I/O: read the
  resource, call a brain function, apply the result, write status. Each is ~10 lines.

Why split? Because you can unit-test the brain in **milliseconds** with no cluster,
and the hands become so thin there's almost nothing left to break. Any `if` worth
testing lives in the brain.

```
        agent (spec-02)                    operator (this)
        writes spec  ────────► WorkloadPlan ◄──────── owns status
                                    │
                                    │ reconcile (hands call brain)
                                    ▼
                    Deployment   ConfigMap   Job   ...   (owned children)
```

The **seam** between agent and operator is the CR itself: the agent owns `spec`,
the operator owns `status`, neither calls the other's internals.

---

## 4. The two validation gates

A bad plan can be caught in two places. Know which is which:

- **Gate 1 (pydantic, agent-side)** — spec-02. The agent validates before it ever
  talks to the cluster. Not in this spec.
- **Gate 2 (the CRD schema, server-side)** — the API server rejects malformed plans
  at submit time, before the operator sees them. This is in `crd.yaml` and is why
  the operator can trust its input and stay dumb.

We test Gate 2 directly (`tests/operator/test_crd_schema.py`): submit a bad plan,
assert the API server returns `422 Unprocessable Entity`.

---

## 5. File-by-file

Files live in `workload_operator/` (the operator) and `tests/operator/` (its tests).

> Aside on the name: the package is `workload_operator`, **not** `operator`, because
> `operator` is a Python standard-library module — a top-level package named
> `operator` would shadow it and break imports across the ecosystem.

### 5.1 `crd.yaml` — the contract

This teaches the cluster the `WorkloadPlan` kind. The parts that carry weight:

- **`group: poc.local`, `version: v1alpha1`, `kind: WorkloadPlan`** — the identity.
  An object of ours has `apiVersion: poc.local/v1alpha1`.
- **`spec.components[]`** — a list where each item is `{name, manifest}`. The
  `manifest` is a *raw Kubernetes object* (a whole Deployment, ConfigMap, etc.).
- **`x-kubernetes-list-type: map` + `x-kubernetes-list-map-keys: [name]`** — makes
  `name` a unique key. The API server **rejects duplicate component names** for free.
- **`manifest` has `required: [apiVersion, kind]` *and*
  `x-kubernetes-preserve-unknown-fields: true`** — this pairing is the crux. `preserve`
  means "store the manifest verbatim, don't strip fields you don't recognize" (so a
  Deployment keeps its `replicas`, GPU limits, everything). `required` means "but it
  must at least be a real object with a kind." Store anything, but it must be a real
  thing.
- **`subresources: {status: {}}`** — makes `status` a separate write path. The
  operator can update status without bumping the object's `generation`, which
  prevents an infinite reconcile loop (status write → change detected → reconcile →
  status write → ...).
- **`additionalPrinterColumns`** — what `kubectl get wp` shows (Phase, Children, Age).

### 5.2 `constants.py` — one source of identity

`group`, `version`, `kind`, `plural`, and the four label keys, defined once. Kopf
does **not** read these from the CRD — you *tell* Kopf what to watch — so if they
weren't centralized they'd drift across the handler decorators, the ownerReferences,
and the labels. Everything imports them from here.

### 5.3 `models.py` — the CRD as typed Python

Pydantic models mirroring the CRD, so the operator works with `plan.components`
instead of `body["spec"]["components"]` and typos become type errors. Highlights:

- `Manifest` uses `model_config = ConfigDict(extra="allow")` — the Python mirror of
  `preserve-unknown-fields`: keep every field, only pin `apiVersion`/`kind`.
- `ChildStatus` carries `ready`, `failed`, and `note`. `note` is the short *reason*
  (for example `2/2 replicas ready` or a failure cause) — this is what lets the
  polling agent explain *why* a child failed, per child, with no extra channel.
- Every field uses `Field(description=...)` so the model doubles as documentation.
- `OwnerMeta` is not a CRD section — it's assembled from the plan's metadata and
  handed to `build_child` to stamp onto children.

### 5.4 `core.py` — the brain (read this closely)

Four pure functions. This is where the logic you'd want to test lives.

**`compute_phase(children) -> "Pending" | "Ready" | "Failed"`**
The order of checks *is* the spec:
```
Failed  if any child failed
Ready   if there is at least one child AND all are ready
Pending otherwise (including the empty list)
```
The subtle bug it avoids: `all([])` is `True` in Python, so a naive
`all(c.ready ...)` would call an empty plan "Ready". The explicit `children and ...`
guard is why the empty case is `Pending`.

**`is_ready(kind, obj) -> Health`** and `HEALTH_ADAPTERS`
`Health` is a 3-value result `(ready, failed, note)`. Two booleans, not one, because
a workload has *three* states: healthy, still-converging, and terminally-failed. A
single `ready` bool couldn't tell "not yet" apart from "failed", and `compute_phase`
needs that distinction.

`HEALTH_ADAPTERS` is a `dict[kind -> function]`. This is the **evolution seam**:
supporting a new kind (even a third-party custom resource) is *one dict entry*, never
a schema change. The seeded adapters:
- `Deployment` → ready when `readyReplicas >= spec.replicas`.
- `Job` → ready when `succeeded >= 1`; **failed** when `failed > backoffLimit`.
- `Pod` → ready when `Running` and all containers ready; failed on phase `Failed`.
- `Service`/`ConfigMap`/`Secret` → ready as soon as they exist.
- unknown kind → ready with a note, so it doesn't block the plan.

**`build_child(component, owner) -> dict`**
The ledger mechanism. Takes a component + the owning plan's identity, returns the
manifest to apply, having stamped:
- an `ownerReference` back to the plan (`controller: true` → cascade GC),
- the attribution labels (`poc.local/plan`, `poc.local/component`, and session/owner
  when present),
- the namespace.
It deep-copies (`model_dump()`) so it never mutates the input.

**`plan_status_digest(children) -> dict`**
Builds the status patch: `phase`, `readyCount`, the per-child `children[]`, and — when
the phase is `Failed` — a `NeedsAttention` condition naming the failed children. That
condition is the **escalation channel** the agent polls (status-as-queue, no message
bus needed for the PoC). "Digest" is deliberate: short reasons only, never log dumps
(status has a size ceiling and high-churn writes cause watch storms).

### 5.5 `k8s.py` — the hands' tools (I/O)

Three tiny functions isolating every cluster call: `dynamic_client()` (build a client
that can act on *any* kind), `apply_manifest()` (server-side apply — the idempotent
create-or-update), and `get_object()` (read one object, or `None`). Isolating I/O here
is what lets a future fast test swap in a fake client.

### 5.6 `handlers.py` — the hands (the Kopf handlers)

Each handler: parse → call brain → do I/O. That's it.

- **`reconcile`** (decorated with `@kopf.on.create`, `@kopf.on.update`,
  `@kopf.on.resume`) — for each component, `build_child` then `apply_manifest`; seed
  `status`. All three triggers share it because SSA makes it safe to repeat.
  `on.resume` fires for existing plans when the operator boots, which re-adopts them
  after a restart (no orphans).
- **`on_delete`** — does nothing but log. The ownerReferences + GC delete the
  children; hand-rolling cleanup would be a bug.
- **`health_sweep`** (a `@kopf.timer`, every 15s) — for each component: read the live
  object, run `is_ready`, and if it's *missing*, re-apply it (**self-heal**). Then
  `plan_status_digest` → patch status.

> **Why synchronous handlers?** The design sketch assumed `async`, but the
> `kubernetes` client is synchronous. An `async` handler making blocking calls would
> freeze Kopf's event loop. Sync handlers let Kopf run them in a thread pool. This is
> a deliberate, correct deviation from the sketch.

> **A cold-start race you'll see in the logs:** on the very first tick the timer can
> fire before `reconcile` finishes, find a child missing, and log `note: "recreated"`.
> It's harmless (both paths apply idempotently), but the note is misleading on the
> first sweep — a candidate for a small "skip heal until first reconcile" guard later.

---

## 6. The testing pyramid

Three layers, fastest first. This mirrors the operator's own brain/hands split.

| Layer | File | Cluster? | Speed | What it proves |
|---|---|---|---|---|
| **Unit** | `test_core.py`, `test_health.py`, `test_build.py` | no | ~0.1s | the brain's logic |
| **Schema (Gate 2)** | `test_crd_schema.py` | API server | ~seconds | the CRD accepts/rejects correctly |
| **Reconcile** | `test_reconcile.py` | yes (KopfRunner) | ~35s | milestones 2–6 end to end |

Key techniques:
- Integration tests are marked `@pytest.mark.integration` and **guarded on the
  minikube context** (`conftest.py`): on any other cluster they *skip*, so you can't
  accidentally hit remote infra.
- They **never `sleep` a fixed time**. `wait_until(predicate, timeout)` polls, because
  cluster state is *eventual* ("the deployment appears eventually").
- `KopfRunner` runs the real operator in-process for the duration of a `with` block —
  the idiomatic way to test a Kopf operator.
- **Per-test isolation via a throwaway namespace.** The `namespace` fixture creates a
  unique `wp-test-<id>` namespace for each test and deletes it at teardown. Unique
  names mean tests can never see each other's objects — no shared state, no ordering
  dependence, and `default` is never touched. Teardown strips any plan finalizers
  first, so the namespace can't wedge in `Terminating` after the in-test operator
  stops; deleting the namespace then removes every child in one shot, even if the
  test failed midway. Runs are deterministic (verified by repeated back-to-back runs).

### Running the tests

```bash
uv run pytest tests/operator -m "not integration"   # fast loop, no cluster (~0.1s)
uv run pytest tests/operator -m integration          # cluster tests (needs minikube)
uv run pytest tests/operator                         # everything
```

---

## 7. RBAC — least privilege for the operator

When the operator runs *inside* the cluster it authenticates as a **ServiceAccount**,
and RBAC decides what that account may do. `workload_operator/rbac.yaml` grants:

- A **ClusterRole** (cluster-scoped needs): watch `customresourcedefinitions` and
  `namespaces`, create `events`. Kopf needs these to function.
- A **Role** (namespaced): full control of `workloadplans` + `workloadplans/status`,
  and manage the child kinds it creates (`deployments`, `services`, `configmaps`,
  `secrets`, `jobs`, `pods`).
- A ServiceAccount and the two bindings tying it to those roles.

You can verify a permission without deploying anything:
```bash
kubectl auth can-i create deployments \
  --as=system:serviceaccount:default:workload-operator -n default   # -> yes
```

> **The tension worth knowing:** "adopt any manifest" fights least-privilege — the
> operator can only manage kinds its Role names. The PoC grants a fixed set. A
> production version would narrow per kind and reject components whose kind isn't
> grantable.

---

## 8. Run the whole thing yourself

Local runs use *your* kubeconfig (admin on minikube), so RBAC is optional for this.

```bash
# 0. cluster up, and CONFIRM you're on minikube (never a remote cluster)
minikube start
kubectl config current-context          # must print: minikube

# 1. teach the cluster our kind
kubectl apply -f workload_operator/crd.yaml

# 2. (optional) install the operator's identity + permissions
kubectl apply -f workload_operator/rbac.yaml

# 3. run the operator (foreground; watches the 'default' namespace)
uv run kopf run -m workload_operator.handlers --namespace default --verbose

# 4. in another terminal: create a plan and watch it converge
kubectl apply -f tests/operator/fixtures/wp-good.yaml
kubectl get wp test-good -w                                   # Phase: Pending -> Ready
kubectl get deploy,cm -l poc.local/plan=test-good             # the owned children

# 5. delete the ONE object; children cascade away
kubectl delete wp test-good
kubectl get deploy,cm -l poc.local/plan=test-good             # gone
```

There's also `tests/operator/check-gate2.sh` — a guarded script that applies the good
plan and two bad ones to show the API server accepting/rejecting them.

### Running it *inside* the cluster (as the ServiceAccount)

Instead of `kopf run` on your laptop, you can run the operator as a real in-cluster
Deployment using its own RBAC:

```bash
kubectl apply -f workload_operator/rbac.yaml         # ServiceAccount + roles
minikube image build -t workload-operator:latest .   # build image into minikube
kubectl apply -f workload_operator/deploy.yaml        # run it as the ServiceAccount
kubectl rollout status deploy/workload-operator
kubectl logs -l app=workload-operator -f              # watch it reconcile
```

Then apply a plan as above. Note: don't run the in-cluster operator *and* the
`KopfRunner` integration tests against the same namespace at once — two operators
would both reconcile the same plans. Use one or the other.

---

## 9. Milestones → where they're proven

| # | Milestone | Proven by |
|---|---|---|
| 1 | CRD applies and rejects bad specs | `test_crd_schema.py`, `check-gate2.sh` |
| 2 | Reconcile applies children (owner-refs + labels) | `test_reconcile_creates_children_...` |
| 3 | Health timer flips phase to Ready | `test_health_sweep_flips_phase_to_ready` |
| 4 | Cascade cleanup via single delete | `test_cascade_delete_removes_children` |
| 5 | Resume re-adopts after restart | `test_resume_adopts_a_preexisting_plan` |
| 6 | Self-heal recreates a deleted child | `test_self_heal_recreates_a_deleted_child` |

---

## 10. Glossary (quick reference)

- **CRD** — defines a new kind so the cluster accepts your objects.
- **Operator** — a program that reconciles a custom kind (ours uses Kopf).
- **Reconcile** — make reality match the desired spec; must be idempotent.
- **ownerReference** — "B is owned by A"; deleting A cascade-deletes B via GC.
- **Server-Side Apply** — repeatable create-or-update in one call.
- **Finalizer** — "don't fully delete until cleanup runs"; Kopf manages ours.
- **Subresource (status)** — separate write path for status; avoids reconcile loops.
- **Health adapter** — per-kind function deciding if a child is ready/failed.
- **Attribution labels** — `poc.local/...` labels making the ledger queryable.

---

## 10.5 Post-review hardening (what a review caught and we fixed)

A review after the first build found three gaps. All are now fixed and tested:

- **Pruning removed components.** If you edit a plan to drop a component, its child
  is now deleted. The operator records what it applied (`apiVersion` + `objectName`
  in `status.children`) and deletes anything recorded that's no longer in `spec`.
  It's *kind-agnostic* — works for a removed inference CRD as much as a removed
  `Deployment`, with no hardcoded kind list.
- **Runs in-cluster.** `Dockerfile` + `workload_operator/deploy.yaml` run it as the
  `workload-operator` ServiceAccount — the RBAC is now actually exercised, not just
  validated on paper.
- **`metadata.name` required.** A nameless component is now rejected by the CRD at
  submit time, instead of failing later at apply.

**One limitation that remains** (worth knowing): the `Deployment` health check means
"replicas ready," which for a model server (vLLM, etc.) happens *before* the model
finishes loading — so it can report `Ready` a bit early. A real fix is a per-kind
health adapter that checks the serving endpoint. Deferred until a real inference
workload is wired in.

## 11. What's next

The operator (this spec) is the "hands" of the larger system. **Spec-02** builds the
**agent** — the "brain" that reads a source (AWS/EKS), decides what to migrate or
provision, and *authors a `WorkloadPlan`*. Everything here was built so that the
agent's job reduces to: write a spec, poll the status, report. The seam is proven;
the agent plugs into it.
