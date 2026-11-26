"""Four actual publication channels and their direct standard-action methods."""
from stratbox.capabilities.model.domains import Applicability, CommandSpec, PublicationSpec
from stratbox.capabilities.model.methods import MethodRef
from .publication_rules import FamilyRule
from ..methods.publications import PublicationRules

RUSSIA_RULES = PublicationRules('rosstat.socioeconomic_russia', 'https://rosstat.gov.ru/compendium/document/50801', frozenset(('pdf',)),
    FamilyRule('rosstat.socioeconomic_russia', 'monthly', 'report', (("таблиц", "tables"), ("table", "tables"), ("историческ", "historical_tables"))), 'report')
RUSSIA = PublicationSpec(id='rosstat.socioeconomic_russia', title='Socioeconomic position of Russia', landing_url='https://rosstat.gov.ru/compendium/document/50801',
    formats=frozenset(('pdf',)), frequency='monthly', settings=RUSSIA_RULES, commands={
        "command.material.identify": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.materials:identify"),
            RUSSIA_RULES, Applicability(source_ids=frozenset({'rosstat.socioeconomic_russia'}))),
        "command.request.prepare": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.publications:request"),
            RUSSIA_RULES, Applicability(source_ids=frozenset({'rosstat.socioeconomic_russia'}))),
        "command.publication.scan": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.publications:scan"),
            RUSSIA_RULES, Applicability(source_ids=frozenset({'rosstat.socioeconomic_russia', 'rosstat.socioeconomic_russia.index'}))),
        "command.issue.select": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.publications:select"),
            RUSSIA_RULES, Applicability(source_ids=frozenset({'rosstat.socioeconomic_russia'}))),
        "command.source.assess": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.publications:assess"),
            RUSSIA_RULES, Applicability(source_ids=frozenset({'rosstat.socioeconomic_russia'}))),
    })

REGIONS_RULES = PublicationRules('rosstat.socioeconomic_regions', 'https://rosstat.gov.ru/folder/11109/document/13259', frozenset(('zip', 'rar')),
    FamilyRule('rosstat.socioeconomic_regions', 'monthly', 'regional_archive', (("историческ", "historical_archive"), ("таблиц", "tables"))), 'regional_archive')
REGIONS = PublicationSpec(id='rosstat.socioeconomic_regions', title='Socioeconomic position of Russian regions', landing_url='https://rosstat.gov.ru/folder/11109/document/13259',
    formats=frozenset(('zip', 'rar')), frequency='monthly', settings=REGIONS_RULES, commands={
        "command.material.identify": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.materials:identify"),
            REGIONS_RULES, Applicability(source_ids=frozenset({'rosstat.socioeconomic_regions'}))),
        "command.request.prepare": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.publications:request"),
            REGIONS_RULES, Applicability(source_ids=frozenset({'rosstat.socioeconomic_regions'}))),
        "command.publication.scan": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.publications:scan"),
            REGIONS_RULES, Applicability(source_ids=frozenset({'rosstat.socioeconomic_regions', 'rosstat.socioeconomic_regions.index'}))),
        "command.issue.select": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.publications:select"),
            REGIONS_RULES, Applicability(source_ids=frozenset({'rosstat.socioeconomic_regions'}))),
        "command.source.assess": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.publications:assess"),
            REGIONS_RULES, Applicability(source_ids=frozenset({'rosstat.socioeconomic_regions'}))),
    })

KEP2_PUBLICATION_RULES = PublicationRules('rosstat.short_term_indicators', 'https://rosstat.gov.ru/compendium/document/50802', frozenset(('xlsx',)),
    FamilyRule('rosstat.short_term_indicators', 'monthly', 'main_workbook', (("историческ", "historical_workbook"), ("архивный", "historical_workbook"), ("таблиц", "tables"))), 'main_workbook')
KEP2_PUBLICATION = PublicationSpec(id='rosstat.short_term_indicators', title='Short-term economic indicators', landing_url='https://rosstat.gov.ru/compendium/document/50802',
    formats=frozenset(('xlsx',)), frequency='monthly', settings=KEP2_PUBLICATION_RULES, commands={
        "command.material.identify": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.materials:identify"),
            KEP2_PUBLICATION_RULES, Applicability(source_ids=frozenset({'rosstat.short_term_indicators'}))),
        "command.request.prepare": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.publications:request"),
            KEP2_PUBLICATION_RULES, Applicability(source_ids=frozenset({'rosstat.short_term_indicators'}))),
        "command.publication.scan": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.publications:scan"),
            KEP2_PUBLICATION_RULES, Applicability(source_ids=frozenset({'rosstat.short_term_indicators', 'rosstat.short_term_indicators.index'}))),
        "command.issue.select": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.publications:select"),
            KEP2_PUBLICATION_RULES, Applicability(source_ids=frozenset({'rosstat.short_term_indicators'}))),
        "command.source.assess": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.publications:assess"),
            KEP2_PUBLICATION_RULES, Applicability(source_ids=frozenset({'rosstat.short_term_indicators'}))),
    })

POPULATION_PUBLICATION_RULES = PublicationRules('rosstat.population_municipalities', 'https://rosstat.gov.ru/compendium/document/13282', frozenset(('xlsx',)),
    FamilyRule('rosstat.population_municipalities', 'annual', 'population_workbook', (("историческ", "historical_workbook"), ("таблиц", "tables"))), 'population_workbook')
POPULATION_PUBLICATION = PublicationSpec(id='rosstat.population_municipalities', title='Municipal population', landing_url='https://rosstat.gov.ru/compendium/document/13282',
    formats=frozenset(('xlsx',)), frequency='annual', settings=POPULATION_PUBLICATION_RULES, commands={
        "command.material.identify": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.materials:identify"),
            POPULATION_PUBLICATION_RULES, Applicability(source_ids=frozenset({'rosstat.population_municipalities'}))),
        "command.request.prepare": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.publications:request"),
            POPULATION_PUBLICATION_RULES, Applicability(source_ids=frozenset({'rosstat.population_municipalities'}))),
        "command.publication.scan": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.publications:scan"),
            POPULATION_PUBLICATION_RULES, Applicability(source_ids=frozenset({'rosstat.population_municipalities', 'rosstat.population_municipalities.index'}))),
        "command.issue.select": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.publications:select"),
            POPULATION_PUBLICATION_RULES, Applicability(source_ids=frozenset({'rosstat.population_municipalities'}))),
        "command.source.assess": CommandSpec(MethodRef("stratbox.domains.rosstat.methods.publications:assess"),
            POPULATION_PUBLICATION_RULES, Applicability(source_ids=frozenset({'rosstat.population_municipalities'}))),
    })

