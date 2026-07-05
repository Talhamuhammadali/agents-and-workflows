"""Unit tests for orphaned_children (the kind-agnostic prune decision).

Pure: desired component names plus recorded child descriptors in, the children
to delete out. No cluster.
"""

from workload_operator.core import orphaned_children


def _child(component, kind="ConfigMap"):
    return {"component": component, "kind": kind, "api_version": "v1", "name": component}


def test_no_orphans_when_all_children_are_desired():
    live = [_child("a"), _child("b")]
    assert orphaned_children({"a", "b"}, live) == []


def test_child_dropped_from_spec_is_orphaned():
    live = [_child("a"), _child("b")]
    orphans = orphaned_children({"a"}, live)
    assert len(orphans) == 1
    assert orphans[0]["component"] == "b"


def test_child_without_component_label_is_left_alone():
    live = [{"component": None, "kind": "ConfigMap", "api_version": "v1", "name": "x"}]
    assert orphaned_children({"a"}, live) == []


def test_empty_live_set_has_no_orphans():
    assert orphaned_children({"a"}, []) == []
