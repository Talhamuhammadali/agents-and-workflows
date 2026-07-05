#!/usr/bin/env bash
set -euo pipefail

EXPECTED_CONTEXT="minikube"
FIXTURES="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/fixtures"

ctx="$(kubectl config current-context)"
if [[ "$ctx" != "$EXPECTED_CONTEXT" ]]; then
  echo "ABORT: current context is '$ctx', expected '$EXPECTED_CONTEXT'." >&2
  echo "Switch with: kubectl config use-context $EXPECTED_CONTEXT" >&2
  exit 1
fi

echo "=== context: $ctx (safe) ==="
echo

echo "=== [1/3] good plan -> expect ACCEPTED ==="
kubectl apply -f "$FIXTURES/wp-good.yaml"
echo

echo "=== strip-vs-store: what the API server kept for the Deployment manifest ==="
echo "(replicas/selector/template present => preserve-unknown-fields works)"
kubectl get wp test-good -o jsonpath='{.spec.components[0].manifest.spec}' | python3 -m json.tool
echo

echo "=== [2/3] duplicate component names -> expect REJECTED (list-type map key) ==="
if kubectl apply -f "$FIXTURES/wp-dup.yaml" 2>&1; then
  echo "UNEXPECTED: duplicate plan was accepted."
else
  echo "OK: rejected as expected."
fi
echo

echo "=== [3/3] malformed manifest -> expect REJECTED (required apiVersion/kind) ==="
if kubectl apply -f "$FIXTURES/wp-malformed.yaml" 2>&1; then
  echo "UNEXPECTED: malformed plan was accepted."
else
  echo "OK: rejected as expected."
fi
echo

echo "=== cleanup ==="
kubectl delete wp test-good --ignore-not-found
echo "done."
