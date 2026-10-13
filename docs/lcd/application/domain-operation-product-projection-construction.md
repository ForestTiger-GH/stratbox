# LCD candidate — domain Operation to product offering projection

**Grade:** \`LCD_CANDIDATE\` for a bounded Qt-independent operation-to-offering construction and cold-implementer fake; \`LCD_BLOCKED\` for a globally canonical domain registry, actual hosted publication/admission, dynamic provider trust and cross-platform release. **Edition:** 2026-10-13. **All Python below is CANDIDATE_DESIGN documentation, not existing Strategy Box source, an adopted public API or a runnable production feature.**

**Consumer and authority.** The admitted architectural constraints are an independently callable analytical **stratbox** core, a separate Strategy Box application/presentation responsibility and an external managed platform boundary. The developer goal of a larger discoverable product-operation catalog is recorded as **U-01**, with the exact catalog ontology, stable IDs, exposure policy and physical package location still open in [Product commitments](../../what/strategy-box/commitment-census.md). A planned logical common host exists as a product direction; creating a separate physical **stratbox-application** repository is still a Product/Engineering Decision. The [application allocation](../../architecture/application-authority-placement.md), [Target HOW-A](../../how/application/invoke-and-interpret.md) and [capability Science](../../science/capabilities/composition-identity-and-user-machine-projections.md) constrain this design. The [local Scenario LCD](local-scenario-execution-construction.md) owns execution, the [host LCD](../hosting/host-authority-and-client-contract-construction.md) owns authoritative hosted admission, and the [machine LCD](../capabilities/curated-machine-operation-adapter-construction.md) owns any approved machine projection. This packet owns **only** the missing domain-definition → curated product-offering → validated invocation seam.

## 1. Exact brownfield limit and motivation

At the pinned Windows implementation revision \`959e9c4ce1441124af5111c1e025041714e04d3b\`, **OperationSpec** in \`application/operations/catalog/models.py\` mixes product title/group, presentation controls, handler string, fixed values, workspace and danger flags. **OperationParamSpec** describes six basic field types; **build_operation_registry** statically defines three product operations. **resolve_params()** merges defaults and arbitrary supplied keys, then overlays fixed values; its implementation alone does **not** validate unknown keys, field applicability, effect permission or a stable core domain definition. One composite Scenario and an atomic wrapper reuse these specifications, but this is not a verified universal domain catalog.

The pinned core FRG API \`run_frg_stage1(root_dir, *, recursive=False, filestore=None) -> dict[str, object]\` returns catalog/latest/dispatch tables. A domain method and an application offering therefore have different consumers and completeness standards. Other core domains already use richer typed Requests/Results. A global operation registry is **not** entailed by these differences; first prove a stable binding for one real operation, with notebook calls untouched. Prior design alternatives—direct handwritten product wrappers, a limited explicit catalog, and fully automatic Python reflection—have different cost/trust profiles. Automatic exposure of every callable is rejected as unsafe and semantically indiscriminate.

**Current-to-target delta:** retain the independently imported core domain function and proven user-visible form semantics; replace the implicit trust in app-supplied parameter dictionaries with an explicitly **versioned curated binding**, **separate user presentation**, **server-side sealing of effective inputs**, and **host effect authorization**. Existing user history is a dated observation, not a promise to reinterpret old cases under new defaults.

## 2. Responsibility and candidate source placement

~~~text
stratbox [existing independent analytics owner]
  domain public function / Request / Result / source and calculation meaning
  optional admitted domain definition/validator (only if a real caller needs it)
          ↑ typed adapter, without core importing an application
Strategy Box logical application authority [candidate common source seam]
  capabilities/domain_binding.py    exact curated installed binding, no client imports
  offerings/contracts.py            offering/field identity and versioned schemas
  offerings/catalog.py              visibility/discovery and safe UI projection
  offerings/resolve.py              trusted effective-parameter compilation
  offerings/serialization.py        canonical sealed-parameter bytes and digest
          ↓ one validated invocation and version-bound binding
  local/host Scenario executor       existing separate LCD owner
          ↓ safe projections only
stratbox-windows / stratbox-web / stratbox-android [clients]
  render fields, obtain suggestions and submit offering ID/revision + user edits
  no domain source code, trust-gate or outcome ledger copied into each client
AppDock [external owner]
  optional lifecycle/activation integration; never domain registry owner
~~~

These are **logical names**; the target-language examples use Python because the observed core/Windows code is Python. A later Web/Android implementation may consume a separately versioned safe transport schema rather than import Python classes. The source package/repository, RPC dialect and actual host process are **BOUNDED_OPEN / BLOCKED** as appropriate. Application authority alone may resolve a handler from its trusted installation binding. A client-provided module/function string is rejected.

## 3. Distinct identities and safe option/default semantics

- **Domain definition ID + semantic revision:** method, units, input/result validity, side effects and scientific scope. Core module path and distribution build are distinct binding provenance.
- **Offering ID + offering revision:** one curated human-facing form and its parameter narrowing. Multiple offerings can reference one domain method. Title, icon and translation can vary without silently changing domain semantics.
- **Scenario/composition ID + revision:** one runnable plan that uses offerings or operations; a catalog folder is not thereby an executable Cascade.
- **Binding revision:** a verified installed implementation selected for one compatible definition. Presence in a catalog is not readiness or authorization.
- **Rendered choice/suggestion revision:** a scoped, expiring **hint**, never an admission receipt or validation of a current source/permission. Suggestions may depend on data/workspace; host re-resolves authoritative defaults at submission. User-preference retention must not change old recorded effective inputs.
- **Invocation identity:** offering and definition versions plus validated sealed actual parameters. A host Run/Attempt/effect retains its **own** authority and identity and is not created by mere form compilation.

**Consequence:** a hidden fixed parameter is a contract binding, not security through obscurity. The client must not override it even if it forges a request. Secret values and privileged path handles must not appear in field snapshots. Changing a default or form revision must not mutate a previously accepted Run.

## 4. Concrete Python construction — CANDIDATE_DESIGN

~~~python
# application_authority/offerings/contracts.py -- DOCUMENTATION ONLY
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Protocol

class ProjectionFailure(str, Enum):
    UNKNOWN_OFFERING = "unknown_offering"
    STALE_OFFERING = "stale_offering"
    BINDING_MISMATCH = "binding_mismatch"
    FORBIDDEN_PARAMETER = "forbidden_parameter"
    UNKNOWN_PARAMETER = "unknown_parameter"
    INVALID_PARAMETERS = "invalid_parameters"
    CONTEXT_CHANGED = "context_changed"
    UNAVAILABLE = "unavailable"

@dataclass(frozen=True, slots=True)
class PublicField:
    key: str
    display_label: str
    presentation_kind: str  # e.g. choice / bool / integer / scoped-resource
    required: bool
    # No client-supplied validators, executables, absolute secret locators.

@dataclass(frozen=True, slots=True)
class ProductOffering:
    offering_id: str
    offering_revision: str
    domain_operation_id: str
    domain_definition_revision: str
    fields: tuple[PublicField, ...]
    fixed_values: Mapping[str, object]       # trusted server snapshot
    permitted_user_keys: frozenset[str]
    # Display and authorization are separate. No executable handler path.

@dataclass(frozen=True, slots=True)
class DomainBinding:
    operation_id: str
    definition_revision: str
    binding_revision: str
    installed: bool
    # The callable is held in a trusted server-side binding, not serialized.

@dataclass(frozen=True, slots=True)
class FormSuggestion:
    offering_id: str
    offering_revision: str
    context_revision: str
    suggestion_revision: str
    proposed_values: Mapping[str, object]
    # Advisory and audience-scoped; it grants no authority.

@dataclass(frozen=True, slots=True)
class ProductFormSubmission:
    offering_id: str
    offering_revision: str
    context_revision_seen: str
    user_values: Mapping[str, object]
    # Authenticated actor and permission scopes are NOT fields supplied here.

@dataclass(frozen=True, slots=True)
class SealedParameters:
    canonical_bytes: bytes
    digest_sha256: str
    schema_revision: str

@dataclass(frozen=True, slots=True)
class ResolvedProductInvocation:
    offering_id: str
    offering_revision: str
    domain_operation_id: str
    domain_definition_revision: str
    binding_revision: str
    context_revision: str
    parameters: SealedParameters

class ProjectionError(ValueError):
    def __init__(self, reason: ProjectionFailure):
        self.reason = reason
        super().__init__(reason.value)

class CuratedOfferingPort(Protocol):
    def exact(self, offering_id: str, revision: str) -> ProductOffering: ...

class InstalledDomainPort(Protocol):
    def exact(self, operation_id: str, revision: str) -> DomainBinding: ...
    def validate_effective(self, binding: DomainBinding,
                           values: Mapping[str, object]) -> Mapping[str, object]: ...

class ContextDefaultsPort(Protocol):
    def resolve(self, offering: ProductOffering, trusted_context: object
                ) -> tuple[str, Mapping[str, object]]: ...

class CanonicalParametersPort(Protocol):
    def seal(self, validated: Mapping[str, object],
             definition_revision: str) -> SealedParameters: ...
~~~

The **canonical sealer** must reject nonportable objects, unbounded nested data, NaN/nonfinite numbers, ambiguous dates/units, duplicate/unknown keys, sensitive values and mutable references unless an approved typed schema provides an explicit representation. It produces an immutable bytes snapshot under versioned canonicalization, with the hash over exactly those bytes and relevant schema/domain revision identity. This is a **candidate local application record**, not a public wire format. File/resource input must resolve to an authorized scoped reference through the host/security boundary, not an arbitrary client pathname.

~~~python
# application_authority/offerings/resolve.py -- CANDIDATE_DESIGN
class ProductInvocationCompiler:
    def __init__(self, *, offerings: CuratedOfferingPort,
                 installed: InstalledDomainPort,
                 defaults: ContextDefaultsPort,
                 sealer: CanonicalParametersPort):
        self.offerings = offerings
        self.installed = installed
        self.defaults = defaults
        self.sealer = sealer

    def compile(self, request: ProductFormSubmission,
                *, trusted_context: object) -> ResolvedProductInvocation:
        # 1. Resolve exact approved offering revision, never latest-by-title.
        # Port errors are mapped to typed safe failures by the adapter.
        offering = self.offerings.exact(
            request.offering_id, request.offering_revision)
        binding = self.installed.exact(
            offering.domain_operation_id, offering.domain_definition_revision)
        if (not binding.installed
                or binding.operation_id != offering.domain_operation_id
                or binding.definition_revision != offering.domain_definition_revision):
            raise ProjectionError(ProjectionFailure.BINDING_MISMATCH)

        # 2. A forged field cannot expand the public offering.
        allowed = {field.key for field in offering.fields}
        if (len(allowed) != len(offering.fields)
                or allowed != set(offering.permitted_user_keys)
                or allowed.intersection(offering.fixed_values)):
            raise ProjectionError(ProjectionFailure.INVALID_PARAMETERS)
        if set(request.user_values) - allowed:
            raise ProjectionError(ProjectionFailure.UNKNOWN_PARAMETER)
        if set(request.user_values).intersection(offering.fixed_values):
            raise ProjectionError(ProjectionFailure.FORBIDDEN_PARAMETER)

        # 3. Trusted contextual defaults must be re-evaluated on the host.
        context_revision, defaults = self.defaults.resolve(
            offering, trusted_context)
        if context_revision != request.context_revision_seen:
            raise ProjectionError(ProjectionFailure.CONTEXT_CHANGED)
        if (set(defaults) - allowed
                or set(defaults).intersection(offering.fixed_values)):
            raise ProjectionError(ProjectionFailure.INVALID_PARAMETERS)

        # 4. Bind user input, guarded defaults and fixed values.
        merged = dict(defaults)
        merged.update(request.user_values)
        merged.update(offering.fixed_values)
        # Domain validator checks required values, units, types, resources,
        # effect target boundaries, semantic and period applicability.
        validated = self.installed.validate_effective(binding, merged)
        sealed = self.sealer.seal(validated, binding.definition_revision)
        return ResolvedProductInvocation(
            offering.offering_id, offering.offering_revision,
            binding.operation_id, binding.definition_revision,
            binding.binding_revision, context_revision, sealed)
~~~

**Compiler responsibility stops at a sealed candidate invocation.** It neither admits a host Run nor grants read/write/delete privileges. The host receives a trusted actor resolved from authentication, performs actual object/effect/budget/approval checks, atomically records the intention and binds the installed callable. It must requalify an effective snapshot when a source, target generation, approval or policy can change between compilation and effect. Any lost host admission acknowledgement remains unknown until reconciliation under a stable intention key: the compiler cannot infer rejection and may not create a second intention silently.

### Host and client adapters (candidate boundaries)

~~~python
# application_authority/offerings/catalog.py -- DOCUMENTATION ONLY
class AuthorizedOfferingViewPort(Protocol):
    def list_displayable(self, trusted_actor: object,
                         trusted_context: object) -> tuple[ProductOffering, ...]: ...
    def suggestions(self, trusted_actor: object,
                    offering: ProductOffering,
                    trusted_context: object) -> FormSuggestion: ...

# Pure semantic renderer in any Windows/Web/Android client:
# render FormSuggestion + PublicField and send ProductFormSubmission.
# Client state owns only form edits, loading/error feedback and read cursors.
# Reuse the existing Scenario/Run authority ports for execution and observation.
# The actual authentication/transport/display stack is intentionally unspecified.
~~~

The client-visible projection must redact **fixed_values** and any protected binding metadata; the complete **ProductOffering** above is an internal application-authority record, so a real adapter must expose an explicit narrower DTO rather than serialize it whole. Displayability is never sufficient for effect admission. Stale form data receives a typed re-render/refresh outcome, not covert execution using new defaults. Form choices can be paginated/bounded but cannot remotely execute Python provider names.

## 5. Cold-implementer conformance plan — PROPOSED, UNEXECUTED

~~~python
# tests/application/test_product_projection.py -- proposed fixtures
def test_unknown_client_parameter_is_rejected(compiler, forged_submission):
    assert compile_failure(compiler, forged_submission) == "unknown_parameter"

def test_hidden_fixed_parameter_override_is_rejected(compiler, forged_fixed):
    assert compile_failure(compiler, forged_fixed) == "unknown_parameter"
    # A final adapter may use a distinct forbidden_parameter classification;
    # disclosure-safe error policy must be chosen consistently.

def test_context_changed_requires_refresh(compiler, old_context_revision):
    assert compile_failure(compiler, old_context_revision) == "context_changed"

def test_display_label_change_preserves_domain_revision(offerings):
    assert offerings.localize("fi").domain_definition_revision == (
        offerings.localize("en").domain_definition_revision)

def test_same_domain_can_have_two_curated_offerings(catalog):
    assert catalog.offering_a.domain_operation_id == catalog.offering_b.domain_operation_id
    assert catalog.offering_a.offering_id != catalog.offering_b.offering_id

def test_uninstalled_domain_binding_is_not_callable(compiler, absent_binding):
    assert compile_failure(compiler, absent_binding) == "binding_mismatch"

def test_client_cannot_send_callable_module_path(compiler, arbitrary_handler):
    assert compile_failure(compiler, arbitrary_handler) == "unknown_parameter"

def test_choice_hint_is_revalidated_at_authority(compiler, expired_hint):
    assert compile_failure(compiler, expired_hint) in (
        "invalid_parameters", "context_changed")

def test_public_view_excludes_fixed_and_secret_values(renderer, internal_offering):
    assert renderer.encode(internal_offering).contains_no_private_values()

def test_core_direct_python_invocation_remains_usable(core_fixture):
    assert core_fixture.call_without_app_authority().has_domain_result()

def test_old_run_retains_sealed_bytes_after_form_revision(host_history):
    assert host_history.old_run.used_bytes == host_history.original_bytes

def test_authorized_catalog_visibility_is_not_effect_grant(host, displayed_offering):
    assert host.revoke_effect_then_submit(displayed_offering).denied
~~~

These are **test intentions**, not executable fixtures or current conformance passes. A minimum coded pilot should pair one actual domain request/result with two offerings, one dynamic choice provider fake, one denial after visible selection and a second direct-Python consumer. Compare source/domain semantics and final Artifact/Run outcomes independently. A static Python parser or fake registry alone cannot prove real effective-permission checks, package topology, browser trust or cross-client parity.

## 6. Decision closure, constrained freedom and readiness

| Choice | Status | Who/what closes it |
| --- | --- | --- |
| Domain meaning stays in **stratbox**; curated application form and authorization sit outside core | **FIXED architectural boundary** | Existing public product constraints |
| One core operation may have zero, one or several offerings; screen labels do not define method identity | **CANDIDATE semantics**, strongly justified | Product application owner; actual two-offering pilot |
| Source module layout above and explicit Python ports | **BOUNDED design freedom** | Engineering owner; consumer/import test |
| Stable operation/offering identity lifecycle and semantic revision policy | **LCD_BLOCKED** | Product/catalog owner; stored-run migration/equivalence tests |
| Choice/default contextual source and trusted resource-selector schema | **LCD_BLOCKED** | Product/domain/security owners; stale/failure/concurrency tests |
| Field types, localized rendering, client platform toolkit | **DELEGATED_NONMATERIAL** subject to accessibility and privacy checks | Windows/Web/Android owner |
| Automated discovery versus manually curated installation bindings | **BOUNDED** to explicitly admitted, nonreflective registrations; global catalog **BLOCKED** | Core/application owners and demonstrated demand |
| Real host Run admission, transport, auth and revocation | **LCD_BLOCKED** | Host/security Product Decisions, native installed tests |
| Direct Python core usability | **FIXED** and must remain verified | Core code owner, import and domain tests |
| Generic plugin/provider internals and platform installation | **NOT_APPLICABLE** to this product projection seam | Separate neutral binding and external integration owners |

**Cold implementer verdict:** one engineer can implement a standalone Python fake/catalog-to-domain projection and guarded invocation compiler using the classes and tests above, while leaving physical repository placement and the host adapter behind explicit ports. Shipping this as authoritative host catalog, browser/Android API or secure operation executor requires decisions and real implementations listed above. **Overall scope: LCD_CANDIDATE; hosted/external claims LCD_BLOCKED.** No change to production code, external clients, Research coverage dispositions or independent lossless assurance is claimed.

**Reopen** on accepted catalog ontology, Product offering policy, domain API revision, new platform consumers, actual artifact/effect storage, authenticated scope or native cross-client evidence.
