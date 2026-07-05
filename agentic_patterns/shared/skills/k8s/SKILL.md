---
name: k8s
description: Provision or migrate Kubernetes workloads by declaring a single WorkloadPlan on a target cluster and watching it converge.
allowed-tools: "declare_plan, get_plan_status, update_plan, delete_plan, list_plans, check_escalations, Read, Write, Edit"
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

Use `check_escalations()` to sweep every environment at once for plans that have
failed, when you are not tracking one plan by name.

`intent` is `provision` (stand up new workloads) or `migrate` (recreate what you
found in a source). It is a tag for your own reporting; the operator treats every
component the same.

## Choosing the target

`target` is the name of a kubernetes environment you were given. If you are
unsure which environment the user means, ask before declaring.

## Migrating a source

When the intent is `migrate` you are recreating something that already exists in
a source environment. There is no fixed mapping table — explore the source
yourself and decide the local equivalents with judgement. Migration is committal
and creates named resources, so it is bracketed by two mandatory `Ask` gates: you
never explore on a guess, and you never declare without sign-off.

1. **Ask before you explore (scope + commit gate).** Confirm with the user that
   they want to migrate, and pin down what is ambiguous *before* touching the
   source:
   - which components / which app they want migrated (do not assume the whole
     account — if the scope is unclear, `Ask`);
   - the names to use on the target: the target namespace, the plan name, and
     the component names (offer sensible defaults, but let the user name them).
   Only explore once scope and names are settled.
2. Explore the source read-only. For an AWS source the `aws` cli is already
   credentialed in your shell (dev mode); inventory only what is in scope and
   never mutate anything.
3. Write `inventory.md` — every in-scope source resource worth recreating, with
   the details you need to rebuild it (images, ports, replicas, env, config
   keys). If the inventory surfaces resources whose inclusion is ambiguous,
   `Ask` again to narrow before drafting the plan.
4. Draft the migration plan (write it to a file): map each inventory item onto a
   WorkloadPlan component under the agreed names and namespace. Where a mapping
   loses something (an AWS-managed load balancer, cert, or secret value that
   cannot be reproduced locally), record it on that component as
   `accepted_losses`, with `source_ref` naming where it came from. If a resource
   has no sensible local equivalent, say so and `Ask` rather than inventing one.
5. **Ask before you declare (final-plan gate).** Show the drafted plan — the
   component list, the chosen names/namespace, and every accepted loss — and get
   explicit approval. Migration is only committed after the user signs off here.
6. `declare_plan(intent="migrate", ...)` from the approved plan, then poll
   `get_plan_status` until Ready and report (including the accepted losses).
