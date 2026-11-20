"""Choose domain guidance from the actual schema, independently of DB names."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import coal_domain, domain

if TYPE_CHECKING:
    from .schema_catalog import SchemaCatalog


@dataclass(frozen=True)
class DomainProfile:
    name: str
    table_notes: dict[str, str]
    column_notes: dict[str, str]
    synonyms: dict[str, tuple[str, ...]]
    main_tables: dict[str, str]
    defaults: tuple[str, ...]
    rules: str
    glossary: str
    router_rules: str


TNB = DomainProfile(
    "tnb", domain.TABLE_NOTES, domain.COLUMN_NOTES, domain.SYNONYMS, domain.MAIN_TABLES,
    ("tnb_analysis", "tnb_sampling_point", "tnb_sampling_point_group"),
    domain.DOMAIN_RULES, domain.GLOSSARY,
    "- TNB tahlillari, nuqtalari, sexlari va metodikalari uchun tnb_* jadvallarini tanla.\n"
    "- Partiya/batch → tnb_party; method → tnb_methodika; shift → tnb_lab_shift;\n"
    "  workshop → tnb_sampling_point_group. Umumiy modul aniq so'ralsa uning jadvalini tanla.",
)
COAL = DomainProfile(
    "coal", coal_domain.TABLE_NOTES, coal_domain.COLUMN_NOTES, coal_domain.SYNONYMS, {},
    coal_domain.DEFAULT_TABLES, coal_domain.DOMAIN_RULES, coal_domain.GLOSSARY, coal_domain.ROUTER_RULES,
)
GENERIC = DomainProfile(
    "generic", {}, {}, {}, {}, (),
    "Faqat joriy sxema va FK yo'llaridan foydalan. Holat kodlarini taxmin qilma. "
    "Modul yoki bog'lanish noaniq bo'lsa aniqlashtiruvchi savol ber. Sanalar Asia/Tashkent vaqtida.",
    "", "- Jadvalni uning nomi, ta'rifi va savoldagi ma'noga qarab tanla.",
)


def for_catalog(catalog: SchemaCatalog) -> DomainProfile:
    if any(name in catalog.tables for name in ("laboratory_results", "coal_standards", "calculation_acts")):
        return COAL
    analysis = catalog.table("tnb_analysis")
    if analysis and analysis.column("sampling_point_code") and catalog.table("tnb_sampling_point"):
        return TNB
    return GENERIC
