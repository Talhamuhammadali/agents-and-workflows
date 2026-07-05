"""Identity constants for the WorkloadPlan CRD.

Single source for the group, version, and names of our own custom resource so
the CRD manifest, the Kopf handler registrations, the ownerReferences the
operator stamps on children, and the attribution labels all agree. Kopf does
not discover these for us: a handler declares which resource it watches, so
these constants are what we hand it.
"""

GROUP = "poc.local"
VERSION = "v1alpha1"
KIND = "WorkloadPlan"
PLURAL = "workloadplans"

API_VERSION = f"{GROUP}/{VERSION}"

DEFAULT_NAMESPACE = "default"

LABEL_PLAN = f"{GROUP}/plan"
LABEL_SESSION = f"{GROUP}/session"
LABEL_OWNER = f"{GROUP}/owner"
LABEL_COMPONENT = f"{GROUP}/component"
