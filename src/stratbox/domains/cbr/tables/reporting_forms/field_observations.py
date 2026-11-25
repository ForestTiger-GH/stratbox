"""Explicit numeric-field interpretation for every admitted reporting-form DBF.

A field binding supplies the economic definition, unit and period. Published
names, record coordinates and literal numeric tokens remain source evidence.
The method does not invent financial models for a form without a reviewed one.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fnmatch import fnmatchcase
from types import MappingProxyType

from stratbox.capabilities.model import declaration_fingerprint
from stratbox.shared.data.observations import MetricRef, Observation, ObservationBatch, PeriodRef, SubjectRef
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from .flakes import validate_flakes


@dataclass(frozen=True, slots=True)
class FormFieldBinding:
    member_pattern: str
    field: str
    subject_field: str
    metric: MetricRef
    period: PeriodRef
    row_fields: tuple[str, ...] = ()
    perimeter: str = 'reported_form_records'
    subject_namespace: str = 'cbr.reporting_forms.source_subject'
    edition: str = 'caller-reviewed.v1'

    def __post_init__(self):
        if (not all(isinstance(item, str) and item for item in
                (self.member_pattern, self.field, self.subject_field, self.perimeter,
                 self.subject_namespace, self.edition))
                or not isinstance(self.metric, MetricRef) or not isinstance(self.period, PeriodRef)
                or not isinstance(self.row_fields, tuple) or len(set(self.row_fields)) != len(self.row_fields)
                or any(not isinstance(field, str) or not field for field in self.row_fields)):
            raise ValueError('cbr.forms.field_binding_invalid')


def extract_fields(flakes, bindings, *, include_deleted=False, checkpoint=None, budget=None):
    """Interpret explicit numeric fields without dropping unselected physical data."""
    validate_flakes(flakes)
    if (not isinstance(bindings, tuple) or not bindings
            or any(not isinstance(binding, FormFieldBinding) for binding in bindings)
            or type(include_deleted) is not bool):
        raise ValueError('cbr.forms.field_bindings_required')
    if not flakes.complete:
        raise ValueError('cbr.forms.flakes_incomplete')
    rows, keys = [], set()
    for binding in bindings:
        matched = [member for member in flakes.members if member.table is not None
            and fnmatchcase(member.name.casefold(), binding.member_pattern.casefold())]
        if not matched:
            raise ValueError('cbr.forms.binding_member_missing')
        for member in matched:
            positions = {field.name: index for index, field in enumerate(member.table.fields)}
            if not {binding.field, binding.subject_field, *binding.row_fields} <= positions.keys():
                raise ValueError('cbr.forms.binding_field_missing')
            descriptor = member.table.fields[positions[binding.field]]
            if descriptor.field_type not in {'N', 'F'}:
                raise ValueError('cbr.forms.binding_field_not_numeric')
            for record in member.table.records:
                if checkpoint is not None:
                    checkpoint()
                if record.deleted and not include_deleted:
                    continue
                raw = record.values[positions[binding.field]]
                text = raw.strip()
                if not text:
                    status, value = 'blank', None
                elif text in {'-', '–', '—'}:
                    status, value = 'dash', None
                elif text in {'...', '…', '*'}:
                    status, value = 'withheld', None
                else:
                    try:
                        value = Decimal(text)
                    except InvalidOperation:
                        raise ValueError('cbr.forms.binding_numeric_token_invalid') from None
                    if not value.is_finite():
                        raise ValueError('cbr.forms.binding_numeric_token_invalid')
                    status = 'reported'
                subject = record.values[positions[binding.subject_field]]
                if not subject.strip():
                    raise ValueError('cbr.forms.binding_subject_missing')
                dimensions = (('source_member', member.name), ('source_record', str(record.ordinal)),
                    ('source_field', binding.field), ('source_deleted', str(record.deleted).lower()),
                    *((field, record.values[positions[field]]) for field in binding.row_fields))
                key = (subject, binding.metric, binding.period, dimensions, binding.perimeter)
                if key in keys:
                    raise ValueError('cbr.forms.binding_duplicate_observation')
                keys.add(key)
                rows.append(Observation(SubjectRef(binding.subject_namespace, subject), binding.metric,
                    binding.period, dimensions, binding.perimeter, value, status,
                    f'{member.identity.sha256}:{record.ordinal}:{binding.field}', raw))
    if budget is not None:
        budget.check('cells', len(rows))
    if not rows:
        raise ValueError('cbr.forms.binding_no_records')
    profile = declaration_fingerprint(bindings)
    source_id = 'cbr.reporting_forms.f' + flakes.key.code
    use = SourceUse(SourceCoordinate(source_id, 'cbr.reporting_forms', 'numeric_fields',
        flakes.key.as_of.isoformat(), material_identity=flakes.original_identity,
        layout_edition=flakes.method_version, semantic_profile_edition=profile),
        'form_flakes', 'explicit_field_bindings')
    return ObservationBatch(source_id + '.fields', 1, flakes.key.as_of.isoformat(), tuple(rows),
        flakes.lineage, (use,))


PUBLISHED_FIELD_PROFILES = {
    'cbr.forms.134.fields.20120801': {
        'form': '134', 'member_pattern': '*134d.dbf', 'subject': 'REGN', 'rows': ('C1',),
        'measures': ('C3',), 'kind': 'stock',
        'source_url': 'https://cbr.ru/vfs/credit/formats/f134-20120801.pdf',
        'fields': (('REGN', 'N', 4), ('C1', 'C', 15), ('C3', 'N', 16)),
    },
    'cbr.forms.803.fields.20230701': {
        'form': '803', 'member_pattern': '*pk803????.dbf', 'subject': 'REGN_GKO',
        'rows': ('RAZDEL', 'STR'), 'measures': ('KORR_P', 'KORR_M', 'VSEGO'), 'kind': 'flow',
        'source_url': 'https://www.cbr.ru/vfs/credit/formats/f803-20230701.pdf',
        'fields': (('REGN_GKO', 'N', 4), ('RAZDEL', 'C', 3), ('STR', 'C', 5),
            ('KORR_P', 'N', 16), ('KORR_M', 'N', 16), ('VSEGO', 'N', 16)),
    },
}

PUBLISHED_FIELD_PROFILES = MappingProxyType({key: MappingProxyType(value) for key, value in PUBLISHED_FIELD_PROFILES.items()})


def published_bindings(flakes, profile_id, *, unit, scale, period):
    """Bind reviewed physical fields to an explicit unit, scale and period.

    The publisher's DBF format describes field geometry; monetary units and
    reporting intervals remain explicit input from the publication's basis.
    """
    validate_flakes(flakes)
    if profile_id not in PUBLISHED_FIELD_PROFILES:
        raise ValueError('cbr.forms.published_field_profile_unknown')
    profile = PUBLISHED_FIELD_PROFILES[profile_id]
    if flakes.key.code != profile['form']:
        raise ValueError('cbr.forms.published_field_profile_mismatch')
    if (not isinstance(period, PeriodRef) or not isinstance(unit, str) or not unit
            or type(scale) is not Decimal or not scale.is_finite() or scale <= 0):
        raise ValueError('cbr.forms.published_field_basis_required')
    if profile['kind'] == 'stock' and (period.kind != 'as_of' or period.as_of != flakes.key.as_of):
        raise ValueError('cbr.forms.published_field_stock_date_mismatch')
    if profile['kind'] == 'flow' and (period.kind != 'interval' or period.end >= flakes.key.as_of):
        raise ValueError('cbr.forms.published_field_flow_interval_required')
    matches = tuple(member for member in flakes.members if member.table is not None
        and fnmatchcase(member.name.casefold(), profile['member_pattern']))
    if len(matches) != 1:
        raise ValueError('cbr.forms.published_field_member_ambiguous')
    member = matches[0]
    fields = {field.name: (field.field_type, field.length) for field in member.table.fields}
    if any(fields.get(name) != (kind, width) for name, kind, width in profile['fields']):
        raise ValueError('cbr.forms.published_field_layout_unsupported')
    return tuple(FormFieldBinding(member.name, field, profile['subject'],
        MetricRef(f'cbr.forms.f{flakes.key.code}.{field.lower()}', unit, profile['kind'], profile_id, scale),
        period, profile['rows'], 'banking_group' if flakes.key.code == '803' else 'credit_institution',
        'cbr.banking_group.registration' if flakes.key.code == '803' else 'cbr.credit_institution.registration',
        profile_id) for field in profile['measures'])
