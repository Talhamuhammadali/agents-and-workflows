"""Unit tests for the WorkloadPlan operator's pure decision functions.

No cluster, no async — the fast red-green loop. Run with:
    uv run pytest tests/operator/test_core.py
"""

from workload_operator.core import compute_phase
from workload_operator.models import ChildStatus


def _child(ready=False, failed=False):
    return ChildStatus(name="c", kind="ConfigMap", ready=ready, failed=failed)


def test_phase_ready_when_all_children_ready():
    assert compute_phase([_child(ready=True), _child(ready=True)]) == "Ready"


def test_phase_failed_when_any_child_failed():
    assert compute_phase([_child(ready=True), _child(failed=True)]) == "Failed"


def test_phase_pending_while_converging():
    assert compute_phase([_child(ready=True), _child()]) == "Pending"


def test_phase_failed_takes_precedence_over_pending():
    assert compute_phase([_child(), _child(failed=True)]) == "Failed"


def test_phase_pending_when_no_children_yet():
    assert compute_phase([]) == "Pending"
