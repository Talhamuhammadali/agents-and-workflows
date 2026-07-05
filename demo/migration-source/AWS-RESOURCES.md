# AWS resources created for the migration demo (source side)

Everything below was created on **2026-07-05** in:

- **Account:** `545009868178`
- **Region:** `us-west-2`
- **Cluster:** `ekai-demo-eks` (pre-existing company cluster — only added to, never replaced)

All demo resources are prefixed `talhas`. Use this list to clean up later.

---

## What was created

| # | Type | Identifier | Notes |
|---|------|-----------|-------|
| 1 | ECR repository | `talhas-secrets-viewer` | holds images `:1.0` and `:1.1` |
| 2 | Secrets Manager secret | `talhas/app-secrets` | single JSON blob (db-password, api-key, third-party-token) |
| 3 | IAM role | `talhas-secrets-viewer-irsa` | IRSA role, trusts cluster OIDC |
| 4 | IAM inline policy | `talhas-secrets-read` (on role above) | allows read of `talhas/*` secrets |
| 5 | K8s namespace | `talhas-experiments` | contains all the app objects below |
| 6 | ALB (auto-created) | `talhas-secrets-viewer` → `talhas-secrets-viewer-1808836117.us-west-2.elb.amazonaws.com` | created by the AWS LB Controller from the Ingress; deleting the Ingress/namespace deletes it (plus its target group + security groups) |

**Also changed (not created) — must be reverted:**

- **7. EKS endpoint allowlist.** Added this machine's IP `154.192.38.125/32` to `ekai-demo-eks` `publicAccessCidrs`.
  Original list was these 4 (revert to exactly these):
  `125.209.68.42/32`, `154.192.39.145/32`, `39.34.155.58/32`, `154.192.100.33/32`

---

## Cleanup (run in this order)

```bash
REGION=us-west-2

# 0. (kubectl needs a kubeconfig; regenerate if you don't have one)
aws eks update-kubeconfig --name ekai-demo-eks --region $REGION

# 1. Delete the namespace — this removes the Deployment/Service/Ingress,
#    and the LB Controller then tears down the ALB + target group + SGs.
kubectl delete namespace talhas-experiments

# 2. Delete the IAM role (inline policy must go first)
aws iam delete-role-policy --role-name talhas-secrets-viewer-irsa --policy-name talhas-secrets-read
aws iam delete-role      --role-name talhas-secrets-viewer-irsa

# 3. Delete the ECR repository (--force also deletes the images inside)
aws ecr delete-repository --repository-name talhas-secrets-viewer --region $REGION --force

# 4. Delete the Secrets Manager secret (no recovery window)
aws secretsmanager delete-secret --secret-id talhas/app-secrets --region $REGION --force-delete-without-recovery

# 5. Revert the EKS endpoint allowlist to the original 4 CIDRs
aws eks update-cluster-config --name ekai-demo-eks --region $REGION \
  --resources-vpc-config '{"endpointPublicAccess":true,"endpointPrivateAccess":true,"publicAccessCidrs":["125.209.68.42/32","154.192.39.145/32","39.34.155.58/32","154.192.100.33/32"]}'
```

## Verify nothing is left

```bash
REGION=us-west-2
aws ecr describe-repositories --repository-names talhas-secrets-viewer --region $REGION 2>&1        # expect: not found
aws secretsmanager list-secrets --region $REGION --filters Key=name,Values=talhas/ --query 'SecretList[].Name'   # expect: empty
aws iam get-role --role-name talhas-secrets-viewer-irsa 2>&1                                        # expect: NoSuchEntity
aws elbv2 describe-load-balancers --region $REGION --query "LoadBalancers[?LoadBalancerName=='talhas-secrets-viewer']"  # expect: []
```

> Note: only items 1–6 are billable demo resources. Item 7 is a config change on
> the shared cluster — revert it regardless of cost, since it widened who can
> reach the cluster API.
