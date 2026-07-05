---
status: scenario design / demo spec
persona: A (Platform Engineer — migrate off AWS)
intent: migrate
validates: [secret migration, ALB→nginx settings fidelity, discovery completeness]
depends_on: [spec-02-agent]
target_secret_store: HashiCorp Vault (dev mode) via External Secrets Operator
---

# Demo — Migrate a secrets-viewer app off AWS (secrets + ALB)

A concrete workload for Persona A. The point of the demo is **not** that an app
runs on minikube — anyone can `kubectl apply`. The point is to prove the two
things only an agent can do:

1. **Discovery** — chase the full dependency closure of an app from a seed, not
   a flat object list.
2. **Honest mapping** — translate every AWS-ism to a local equivalent, and
   account for the ones that can't be, with nothing silently dropped.

The app is deliberately trivial (a viewer with two endpoints) so all the
attention is on the migration, not the app.

## Thesis (what a green demo actually proves)

> A correct migration is one where **every discovered thing is accounted for** —
> mapped, relocated, degraded, or explicitly declared lost — and the migrated
> app produces the **same observable output** as the source. "Same output" is
> the `/secrets` parity check; "accounted for" is the migration report.

Read that twice: "properly migrated" is *not* "behaves identically to AWS." A
WAF rule has no local equivalent — dropping it is correct, **as long as the drop
is declared.** The demo is built to make the honest path the only passing path.

---

## The source app (what you build on EKS)

A tiny FastAPI/Flask service, `secrets-viewer`, in namespace `web`:

| Endpoint | Returns | Used for |
|---|---|---|
| `GET /healthz` | `200 {"ok": true}` | liveness/readiness probe + ALB health check |
| `GET /secrets` | JSON: `{name: value}` for every secret the pod can see | the migration parity check |

The app reads secrets from a **mounted/env k8s Secret** — it is store-agnostic
and never talks to AWS or Vault directly. That is the whole trick: the app is the
invariant, and everything *behind* the Secret is what migrates.

### Source topology (the dependency closure to discover)

```
web/Deployment/secrets-viewer      image=secrets-viewer:1.0  replicas=2
  ├─ envFrom  ConfigMap/web-config          (APP_ENV, LOG_LEVEL)   ← recall trap
  ├─ envFrom  Secret/web-secrets            (the synced secret)
  └─ serviceAccountName: secrets-viewer     (IRSA annotation)      ← recall trap
web/Service/secrets-viewer         ClusterIP :8080
web/Ingress/secrets-viewer         class=alb   host=secrets.example.com  + alb annotations
web/ServiceAccount/secrets-viewer  ann: eks.amazonaws.com/role-arn=arn:aws:iam::...:role/secrets-viewer
web/SecretStore/aws-sm             provider: aws (SecretsManager, region)
web/ExternalSecret/web-secrets     refreshInterval; data ← [demo/db-password, demo/api-key, demo/third-party-token]
web/Secret/web-secrets             (SYNCED by ESO from AWS — values present in-cluster)
```

And, in AWS Secrets Manager (the ultimate source of truth):

```
demo/db-password        = "s3cr3t-pw"
demo/api-key            = "ak_live_9f2..."
demo/third-party-token  = "tok_abc..."
```

### Discovery traps to seed on purpose

Discovery is **graph traversal from a seed**, not `kubectl get all`. `get all`
misses ConfigMaps, Secrets, ServiceAccounts, and the ESO CRs entirely. Seed the
namespace so a lazy pass fails and a real closure passes:

**Recall traps (must be found by following references):**
- `ConfigMap/web-config` — reachable only via the Deployment's `envFrom`.
- `ServiceAccount/secrets-viewer` — reachable only via `spec.serviceAccountName`; carries the IRSA annotation that explains *how* secrets work.
- `ExternalSecret/web-secrets` + `SecretStore/aws-sm` — CRs, invisible to `get all`.

**Precision traps (must NOT be migrated):**
- `Secret/sh.helm.release.v1.web.v1` — a Helm release blob. Copying it is wrong.
- `Secret/secrets-viewer-token-xxxx` — a ServiceAccount token. Auto-generated; must not travel.
- `Deployment/other-team-api` in the same `web` namespace — scope discipline: the agent must migrate *this app*, not the namespace.

> Discovery quality = **recall** (found the whole closure) × **precision**
> (left the junk). Score both when you test the agent.

---

## Part 1 — Secret migration (AWS Secrets Manager → local Vault)

**Decision taken:** the app stays store-agnostic; External Secrets Operator runs
on **both** sides; only the `SecretStore` backend swaps. The reference pattern is
the invariant.

```
SOURCE                                TARGET
 AWS Secrets Manager                   HashiCorp Vault (dev mode, 1 pod)
   ▲                                     ▲
   │ SecretStore(aws)                    │ SecretStore(vault)   ← the ONLY backend change
 ExternalSecret/web-secrets   ─────►   ExternalSecret/web-secrets  (data keys unchanged)
   │                                     │
 Secret/web-secrets (synced)          Secret/web-secrets (synced)
   │                                     │
 secrets-viewer (unchanged) ─────────► secrets-viewer (unchanged)
```

New mapping-table row:

| Source | Target | Note |
|---|---|---|
| `SecretStore` (AWS SM provider) + IRSA | `SecretStore` (Vault provider) + Vault token | pattern preserved; **values must be re-materialized into Vault**; IRSA → Vault auth is an accepted change |

### The three sub-problems (the meaty parts)

1. **Stand up the store.** Vault dev-mode `Deployment` + `Service` become
   components in the WorkloadPlan. Unsealed, root token — demo-grade.
2. **Migrate the values (data plane, not manifests).** Read the actual secret
   values on the source, write them into Vault at `secret/demo/*`. This is what
   `/secrets` parity ultimately proves.
3. **Rewire.** Point the target `SecretStore` at local Vault; ESO on the target
   syncs Vault → `Secret/web-secrets` → app.

### The no-boto3 bridge (stays in spec-02 scope)

The agent does **not** need AWS API access to get the values. ESO on the source
has *already* synced them into `Secret/web-secrets`, which `discover_source` can
read read-only. The agent reads that synced Secret and pushes the values into
Vault. (Reading straight from Secrets Manager via boto3 is the level-up, not
required here.)

### ⚠️ Open design problem #1 — how do the values actually enter Vault?

Your current spec-02 tools (`discover_source`, `declare_plan`, `get_plan_status`,
`describe`, `logs`, `check_escalations`) **only apply manifests**. None of them
move secret *data* into Vault. This demo surfaces a genuine gap. Three ways to
close it — decide which fits your seam:

| Option | How | Cost / risk |
|---|---|---|
| (a) new `seed_store` tool | agent reads source Secret, writes to Vault via its API | simplest; **values transit the agent workspace** |
| (b) bootstrap-Job component | agent creates a temp Secret with the values, a Job mounts it and `vault kv put`s, then the temp Secret is deleted | declarative/k8s-native; plaintext lands in a transient Secret; teardown ordering is fiddly |
| (c) store-to-store operator | operator (not agent) does the copy | most "correct"; violates "operator never does app-specific logic" — probably out of scope |

**Think about:** which of these keeps the operator dumb *and* keeps plaintext off
the agent? (Hint: none do both cleanly at PoC scale — which is itself the honest
finding to document.)

### ⚠️ Security note to declare (not hide)

In options (a) and (b) the plaintext secret values **transit the agent's
workspace or a temporary Secret**. That is an accepted loss of the PoC, and a
good demo *declares* it — same spirit as `accepted_losses` on the Ingress. In
production you'd want a path where plaintext never lands on the migrator.

### Validation — secret parity

```
curl http://secrets.example.com/secrets     # SOURCE (EKS, via ALB)
curl http://secrets.local/secrets           # TARGET (minikube, via nginx → Vault → ESO → Secret)
```

Both must return the identical `{name: value}` map. Because the source uses ESO
and the target uses ESO-with-Vault, a green parity check proves the values
*travelled the whole chain* — it is not satisfiable by copying a k8s Secret.

---

## Part 2 — ALB → nginx settings fidelity

This is the richer fidelity test: ALB annotations carry *behavior*, and they do
**not** map 1:1. Put a realistic set on the source Ingress:

```yaml
kind: Ingress
metadata:
  name: secrets-viewer
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-path: /healthz
    alb.ingress.kubernetes.io/load-balancer-attributes: idle_timeout.timeout_seconds=60
    alb.ingress.kubernetes.io/ssl-redirect: '443'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:...:certificate/abc
    alb.ingress.kubernetes.io/wafv2-acl-arn: arn:aws:wafv2:...:regional/webacl/xyz
```

### The four verdict classes (the taxonomy to demonstrate)

| Verdict | Source annotation | Target | Why it's interesting |
|---|---|---|---|
| **mapped 1:1** | `idle_timeout=60` | `nginx.ingress.kubernetes.io/proxy-read-timeout: "60"` | direct equivalent exists |
| **relocated** | `healthcheck-path: /healthz` | Deployment `readinessProbe.httpGet.path: /healthz` | **moves to a different resource** — an Ingress setting becomes a pod probe; a flat annotation-translator gets this wrong |
| **degraded** | `certificate-arn` (ACM) + `ssl-redirect` | self-signed TLS Secret + `force-ssl-redirect: "true"` | HTTPS survives; trust chain does not |
| **lost** | `wafv2-acl-arn`, `scheme: internet-facing`, `target-type` | *(nothing)* | no local equivalent → `accepted_losses` |

### The real validation artifact — the migration report

Since "identical behavior" is impossible, the deliverable is a **report with a
verdict per setting and zero `unaccounted` entries**:

```
setting                          verdict      target
idle_timeout=60                  mapped       proxy-read-timeout: "60"
healthcheck-path=/healthz        relocated    Deployment/readinessProbe
certificate-arn + ssl-redirect   degraded     self-signed TLS + force-ssl-redirect
wafv2-acl-arn                    lost         accepted_losses[]
scheme=internet-facing           lost         accepted_losses[] (N/A locally)
target-type=ip                   lost         accepted_losses[] (nginx routes to endpoints)
──────────────────────────────────────────────────────────────────
unaccounted: 0        ← the pass/fail line
```

The losses ride into the CR as annotations (`poc.local/accepted-losses`), exactly
as `build_workload_plan` already folds them (see `tools/models.py`). So the
report is reconstructable from the live CR — the accounting lives *in the
cluster*, not just in chat.

### One behavioral check (for the live "wow")

Pick a single setting and prove it end-to-end rather than on paper:
- **`ssl-redirect`:** `curl -I http://secrets.local/secrets` returns `308` → `https://…`.
- *(alt)* **`proxy-read-timeout`:** add a `/slow?sleep=65` endpoint; both ALB (idle 60) and nginx (proxy-read-timeout 60) cut it at ~60s with a 504.

---

## Validation summary (the three green lights)

| Check | Artifact | Passes only if |
|---|---|---|
| Secret parity | `/secrets` on both clusters | values traversed AWS→Vault→ESO→Secret→app |
| Settings fidelity | migration report | `unaccounted: 0` |
| Behavioral spot-check | one live curl | `ssl-redirect` (or timeout) reproduces |

Plus discovery scored separately: **recall** (found the closure incl. traps) and
**precision** (skipped Helm/SA-token/other-team objects).

---

## Open thinking problems (for you, before you build)

1. **Where do values enter Vault?** Resolve Open Problem #1 above. The "right"
   answer might be to *admit* the PoC has no clean option and document the
   tradeoff — that's a legitimate finding, not a failure.
2. **What is discovery's stopping condition?** Reference-chasing is a graph walk
   — where does it stop? (SA → its Role → its RoleBinding → …?) Define the
   closure boundary explicitly or the agent over- or under-collects.
3. **How does the agent *know* it found everything?** There is no oracle. Is the
   check "the app's `/secrets` works on the target" (behavioral, end-to-end) or
   "it enumerated N objects" (structural)? Which is more trustworthy, and why?
4. **Is `unaccounted: 0` game-able?** Could an agent mark everything `lost` and
   pass? What second signal catches that? (Hint: parity + behavioral check.)
5. **Idempotency.** `declare_plan` re-apply is idempotent for manifests — is
   *value seeding* idempotent? Re-running the migration must not double-write or
   drift Vault.

---

## Build checklist (your delivery — this is your todo, not mine)

Source (EKS) side:
- [ ] `secrets-viewer` app: `/healthz`, `/secrets`; reads secrets from env/mount (store-agnostic).
- [ ] AWS Secrets Manager: seed `demo/db-password`, `demo/api-key`, `demo/third-party-token`.
- [ ] Install ESO on EKS; `SecretStore(aws)` + `ExternalSecret/web-secrets`.
- [ ] Deployment + ClusterIP Service + ConfigMap + IRSA ServiceAccount.
- [ ] ALB Ingress with the full annotation set above.
- [ ] Seed the discovery traps (Helm secret, SA-token, other-team Deployment).

Target (minikube) side (what the agent should produce):
- [ ] Install ESO + nginx ingress on minikube (prerequisites, not migrated).
- [ ] Vault dev-mode Deployment + Service (plan components).
- [ ] Value-seeding path (Open Problem #1).
- [ ] `SecretStore(vault)` + the (nearly unchanged) `ExternalSecret`.
- [ ] Migrated Deployment/Service/ConfigMap + nginx Ingress with translated annotations.
- [ ] Migration report generation + the one behavioral check.

Test harness:
- [ ] Parity assertion (`/secrets` source == target).
- [ ] Report assertion (`unaccounted == 0`).
- [ ] Discovery recall/precision scoring against the seeded traps.
