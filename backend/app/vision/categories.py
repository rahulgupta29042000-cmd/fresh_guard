"""Maps a product's category/packaging to a visual-inspection defect group.

Some categories are not visually inspectable in Phase 2 by design — e.g.
plain dairy (non-glass): spoilage/temperature issues aren't a *visible*
defect a camera can assess, and Phase 2 explicitly does not claim to
detect hidden/internal quality problems.
"""

PRODUCE = "produce"
FRAGILE_GLASS = "fragile_glass"
PACKAGED_GOODS = "packaged_goods"
NOT_INSPECTABLE = "not_inspectable"

DEFECT_TYPES_BY_GROUP = {
    PRODUCE: [
        {"type": "bruising", "label": "Bruising"},
        {"type": "cuts", "label": "Cuts"},
        {"type": "rot_discoloration", "label": "Rot / Discoloration"},
        {"type": "deformation", "label": "Deformation"},
    ],
    FRAGILE_GLASS: [
        {"type": "crack", "label": "Crack"},
        {"type": "broken_seal", "label": "Broken Seal"},
        {"type": "leakage", "label": "Leakage"},
        {"type": "packaging_damage", "label": "Packaging Damage"},
    ],
    PACKAGED_GOODS: [
        {"type": "crushed_packaging", "label": "Crushed Packaging"},
        {"type": "broken_seal", "label": "Broken Seal"},
        {"type": "leakage", "label": "Leakage"},
        {"type": "severe_deformation", "label": "Severe Deformation"},
        {"type": "damaged_outer_packaging", "label": "Damaged Outer Packaging"},
    ],
}


def defect_group_for_product(category: str, packaging_type: str) -> str:
    if packaging_type == "glass":
        return FRAGILE_GLASS
    if category == "produce":
        return PRODUCE
    if category == "dairy":
        return NOT_INSPECTABLE
    return PACKAGED_GOODS


def is_inspectable(category: str, packaging_type: str) -> bool:
    return defect_group_for_product(category, packaging_type) != NOT_INSPECTABLE


def defect_types_for_product(category: str, packaging_type: str):
    group = defect_group_for_product(category, packaging_type)
    return DEFECT_TYPES_BY_GROUP.get(group, [])
