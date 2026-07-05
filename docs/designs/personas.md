---
status: mock / PoC-level
mock_data: true
cr_kind: WorkloadPlan
intents_covered: [migrate, provision]
note: >
  Two thin personas for the agent-operator PoC. Both drive ONE custom
  resource (WorkloadPlan) with a discriminated `spec.intent`. The operator
  materializes children (owner-ref'd), the agent reads status. "Done" = all
  children healthy / the run completes. See agent-operator-design.md for the
  operator internals.
---

# Agent-Operator PoC — Personas

Both personas share the same shape:

```
intent capture  →  agent authors ONE WorkloadPlan CR  →  Gate 1 (pydantic)
                →  operator reconciles → owner-ref'd children
                →  agent polls status.phase / conditions  →  report when healthy
```

The CR is the single point of entry, watch, and cleanup: delete the CR →
cascade-GC removes every child. The operator owns `status.phase`; the agent
owns `spec`.

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

**Tool call:** `discover_source(context="eks-prod", namespace="web")`

Writes `inventory.md` to the workspace:

```
web/Deployment/web-api        image=web-api:1.4  replicas=3
web/Service/web-api           type=ClusterIP     port=8080
web/ConfigMap/web-api-config  keys=[APP_ENV, LOG_LEVEL]
web/Ingress/web-api           class=alb          host=api.example.com
```

### Turn 3 — Declare the migration (single CR)

**Tool call:** `declare_migration(spec=...)` → Gate 1 validates → submits one CR.

```yaml
kind: WorkloadPlan
metadata: { name: migrate-web-app }
spec:
  intent: migrate
  target:  { provider: minikube, context: minikube }
  approval: { required: false }          # dev, non-destructive
  migrate:
    source: { provider: aws, context: eks-prod, namespace: web }
    components:
      - sourceRef: web/Deployment/web-api
        mode: native
        chosen: Deployment (replicas 3, image web-api:1.4)
      - sourceRef: web/Service/web-api
        mode: native
        chosen: Service ClusterIP:8080
      - sourceRef: web/ConfigMap/web-api-config
        mode: native
        chosen: ConfigMap (2 keys)
      - sourceRef: web/Ingress/web-api
        mode: native
        chosen: nginx Ingress
        acceptedLosses: ["ALB → nginx: no WAF, no AWS cert; host preserved"]
```

### Turn 4 — Converge + report

```
status.phase: PROVISIONING → VALIDATING → READY
status.conditions: [{ type: AllHealthy, status: "True" }]
status.children:
  web-api (Deployment)  ready 3/3
  web-api (Service)     ready
  web-api-config        ready
  web-api (Ingress)     ready  (nginx)
```

**Agent:**
> Migration complete. All 4 components healthy on minikube. One accepted loss:
> the ALB became an nginx Ingress (host preserved, WAF/cert dropped — those were
> AWS-managed). Tear down anytime with `kubectl delete workloadplan migrate-web-app`.

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
> 24GB GPU — fine for a modest batch. I'll declare one plan: a vLLM server plus
> a benchmark Job that drives it, both on minikube using the GPU. It runs to
> completion, reports metrics, then you decide whether to keep it.

### Turn 2 — Declare the provision plan (single CR)

**Tool call:** `declare_provision(spec=...)` → Gate 1 validates → submits one CR.

```yaml
kind: WorkloadPlan
metadata: { name: vllm-bench }
spec:
  intent: provision
  target:  { provider: minikube, context: minikube }
  approval: { required: false }          # local, no spend
  provision:
    topology:
      gpuCount: 1
      gpuMemoryGB: 24
    workload:
      type: vllm-inference
      baseModel: llama-3-8b
      precision: fp16
      serve: { engineArgs: { "--max-model-len": 4096, "--gpu-memory-utilization": 0.9 } }
    jobs:
      benchmark:
        type: batch-inference
        prompts: 2000
        concurrency: 32
        metrics: [tokens_per_sec, ttft_ms, p95_latency_ms]
```

### Turn 3 — Provision + run + report

```
status.phase: PROVISIONING → VALIDATING → READY → RUNNING → DONE
status.children:
  vllm-server (Deployment)  ready 1/1   gpu=1
  vllm-bench  (Job)         completed
status.conditions: [{ type: AllHealthy, status: "True" }]
status.resultDigest:
  tokens_per_sec: 3120
  ttft_ms: 210
  p95_latency_ms: 640
  prompts: 2000/2000
```

**Agent:**
> Benchmark complete: 3,120 tok/s aggregate, TTFT 210 ms, p95 640 ms over 2,000
> prompts at concurrency 32. The vLLM server is still up (phase RUNNING → idle).
> Keep it for more runs, or `kubectl delete workloadplan vllm-bench` to release
> the GPU.

---

## What the two personas share (the point of one CR)

| | Persona A (migrate) | Persona B (provision) |
|---|---|---|
| Desired state from | reading EKS | engineer intent |
| CR body | `spec.migrate.components[]` | `spec.provision.{topology,workload,jobs}` |
| Lifecycle used | `…→ READY` (steady) | `…→ RUNNING → DONE` (run-to-completion) |
| "Done" | all children healthy | benchmark Job completed + healthy |
| Cleanup | delete CR → cascade GC | delete CR → cascade GC |

Same envelope, same operator, same watch/cleanup story — only the `spec.<intent>`
body and the lifecycle tail differ.
