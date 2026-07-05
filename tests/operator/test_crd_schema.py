"""Gate 2 tests: the CRD schema accepts good plans and rejects bad ones.

No operator is involved. These assert that the API server itself enforces the
contract at submit time, which is why the operator can stay dumb. Written
outside-in: the reject cases are the point. Each test runs in its own namespace.
"""

import pytest
from kubernetes import client
from kubernetes.client.exceptions import ApiException

from tests.operator.conftest import load_fixture
from workload_operator.constants import GROUP, PLURAL, VERSION

pytestmark = pytest.mark.integration


def _create(ns: str, body: dict) -> None:
    client.CustomObjectsApi().create_namespaced_custom_object(
        group=GROUP, version=VERSION, namespace=ns, plural=PLURAL, body=body
    )


def test_good_plan_is_accepted(namespace: str) -> None:
    body = load_fixture("wp-good.yaml")
    _create(namespace, body)
    got = client.CustomObjectsApi().get_namespaced_custom_object(
        group=GROUP, version=VERSION, namespace=namespace, plural=PLURAL, name=body["metadata"]["name"]
    )
    assert got["spec"]["components"][0]["manifest"]["spec"]["replicas"] == 2


def test_duplicate_component_names_are_rejected(namespace: str) -> None:
    with pytest.raises(ApiException) as exc:
        _create(namespace, load_fixture("wp-dup.yaml"))
    assert exc.value.status == 422


def test_manifest_missing_apiversion_and_kind_is_rejected(namespace: str) -> None:
    with pytest.raises(ApiException) as exc:
        _create(namespace, load_fixture("wp-malformed.yaml"))
    assert exc.value.status == 422


def test_manifest_missing_metadata_name_is_rejected(namespace: str) -> None:
    with pytest.raises(ApiException) as exc:
        _create(namespace, load_fixture("wp-noname.yaml"))
    assert exc.value.status == 422
