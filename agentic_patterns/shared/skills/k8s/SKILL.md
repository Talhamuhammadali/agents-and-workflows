---
name: k8s
description: Provision or migrate Kubernetes workloads by declaring a single WorkloadPlan on a target cluster and watching it converge.
allowed-tools: "declare_plan, get_plan_status, update_plan, delete_plan, list_plans, Read, Write, Edit"
version: 0.1.0
---

# Kubernetes provisioning via WorkloadPlan

Your mode of provisioning here is the WorkloadPlan custom resource. You never
apply raw manifests to the cluster and you never run kubectl. You declare one
WorkloadPlan; an operator on the cluster reconciles it into owner-referenced
child resources, watches their health, and self-heals them. You own the desired
state you declare; the operator owns the status you read back.

## The loop

1. Decide the components. Each is a complete Kubernetes manifest (apiVersion,
   kind, metadata.name) plus a unique component name.
2. `declare_plan(name, intent, components, target)` — validated in process
   before anything reaches the cluster. A validation error tells you what to fix
   and applies nothing.
3. `get_plan_status(name, target)` — poll until phase is Ready or Failed.
4. Report. On Failed, a NeedsAttention line names the children that need a human.

`intent` is `provision` (stand up new workloads) or `migrate` (recreate what you
found in a source). It is a tag for your own reporting; the operator treats every
component the same.

## Choosing the target

`target` is the name of a kubernetes environment you were given. If you are
unsure which environment the user means, ask before declaring.

## Migration mapping (source to target)

When migrating from AWS, map each source resource onto a local equivalent and
record any loss on the component as `accepted_losses`, with `source_ref` naming
where it came from. Supported attachments for now:

| Source (AWS) | Target | Note |
|---|---|---|
| ALB / NLB Ingress | nginx Ingress | drops WAF and ACM cert; host preserved |
| Secrets Manager secret | Kubernetes Secret | value must be re-supplied locally |

Anything you can explore but not yet attach (RDS, ECR, CodeBuild, IAM, ...) goes
in your inventory as explored-but-unsupported. Do not invent a mapping for it —
say so and ask.
