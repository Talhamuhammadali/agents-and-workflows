---
status: mock / PoC-level
mock_data: true
cr_kind: WorkloadPlan
intents_covered: [migrate, provision]
note: >
  Two thin personas for the agent-operator PoC. Both drive ONE custom
  resource (WorkloadPlan) whose spec is a flat list of raw manifests
  (spec.components[]) plus an optional spec.intent tag. The operator adopts
  each manifest (owner-ref'd child), watches its health, and writes status;
  the agent reads status. "Done" = phase Ready. See agent-operator-design.md
  for the operator internals and spec-01-crd-operator.md for the shipped CRD.
---

# Agent-Operator PoC — Personas

Both personas share the same shape:

```
intent capture  →  agent authors ONE WorkloadPlan CR  →  Gate 1 (pydantic)
                →  operator reconciles → owner-ref'd children
                →  agent polls status.phase / conditions  →  report when Ready
```

The CR is the single point of entry, watch, and cleanup: delete the CR →
cascade-GC removes every child. The operator owns `status`; the agent owns
`spec`. There is no discriminated `spec.migrate`/`spec.provision` body — both
intents produce the **same** flat `spec.components[]`, each entry a real
Kubernetes manifest the operator applies verbatim. `spec.intent` is a plain tag
(`migrate` | `provision`) the agent sets so its own reporting reads right; the
operator treats every component identically regardless of intent.

## Status contract (as shipped in spec-01)

```
status.phase:  Pending | Ready | Failed        # Failed if any child failed;
                                                # Ready if all children ready
status.readyCount: <int>                        # how many children are ready
status.observedGeneration: <int>
status.children[]:
  - name:        <component name>
    kind:        Deployment | Service | ConfigMap | Job | ...
    apiVersion:  apps/v1 | v1 | batch/v1 | ...
    objectName:  <metadata.name of the child>
    ready:       true | false
    failed:      true | false
    note:        "<why, e.g. 'failed > backoffLimit' or 'recreated'>"
status.conditions[]:
  - type: NeedsAttention                        # present ONLY when phase=Failed;
    status: "True"                              # this is the agent's escalation
    message: "<names the failed children>"
```

There is no `AllHealthy` condition and no `resultDigest` — Ready is expressed by
`phase`, and a benchmark's metrics are read by the agent from the Job's **pod
logs**, not from status (status is a digest/pointer, never a raw result blob).

---

## Persona A — Platform Engineer, migrate an app off AWS

**Workload:** move a small web app (Deployment + Service + Ingress + ConfigMap)
from EKS to local minikube. `intent: migrate`.

### Turn 1 — Intent capture

**Engineer:**
> I have a web app running on our EKS cluster — a deployment behind an ALB
> ingress with a config map and a ClusterIP service. I want to stand up an
> equivalent on my local minikube to develop against. Read what's there and
> mirror it locally.

**Agent:**
> I'll read the source read-only, write an inventory, then declare a single
> migration plan. Heads-up on one lossy mapping already: an AWS ALB Ingress has
> no minikube equivalent — I'll map it to an nginx Ingress and record that as an
> accepted loss. Nothing on AWS will be modified.

### Turn 2 — Discover source (read-only)

**Tool call:** `discover_source(namespace="web")` against the SOURCE role (EKS).

Writes `inventory.md` to the workspace:

```
web/Deployment/web-api        image=web-api:1.4  replicas=3
web/Service/web-api           type=ClusterIP     port=8080
web/ConfigMap/web-api-config  keys=[APP_ENV, LOG_LEVEL]
web/Ingress/web-api           class=alb          host=api.example.com
```

### Turn 3 — Declare the migration (single CR)

**Tool call:** `declare_plan(name="migrate-web-app", intent="migrate", components=[...])`
→ Gate 1 (pydantic `PlanModel`) validates → translates to the CR → server-side
applies one object. The lossy mapping travels as an annotation on the component
so the loss is declared **in the CR**, not just in chat.

```yaml
kind: WorkloadPlan
metadata: { name: migrate-web-app }
spec:
  intent: migrate
  components:
    - name: web-api
      manifest:
        apiVersion: apps/v1
        kind: Deployment
        metadata:
          name: web-api
          annotations: { poc.local/source-ref: "web/Deployment/web-api" }
        spec: { replicas: 3, template: { spec: { containers: [{ name: web-api, image: web-api:1.4 }] } } }
    - name: web-api-svc
      manifest:
        apiVersion: v1
        kind: Service
        metadata: { name: web-api }
        spec: { type: ClusterIP, ports: [{ port: 8080 }] }
    - name: web-api-config
      manifest:
        apiVersion: v1
        kind: ConfigMap
        metadata: { name: web-api-config }
        data: { APP_ENV: dev, LOG_LEVEL: info }
    - name: web-api-ingress
      manifest:
        apiVersion: networking.k8s.io/v1
        kind: Ingress
        metadata:
          name: web-api
          annotations:
            poc.local/source-ref: "web/Ingress/web-api"
            poc.local/accepted-losses: "ALB → nginx: no WAF, no AWS cert; host preserved"
        spec: { ingressClassName: nginx, rules: [{ host: api.example.com }] }
```

### Turn 4 — Converge + report

```
status.phase: Pending → Ready
status.readyCount: 4
status.children:
  - { name: web-api,         kind: Deployment, objectName: web-api,        ready: true }
  - { name: web-api-svc,     kind: Service,    objectName: web-api,        ready: true }
  - { name: web-api-config,  kind: ConfigMap,  objectName: web-api-config, ready: true }
  - { name: web-api-ingress, kind: Ingress,    objectName: web-api,        ready: true }
```

**Agent:**
> Migration complete. All 4 components healthy on minikube (phase Ready). One
> accepted loss: the ALB became an nginx Ingress (host preserved, WAF/cert
> dropped — those were AWS-managed). Tear down anytime with
> `kubectl delete workloadplan migrate-web-app`.

---

## Persona B — ML Engineer, local vLLM batch-inference benchmark

**Workload:** deploy vLLM on minikube with a local 24GB GPU, serve Llama 3 8B
(fp16, fits in 24GB), run a fixed batch of prompts, report throughput/latency.
`intent: provision`.

### Turn 1 — Intent capture

**Engineer:**
> On my minikube box I have one 24GB GPU. Deploy Llama 3 8B in fp16 with vLLM
> and run a batch inference benchmark — a couple thousand prompts — so I can see
> tokens/sec and p95 latency before I commit to a config.

**Agent:**
> Llama 3 8B in fp16 is ~16GB of weights, leaving ~8GB for KV cache on your
> 24GB GPU — fine for a modest batch. I'll declare one plan: a vLLM server
> Deployment plus a benchmark Job that drives it, both on minikube using the
> GPU. The Job runs to completion; when the plan reports Ready I'll read the
> Job's pod logs for the metrics, then you decide whether to keep it.

### Turn 2 — Declare the provision plan (single CR)

**Tool call:** `declare_plan(name="vllm-bench", intent="provision", components=[...])`
→ Gate 1 validates → submits one CR. The two workloads are just two entries in
the same `spec.components[]` — the server (a long-running Deployment) and the
benchmark (a run-to-completion Job).

```yaml
kind: WorkloadPlan
metadata: { name: vllm-bench }
spec:
  intent: provision
  components:
    - name: vllm-server
      manifest:
        apiVersion: apps/v1
        kind: Deployment
        metadata: { name: vllm-server }
        spec:
          replicas: 1
          template:
            spec:
              containers:
                - name: vllm
                  image: vllm/vllm-openai:latest
                  args: ["--model", "meta-llama/Meta-Llama-3-8B", "--dtype", "float16",
                         "--max-model-len", "4096", "--gpu-memory-utilization", "0.9"]
                  resources: { limits: { "nvidia.com/gpu": 1 } }
    - name: vllm-bench
      manifest:
        apiVersion: batch/v1
        kind: Job
        metadata: { name: vllm-bench }
        spec:
          backoffLimit: 0
          template:
            spec:
              restartPolicy: Never
              containers:
                - name: bench
                  image: vllm-bench:local
                  args: ["--target", "http://vllm-server:8000", "--prompts", "2000", "--concurrency", "32"]
```

### Turn 3 — Provision + run + report

```
status.phase: Pending → Ready          # Ready once the Job succeeds (succeeded >= 1)
status.readyCount: 2
status.children:
  - { name: vllm-server, kind: Deployment, objectName: vllm-server, ready: true }
  - { name: vllm-bench,  kind: Job,        objectName: vllm-bench,  ready: true }
```

Then the agent reads the benchmark output from the Job's pod:

**Tool call:** `logs(role="target", pod="<vllm-bench pod>")` →
`tokens_per_sec=3120  ttft_ms=210  p95_latency_ms=640  prompts=2000/2000`

**Agent:**
> Benchmark complete (phase Ready — the Job succeeded): 3,120 tok/s aggregate,
> TTFT 210 ms, p95 640 ms over 2,000 prompts at concurrency 32 (read from the
> Job's pod logs). The vLLM server Deployment is still up. Keep it for more
> runs, or `kubectl delete workloadplan vllm-bench` to release the GPU.

If the Job had exceeded its `backoffLimit`, the plan would instead be
`phase: Failed` with a `NeedsAttention` condition naming `vllm-bench` — the
signal the agent polls for to know a run needs a human.

---

## What the two personas share (the point of one CR)

| | Persona A (migrate) | Persona B (provision) |
|---|---|---|
| Desired state from | reading EKS | engineer intent |
| CR body | `spec.components[]` (flat manifests) | `spec.components[]` (flat manifests) |
| `spec.intent` tag | `migrate` | `provision` |
| "Done" | phase `Ready` (all children ready) | phase `Ready` (benchmark Job succeeded) |
| Metrics readout | n/a | agent reads Job pod **logs** (not status) |
| Cleanup | delete CR → cascade GC | delete CR → cascade GC |

Same envelope, same operator, same watch/cleanup story. The only real
difference is where the components come from (discovery vs intent) and how the
agent reports — the CR shape and the operator are identical.
