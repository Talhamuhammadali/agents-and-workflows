"""Kopf handlers for the WorkloadPlan operator (the hands).

Each handler is deliberately thin: parse the resource into typed models, call
the pure decision functions in core, and perform the resulting I/O. Any real
branching lives in core with a unit test, not here. Handlers are synchronous
because the kubernetes client is synchronous; Kopf runs them in a thread pool.
"""

from typing import Any

import kopf

from workload_operator.constants import GROUP, LABEL_OWNER, LABEL_SESSION, PLURAL, VERSION
from workload_operator.core import build_child, is_ready, orphaned_children, plan_status_digest
from workload_operator.k8s import apply_manifest, delete_object, dynamic_client, get_object
from workload_operator.models import ChildStatus, OwnerMeta, parse_spec

HEALTH_INTERVAL = 15.0


def _owner_meta(name: str, namespace: str, uid: str, meta: kopf.Meta) -> OwnerMeta:
    """Assemble the owning-plan identity from the resource metadata."""
    labels = meta.get("labels", {})
    return OwnerMeta(
        name=name,
        uid=uid,
        namespace=namespace,
        session=labels.get(LABEL_SESSION, ""),
        owner=labels.get(LABEL_OWNER, ""),
    )


def _prune_orphans(client: Any, namespace: str, desired_names: set[str], status: Any, logger: Any) -> None:
    """Delete children recorded in status whose component left the spec.

    Kind-agnostic: it deletes whatever was recorded, so a removed inference CRD
    is pruned exactly like a removed Deployment, with no fixed kind list.
    """
    recorded = (status or {}).get("children", [])
    live = [
        {
            "component": child.get("name"),
            "kind": child.get("kind"),
            "api_version": child.get("apiVersion"),
            "name": child.get("objectName"),
        }
        for child in recorded
    ]
    for orphan in orphaned_children(desired_names, live):
        if orphan["api_version"] and orphan["name"]:
            delete_object(client, orphan["api_version"], orphan["kind"], orphan["name"], namespace)
            logger.info(f"pruned orphaned child {orphan['kind']}/{orphan['name']}")


@kopf.on.create(GROUP, VERSION, PLURAL)
@kopf.on.update(GROUP, VERSION, PLURAL)
@kopf.on.resume(GROUP, VERSION, PLURAL)
def reconcile(
    spec: kopf.Spec,
    meta: kopf.Meta,
    status: kopf.Status,
    name: str,
    namespace: str | None,
    uid: str,
    patch: kopf.Patch,
    logger: Any,
    **_: Any,
) -> None:
    """Apply every component as an owned child, prune removed ones, seed status.

    Idempotent via server-side apply, so create, update, and resume all reuse
    it. Pruning diffs the previously recorded children against the current spec,
    so a component dropped from the plan has its child deleted. The health timer,
    not this handler, decides readiness.
    """
    assert namespace is not None
    plan = parse_spec(dict(spec))
    owner = _owner_meta(name, namespace, uid, meta)
    client = dynamic_client()
    children = []
    for component in plan.components:
        manifest = component.manifest
        apply_manifest(client, build_child(component, owner))
        children.append(
            ChildStatus(
                name=component.name,
                kind=manifest.kind,
                apiVersion=manifest.apiVersion,
                objectName=manifest.metadata.name,
            ).model_dump()
        )
    _prune_orphans(client, namespace, {component.name for component in plan.components}, status, logger)
    patch.status["children"] = children
    patch.status["phase"] = "Pending"
    patch.status["readyCount"] = 0
    patch.status["observedGeneration"] = meta.get("generation")
    logger.info(f"reconciled {len(children)} component(s)")


@kopf.on.delete(GROUP, VERSION, PLURAL)
def on_delete(name: str, logger: Any, **_: Any) -> None:
    """Do nothing but log; ownerReferences cascade-delete the children."""
    logger.info(f"plan {name} deleted; children removed by cascade garbage collection")


@kopf.timer(GROUP, VERSION, PLURAL, interval=HEALTH_INTERVAL)
def health_sweep(
    spec: kopf.Spec,
    meta: kopf.Meta,
    name: str,
    namespace: str | None,
    uid: str,
    patch: kopf.Patch,
    logger: Any,
    **_: Any,
) -> None:
    """Reassess each child's health, self-heal missing ones, patch the digest."""
    assert namespace is not None
    plan = parse_spec(dict(spec))
    owner = _owner_meta(name, namespace, uid, meta)
    client = dynamic_client()
    children: list[ChildStatus] = []
    for component in plan.components:
        manifest = component.manifest
        kind = manifest.kind
        live = get_object(client, manifest.apiVersion, kind, manifest.metadata.name, namespace)
        if live is None:
            apply_manifest(client, build_child(component, owner))
            children.append(
                ChildStatus(
                    name=component.name,
                    kind=kind,
                    apiVersion=manifest.apiVersion,
                    objectName=manifest.metadata.name,
                    note="recreated",
                )
            )
            continue
        health = is_ready(kind, live)
        children.append(
            ChildStatus(
                name=component.name,
                kind=kind,
                apiVersion=manifest.apiVersion,
                objectName=manifest.metadata.name,
                ready=health.ready,
                failed=health.failed,
                note=health.note,
            )
        )
    digest = plan_status_digest(children)
    digest["observedGeneration"] = meta.get("generation")
    patch.status.update(digest)
