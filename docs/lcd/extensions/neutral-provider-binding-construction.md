# LCD candidate — neutral provider discovery, selection, binding and conformance

**Status:** \`LCD_CANDIDATE\` for one typed public-neutral binding seam and fake/installed-wheel test plan; \`LCD_BLOCKED\` for adopting a general extension API, package/privilege policy, user configuration and cross-platform availability contract. Prepared 2026-10-12. All Python below is \`CANDIDATE_DESIGN\`, not installed code, an accepted SDK or a conformance certificate. This document describes **only generic public contracts**; separately deployed provider implementations own their own private configuration and code.

**Ownership:** [Product boundary](../../what/strategy-box/commitment-census.md) PC-SB-001, PC-SB-002 and PC-SB-007; [provider conformance LDD](../../ldd/extensions/neutral-provider-conformance-vectors.md), [capability readiness Science](../../science/extensions/provider-discovery-binding-readiness-and-conformance.md), [public-neutral threat Science](../../science/extensions/trusted-provider-conformance-and-false-success-threats.md) and [configuration boundary Science](../../science/extensions/configuration-catalog-readiness-and-surface-boundaries.md). **Current source:** core \`src/stratbox/base/runtime.py\` at \`stratbox@8459dc58922b7e8df853cf1d9e8131fa9e132580\` discovers optional infrastructure contributors; selection/fallback and styling contribution behavior is narrower and less typed than this target. Discovery success in the current code does not prove an installed compatible or healthy provider.

## 1. Responsibility separation, applicability and non-goals

An installed package may be discoverable, yet incompatible, unselected, unconfigured, not ready for a specific dataset/storage action, or not authorized for the actual user's effect. Those are different facts. A provider implementing neutral network/storage/secret/style functionality **does not own** canonical banking data, product Artifact identity, user Work, Case state, Run outcome, host permissions or AppDock package installation.

Only a small seam serving a real consumer should be constructed first. This LCD does not mandate a universal plugin manager, marketplace, package installer, Python sandbox, cross-client UI renderer, arbitrary client JavaScript or domain-result override. Independent \`stratbox\` calculation remains callable directly from Python with an explicitly selected neutral backend. Host/client Web/Windows/Android display provider status through product-owned view models, with no dependency on an installed private package name.

## 2. Candidate module layout — documentation only

~~~text
Public-neutral library seam (physical placement requires authority):
    base/capabilities/
        descriptors.py       version/slots/type and pure metadata
        discovery.py         read installed entry-point metadata without side effects
        selection.py         deterministic explicit policy and collision diagnostics
        binding.py           validated capability composition, no hidden fallback
        readiness.py         context-specific availability, safe errors and health
        conformance.py       capability-focused test contract, profile-specific results
        errors.py            typed unavailable/unsupported/partial/unknown outcomes
Application-side, if a real UI host consumer exists:
    application/extensions/
        catalogue_view.py    installed/compatible/selected/ready vs permitted projection
        configuration.py     product-owned declarative form and local/managed policy
Tests:
    tests/neutral_capabilities/test_duplicate_and_missing.py
    tests/neutral_capabilities/test_no_import_side_effect.py
    tests/neutral_capabilities/test_no_false_success.py
    tests/neutral_capabilities/test_provider_fallback_policy.py
    tests/neutral_capabilities/test_wheel_and_runtime_asset.py
~~~

A logical file layout is **not** a commitment to introduce all these modules, a third repository or a state database. A minimal functional adapter and tests can collapse several files when a single component is sufficient.

## 3. Candidate typed discovery and binding contracts

~~~python
# base/capabilities/descriptors.py -- CANDIDATE_DESIGN
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Mapping

class ContributionKind(str, Enum):
    FILE_BYTES = "file_bytes"
    NETWORK_ROUTE = "network_route"
    SECRET_RESOLUTION = "secret_resolution"
    FORMAT_CODEC = "format_codec"
    STYLE_RESOURCES = "style_resources"
    DOMAIN_OPERATION = "domain_operation"

class BindingStatus(str, Enum):
    NOT_SELECTED = "not_selected"
    INCOMPATIBLE = "incompatible"
    CONFIGURATION_REQUIRED = "configuration_required"
    READY = "ready"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    CONTRACT_FAILURE = "contract_failure"

class FailureKind(str, Enum):
    UNAVAILABLE = "unavailable"
    UNSUPPORTED = "unsupported"
    PERMISSION_DENIED = "permission_denied"
    PARTIAL_FAILURE = "partial_failure"
    OUTCOME_UNKNOWN = "outcome_unknown"

@dataclass(frozen=True, slots=True)
class ProviderDescriptor:
    public_provider_id: str
    distribution_ref: str        # package ID/version, not execution authority
    api_major: int
    api_minor: int
    contribution_kind: ContributionKind
    capability_slot: str
    capability_revision: str
    requires_configuration: bool

@dataclass(frozen=True, slots=True)
class BindingPolicy:
    scope_ref: str
    singleton_choice: Mapping[str, str]  # slot -> provider ID
    allow_optional_fallback: frozenset[str]
    required_slots: frozenset[str]

@dataclass(frozen=True, slots=True)
class BindingResult:
    capability_slot: str
    provider_id: str | None
    status: BindingStatus
    safe_code: str
    contract_revision: str | None

@dataclass(frozen=True, slots=True)
class CapabilityFailure:
    kind: FailureKind
    safe_code: str
    retryable: bool
    effect_uncertain: bool

class DiscoveryPort(Protocol):
    def list_metadata_only(self) -> tuple[ProviderDescriptor, ...]: ...

class CompatibilityPort(Protocol):
    def validate(self, descriptor: ProviderDescriptor,
                 required_major: int) -> bool: ...

class ActivationPort(Protocol):
    def activate(self, descriptor: ProviderDescriptor,
                 scoped_configuration: Mapping[str, object]) -> object: ...

class HealthPort(Protocol):
    def check(self, provider: object, scope_ref: str) -> BindingStatus: ...
~~~

**Types are candidates, not mandated public API.** Exact public entry-point group, version-major strategy and compatibility policy need approval. In-process Python provider code is trusted executable code with the ordinary process privileges; import success **is not sandboxing**, so supply-chain trust and package installation belong to a separate deployment owner.

## 4. Deterministic binding and failure behavior — CANDIDATE_DESIGN

~~~python
# base/capabilities/selection.py -- CANDIDATE_DESIGN
class NeutralProviderResolver:
    def __init__(self, discovery: DiscoveryPort, compatibility: CompatibilityPort,
                 activation: ActivationPort, health: HealthPort):
        self.discovery = discovery
        self.compatibility = compatibility
        self.activation = activation
        self.health = health

    def resolve(self, policy: BindingPolicy, slot: str,
                *, required_major: int,
                configuration: Mapping[str, object]) -> BindingResult:
        descriptors = tuple(
            d for d in self.discovery.list_metadata_only()
            if d.capability_slot == slot)
        ids = [d.public_provider_id for d in descriptors]
        if len(ids) != len(set(ids)):
            return BindingResult(slot, None, BindingStatus.CONTRACT_FAILURE,
                                 "DUPLICATE_PROVIDER_ID", None)
        chosen_id = policy.singleton_choice.get(slot)
        if chosen_id is None:
            # Optional unbound feature stays explicit; required one fails.
            code = ("REQUIRED_PROVIDER_NOT_SELECTED" if slot in policy.required_slots
                    else "OPTIONAL_PROVIDER_NOT_SELECTED")
            return BindingResult(slot, None, BindingStatus.NOT_SELECTED, code, None)
        chosen = next((d for d in descriptors if d.public_provider_id == chosen_id), None)
        if chosen is None:
            return BindingResult(slot, chosen_id, BindingStatus.UNAVAILABLE,
                                 "SELECTED_PROVIDER_NOT_INSTALLED", None)
        if not self.compatibility.validate(chosen, required_major):
            return BindingResult(slot, chosen_id, BindingStatus.INCOMPATIBLE,
                                 "API_MAJOR_INCOMPATIBLE", chosen.capability_revision)
        # A declared configuration requirement must not be silently promoted
        # to a ready provider through an empty/default activation.
        # Complete schema validation still belongs to the trusted activator.
        if chosen.requires_configuration and not configuration:
            return BindingResult(slot, chosen_id, BindingStatus.CONFIGURATION_REQUIRED,
                                 "SCOPED_CONFIGURATION_REQUIRED",
                                 chosen.capability_revision)
        try:
            instance = self.activation.activate(chosen, configuration)
            readiness = self.health.check(instance, policy.scope_ref)
        except Exception:
            return BindingResult(slot, chosen_id, BindingStatus.CONTRACT_FAILURE,
                                 "ACTIVATION_OR_HEALTH_FAILED", chosen.capability_revision)
        if not isinstance(readiness, BindingStatus):
            return BindingResult(slot, chosen_id, BindingStatus.CONTRACT_FAILURE,
                                 "HEALTH_STATUS_CONTRACT_INVALID",
                                 chosen.capability_revision)
        if readiness is not BindingStatus.READY:
            return BindingResult(slot, chosen_id, readiness,
                                 "PROVIDER_NOT_READY",
                                 chosen.capability_revision)
        return BindingResult(slot, chosen_id, BindingStatus.READY,
                             "BOUND_AND_HEALTHY", chosen.capability_revision)
~~~

**Unresolved critical contract:** a \`BindingResult\` metadata record alone does not own the lifetime of \`instance\`, resource cleanup, concurrent call fencing, credential rotation, request-level availability or return a typed capability port for a caller. A production binding must include an exact context-managed instance/lease and cancellation/cleanup protocol, with validated capability-specific ports and error mapping. The result type above is a first *selection visibility* component, not a complete executor binding. An independently coded caller may not use a descriptor ID as a handler reference to import arbitrary modules on demand.

**Fallback policy:** the chosen required provider must not silently fall back to a different provider when activation/readiness fails. Even for an optional slot, fallback requires an accepted compatible choice, observable provenance and a stability rule for in-flight operations. Some provider failures represent \`OUTCOME_UNKNOWN\` because an external write could have committed before a response was lost; these cannot turn into an empty successful list.

**Producer fault-boundary correction:** an extension health function may return an arbitrary truthy object, string or Boolean despite the advertised `HealthPort.check() -> BindingStatus` type annotation. The first resolver blindly used that return as a status and labeled it `BOUND_WITH_CHECK`, which could mislead a consumer about readiness. The candidate now requires an actual `BindingStatus` instance and keeps every non-READY value explicitly non-ready. It also prevents activation on an explicitly `requires_configuration` descriptor if no scoped configuration was supplied. This **does not** validate the completeness or security of nonempty configurations, health probe authenticity, trustworthiness of installed package code, or authorization to call the bound capability. Such checks belong to approved provider contracts and actual domain/security owner ports.

## 5. Runtime and client-visible capability gates

A capable machine/UI caller must distinguish: \`discovered\`, \`compatible\`, \`selected\`, \`activated\`, \`ready\`, \`permitted\`, \`approved_if_effectful\`, \`resource_available\`. The final actor/object/effect authorization belongs to [host security LCD](../security/host-effect-authorization-construction.md); \`BindingStatus.READY\` is provider readiness only, never permission or valid bank methodology.

Neutral capability failures must preserve:

- **Storage:** \`NOT_FOUND\` differs from directory listing denied, backend unavailable, unsupported atomic replace, ambiguous commit and partial bytes. A list error is never a truthful empty collection.
- **Network:** normalization/route policy failure differs from official publisher no-data and HTTP status; no transparent bypass of a mandatory route policy.
- **Credentials:** missing scoped secret is \`UNAVAILABLE\`/\`NEEDS_AUTHORIZATION\`, not a hardcoded fallback, shared log disclosure or a headless interactive password prompt.
- **Style resources:** namespaced contribution collisions and unsupported format features are checked before Artifact construction; passive resources do not grant UI shell or economic-calculation modification.
- **Operation and domain capability:** discovery of a public descriptor does not license arbitrary bank formulas; the actual domain-operation binding and source validity are separately versioned.

**UI posture:** the product renders safe status/diagnosis and, only where policy permits, structured configuration. Do not embed package install/uninstall/upgrade commands in Strategy Box Settings; real installation belongs to the distribution/platform owner. Product-owned Web/Windows/Android forms can render the same safe descriptors differently, without provider-owned arbitrary UI code.

## 6. Source-grounded negative and conformance stubs — UNEXECUTED

~~~python
def test_duplicate_provider_id_fails_not_first_wins(resolver, duplicate_fixture):
    r = resolver.resolve(duplicate_fixture.policy, "file_bytes",
                         required_major=1, configuration={})
    assert r.status is BindingStatus.CONTRACT_FAILURE

def test_selected_required_unavailable_does_not_fallback(resolver, missing_fixture):
    r = resolver.resolve(missing_fixture.policy, "network_route",
                         required_major=1, configuration={})
    assert r.status is BindingStatus.UNAVAILABLE

def test_failed_list_cannot_return_empty_success(faulty_file_provider):
    result = faulty_file_provider.listdir("scope")
    assert result.is_failure and not result.is_successful_empty

def test_api_major_incompatible_rejected(resolver, incompatible_fixture):
    result = resolver.resolve(incompatible_fixture.policy, "file_bytes",
                              required_major=2, configuration={})
    assert result.status is BindingStatus.INCOMPATIBLE

def test_health_truthy_value_cannot_become_ready(resolver, health):
    health.return_value = True
    result = resolver.resolve(policy, "file_bytes",
                              required_major=1, configuration={})
    assert result.status is BindingStatus.CONTRACT_FAILURE

def test_required_scoped_configuration_blocks_empty_activation(resolver, activation):
    result = resolver.resolve(configured_policy, "format_codec",
                              required_major=1, configuration={})
    assert result.status is BindingStatus.CONFIGURATION_REQUIRED
    assert activation.calls == 0

def test_optional_secret_provider_missing_is_noninteractive(headless_runtime):
    result = headless_runtime.resolve_credential("configured_scope")
    assert result.needs_configuration
    assert not headless_runtime.prompted_on_stdin

def test_provider_effect_after_lost_ack_preserves_unknown(external_write_fixture):
    r = external_write_fixture.commit_then_drop_reply()
    assert r.outcome is FailureKind.OUTCOME_UNKNOWN

def test_style_collision_preserves_namespace(style_catalog):
    with raises(ContributionCollision):
        style_catalog.register_two_same_keys_without_namespace()

def test_direct_core_import_without_provider_package(core_import):
    assert core_import.imports_without_optional_extension()
~~~

These are test skeletons, not actual provider certification. The 98 source-proposed vectors in [provider LDD](../../ldd/extensions/neutral-provider-conformance-vectors.md) require declared scope and exact pinned distributions: fake contract checks, clean-wheel provenance and real backend fault-injection are **different evidence grades**. Do not run destructive or secret-recovery tests against real user environments. Production security and conformance require an independent specialist rather than a self-approved verdict.

## 7. Decisions, implementer freedom and readiness

| Design issue | Status / owner |
| --- | --- |
| Independent analytic core and public-neutral capability interface | FIXED Product boundary |
| Metadata-based discovery, duplicate detection, explicit selected singleton slot | LCD_CANDIDATE as design guard, public API naming/major version open |
| Dynamic provider package installation and shell UI override | NOT_APPLICABLE to this seam and outside Strategy Box app ownership |
| Packaging/trust policy, versioned entrypoint, deployment lifecycle and installation | LCD_BLOCKED / platform+security owner |
| Chosen required provider activation/fallback policy and per-capability readiness | LCD_BLOCKED pending accepted Product/operations profile |
| Object permissions, secret scope, config retention, audit/log audience | LCD_BLOCKED / Product/security |
| Resource lifetime, lease, concurrent binding swap and effect reconciliation | LCD_BLOCKED / implementation+operations |
| Private implementation naming, exact backend I/O and helper filenames | DELEGATED_NONMATERIAL where public contracts and tests suffice |
| Actual public contract conformance and installed-wheel tests | UNEXECUTED independent verification |

**Conclusion:** the scoped logical construction is \`LCD_CANDIDATE\`; no general provider management subsystem is certified or authorized for a production patch. An implementer may use the typed ports to prototype a fake resolver only after normal engineering authority, and must obtain real binding/runtime policies before committing integration. No extension-specific private implementation information is needed or provided.
