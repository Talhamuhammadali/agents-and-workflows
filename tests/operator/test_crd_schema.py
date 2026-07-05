"""Gate 2 tests: the CRD schema accepts good plans and rejects bad ones.

No operator is involved. These assert that the API server itself enforces the
contract at submit time, which is why the operator can stay dumb. Written
outside-in: the reject cases are the point. Each test runs in its own namespace.
"""

import pytest
from kubernetes.client.exceptions import ApiException

from tests.operator.conftest import create_plan, get_plan, load_fixture

pytestmark = pytest.mark.integration


def test_good_plan_is_accepted(namespace: str) -> None:
    name = create_plan(load_fixture("wp-good.yaml"), namespace)
    got = get_plan(name)
    assert got["spec"]["components"][0]["manifest"]["spec"]["replicas"] == 2


def test_duplicate_component_names_are_rejected(namespace: str) -> None:
    with pytest.raises(ApiException) as exc:
        create_plan(load_fixture("wp-dup.yaml"), namespace)
    assert exc.value.status == 422


def test_manifest_missing_apiversion_and_kind_is_rejected(namespace: str) -> None:
    with pytest.raises(ApiException) as exc:
        create_plan(load_fixture("wp-malformed.yaml"), namespace)
    assert exc.value.status == 422


def test_manifest_missing_metadata_name_is_rejected(namespace: str) -> None:
    with pytest.raises(ApiException) as exc:
        create_plan(load_fixture("wp-noname.yaml"), namespace)
    assert exc.value.status == 422
