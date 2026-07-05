---
status: scenario design / demo spec
persona: B (ML Engineer — provision + benchmark)
intent: provision
validates: [diagnostic re-planning, escalate-vs-autofix boundary, goal-seeking]
depends_on: [spec-02-agent]
workload: vLLM serving Llama 3 8B on a single 24GB GPU + batch benchmark
---

# Demo — ML provisioning as a diagnostic staircase

Persona B's current sketch is "deploy vLLM, run a benchmark, report the number."
That works but it undersells the agent — a `kubectl apply` plus a `kubectl logs`
does the same. This doc reshapes it into a demo that proves the *one thing only
an agent can do here*.

## Why this demo exists (read this first)

Your operator design has a hard rule: **never call the LLM from inside the
reconcile loop** (`agent-operator-design.md`). The operator only ever knows
`ready | converging | failed`. So every decision that requires *reading an error
and changing the desired state in response* can only live agent-side.

That is exactly what getting a model onto a GPU is: a loop of
**observe failure → diagnose → change a knob → re-declare**. An ML engineer
spends the afternoon on this. A dumb operator structurally cannot do it. **So
this demo is the one that justifies having an agent at all.** The migration demo
justifies discovery+mapping; this one justifies diagnostic re-planning.

> Design the demo around the *loop*, not the happy path. "Enable GPU, then run"
> is one rung. The worth is the whole staircase.

---

## The diagnostic staircase

Each rung is a **distinct failure class** with a **distinct signal** in a
**distinct place** and a **distinct resolution class**. That variety is the
demo — it exercises every observability tool the agent has (`describe` for
events, `logs(previous=True)` for crashloops, idempotent `declare_plan` re-apply,
`check_escalations`/`Ask` for the human boundary).

| # | Injected failure | Signal (and where) | Resolution class | Agent tool exercised |
|---|---|---|---|---|
| 1 | GPU not advertised on the node | pod `Pending`; **events**: `FailedScheduling — 0/1 nodes … Insufficient nvidia.com/gpu` | **precondition fix** — enable addon + device plugin, *verify capacity before declaring* | `describe(node)`, `get_plan_status` |
| 2 | Gated model weights | pod `CrashLoop`; **logs**: `401 … gated repo, accept the license` | **escalate** — needs an `HF_TOKEN` it doesn't have → human → re-declare with a Secret | `logs(previous=True)`, `check_escalations`/`Ask` |
| 3 | KV-cache OOM (context too long for 24GB) | pod `CrashLoop`; **logs**: `torch.OutOfMemoryError: CUDA out of memory` | **re-plan** — lower `max-model-len` / `gpu-memory-utilization`, or quantize | `logs(previous=True)`, `declare_plan` (update) |
| 4 | Benchmark misses target | Job `Ready` but tok/s < target in **bench pod logs** | **optimization re-plan** — tune knobs, or report *infeasible-with-evidence* | `logs(bench pod)`, `declare_plan` |

Note the resolution classes are all different: **environment fix**, **escalate to
human**, **autonomous re-plan**, **optimize-or-declare-infeasible**. That spread
is the point — it shows the agent correctly *routing* each failure, which is the
judgment a controller can't have.

### Rung 1 — GPU not advertised (the precondition-check lesson)

The subtle teaching point: `minikube start --gpus` (or the addon) is **not
enough**. Capacity `nvidia.com/gpu` is only advertised once the **NVIDIA device
plugin DaemonSet** is running and the kubelet reports it. If the agent declares
the vLLM plan before that, the pod sits `Pending` forever with `FailedScheduling`.

The mature behavior is **check the environment can satisfy the request before
declaring it** — `describe(node)` and confirm `status.allocatable["nvidia.com/gpu"]
>= 1`. This is the provisioning mirror of the migration demo's discovery: look
before you leap.

### Rung 2 — gated weights (the escalate boundary)

Llama is a gated HF repo. First pull → `401`. The agent **does not have** a token
and **cannot invent one** — this is the textbook *ambiguous* case from your
orphan taxonomy that must **escalate**, not auto-fix. Flow: detect in logs →
raise `NeedsAttention` / `Ask` → human supplies `HF_TOKEN` → agent adds a Secret
component + `env` ref → re-declare. Clean human-in-the-loop, and it **reuses the
secrets machinery from the migration demo** — nice symmetry across personas.

### Rung 3 — KV-cache OOM (the autonomous re-plan)

Ask for something that does *not* trivially fit: Llama 3 8B fp16 at
`--max-model-len 32768`. Weights are ~16GB; a 32k KV cache blows past the
remaining ~8GB → CUDA OOM at startup. The agent reads the crashloop log
(`logs(previous=True)` — the live container is empty), recognizes OOM, and
**re-plans**: drop `max-model-len` to 4096, or lower `gpu-memory-utilization`, or
switch to an AWQ/fp8 quant. Then re-`declare_plan` (idempotent update) and watch
it converge. This is the core ML-eng loop, fully autonomous.

### Rung 4 — goal-seeking, not fire-and-report

Don't ask "run a benchmark and tell me the number." Ask for a **target with a
stopping condition**:

> Get me **≥ 2500 tok/s at p95 < 700ms**, or tell me it's not achievable on this
> GPU and why.

Now the benchmark result *feeds a decision*. Miss → try one more config (raise
`gpu-memory-utilization`, enable prefix caching, bump concurrency, try fp8). Hit
→ stop and report. The demo has a plot and a definite end.

---

## Redefine "done" (the framing that makes it worthwhile)

> **Done is not "it works." Done is "target met, OR infeasibility explained with
> evidence from logs."**

An agent that correctly concludes *"Llama 3 8B fp16 at 32k context will not fit a
24GB GPU — here is the OOM, and here is the config that would fit"* is **more**
impressive than one that got lucky on the first try. Bake a deliberately
infeasible variant into the demo so you can show the agent *declining
intelligently* rather than thrashing forever. That requires a **re-plan budget**
(see thinking problems) so it gives up with a reason instead of looping.

---

## Scope tiers (pick your depth — don't build all of it at once)

**Minimum worthwhile** (proves the thesis on its own):
- Rung 1 (GPU precondition) + Rung 3 (OOM re-plan) + Rung 4 (goal-seeking).
- This is already a real diagnostic loop: fix env → fit model → hit target.

**Add for the human-in-loop story:**
- Rung 2 (gated weights → escalate). High value, reuses secrets machinery.

**Optional depth (only if time):**
- **Weight-cache PVC** — 16GB re-downloaded every pod restart is painful; a
  `standard`/hostPath PVC as the HF cache. Ties to the mapping-table PVC row and
  adds a stateful component.
- **fp8/AWQ path** — a second, quantized re-plan branch when fp16 can't hit the
  target. Shows the agent reaching for a qualitatively different fix.

---

## Open thinking problems (for you, before you build)

1. **When to escalate vs re-plan?** OOM = re-plan (mechanical, agent can fix).
   Gated repo = escalate (needs a human secret). What's the *general rule* that
   tells them apart? (Hint: can the fix be derived from cluster state alone, or
   does it need information the agent structurally cannot have?)
2. **The re-plan budget.** Without a cap, a goal-seeking agent loops forever on
   an infeasible target. What bounds it — N attempts? diminishing returns on
   tok/s? a hard "declare infeasible after K" rule? This is what turns "thrash"
   into "intelligent decline."
3. **Reading structured signal from unstructured logs.** OOM, `401`, and the
   tok/s number all come from **pod logs**, which are free text. How reliable is
   LLM extraction here, and where would you want the *benchmark* to emit
   structured output instead (JSON line) to make Rung 4 deterministic?
4. **Is a re-plan a new CR or an update to the same one?** `declare_plan` is
   idempotent — re-applying updates in place. But does the *history* of failed
   attempts matter for the demo narrative? Where does it live if `status` only
   holds the current digest?
5. **Precondition check as a tool.** Rung 1 wants "does the node advertise a
   GPU?" *before* declaring. Is that a new capability, or does `describe(node)`
   already give it? Where does "check the environment" belong in the tool set —
   is it discovery (like Persona A) generalized?
6. **How does the operator report a `Pending` pod?** Rung 1's pod is `Pending`,
   not `Failed`. Your `Health(ready, failed, note)` is 3-valued — does `Pending`
   read as "converging" forever, and how long before the agent decides
   converging-too-long *is* a problem? (This is a real gap worth pinning down.)

---

## Build checklist (your delivery — your todo, not mine)

Environment:
- [ ] minikube with a real 24GB GPU passthrough (or a stub that fakes `nvidia.com/gpu` capacity + a container that emulates the failure signals, if no GPU box).
- [ ] Start *without* the device plugin so Rung 1 fires; script the enable step.

Workloads (plan components the agent authors):
- [ ] vLLM `Deployment` (Llama 3 8B), knobs as args: `--max-model-len`, `--dtype`, `--gpu-memory-utilization`.
- [ ] Benchmark `Job` that drives it and emits **structured** results (tok/s, ttft, p95) as a final JSON log line.
- [ ] `HF_TOKEN` Secret path (Rung 2) — reuse the migration demo's secrets machinery.
- [ ] (optional) weight-cache PVC.

Failure injection (so each rung actually fires):
- [ ] Rung 1: device plugin absent at start.
- [ ] Rung 2: use the real gated repo (or stub a `401`).
- [ ] Rung 3: first plan asks for `--max-model-len 32768` (guaranteed OOM on 24GB).
- [ ] Rung 4: set a target that the first *feasible* config misses, so one tune-and-retry is needed.

Test harness:
- [ ] Assert the agent's *resolution class* per rung (fixed env / escalated / re-planned / optimized) — not just "ended green."
- [ ] Assert the infeasible variant ends in "declined with evidence," not a timeout.
