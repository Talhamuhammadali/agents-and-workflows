"""Tool descriptions for the infrastructure agent tools."""

DECLARE_PLAN_DESCRIPTION = """Declare a set of components as a single WorkloadPlan on a target kubernetes environment.

Pass a plan name, the intent (migrate or provision), the list of components, and the name of the target
environment to apply to. Each component is an object with a unique 'name' and a 'manifest' (a complete
kubernetes object with apiVersion, kind and metadata.name). For a migration a component may also carry
'source_ref' (where it came from) and 'accepted_losses' (declared lossy mappings).

The plan is validated in process before anything reaches the cluster. On a validation error nothing is
applied and you are told exactly what to fix. On success an operator reconciles the plan into owned child
resources; call get_plan_status to watch it converge."""

GET_PLAN_STATUS_DESCRIPTION = """Read the status of a WorkloadPlan you declared.

Pass the plan name and the target environment name. Returns the phase (Pending, Ready or Failed), how many
children are ready, a per-child breakdown with any failure notes, and any NeedsAttention escalation naming
the children that need a human."""
