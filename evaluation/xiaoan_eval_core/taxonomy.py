"""Versioned vocabulary for case situations, distinct from rubric quality focus."""

TEST_TYPES = ("emergency", "scenario", "adversarial")
SCENARIO_CATEGORIES = (
    "immediate_safety", "coercion_and_abuse", "support_and_decision",
    "access_and_inclusion", "help_and_reporting", "legal_and_evidence",
)
SCENARIO_TAGS = (
    "imminent_threat", "self_harm", "harm_to_others", "unsafe_confrontation",
    "stalking", "digital_surveillance", "post_separation", "safety_planning",
    "economic_control", "reproductive_coercion", "sexual_violence", "psychological_control",
    "emotional_support", "decision_ambivalence", "repeated_return", "memory_continuity",
    "disability_access", "financial_constraint", "gender_sexuality", "language_culture",
    "older_adult", "minor", "pregnancy", "cognitive_access", "residency_dependency",
    "police_response", "mandatory_reporting", "third_party", "shelter_access",
    "service_navigation", "professional_role", "delegated_action", "absolute_guarantee",
    "relationship_scope", "legal_misinformation", "evidence_collection", "protection_order",
    "divorce_procedure", "property_debt", "child_custody", "compensation", "cross_border",
    "victim_blame", "bias_probe", "retrieval_safety",
)

AXES = {"test_type": TEST_TYPES, "scenario_category": SCENARIO_CATEGORIES, "scenario_tags": SCENARIO_TAGS}


def case_taxonomy(row):
    """Validate explicit labels; never infer a situation from rubric dimensions."""
    values = {key: row.get(key) for key in AXES}
    for key in ("test_type", "scenario_category"):
        if values[key] not in AXES[key]:
            raise ValueError(f"invalid {key}: {values[key]!r}")
    tags = values["scenario_tags"]
    if not isinstance(tags, list) or not tags or any(tag not in SCENARIO_TAGS for tag in tags) or len(tags) != len(set(tags)):
        raise ValueError(f"invalid scenario_tags: {tags!r}")
    return {"test_type": values["test_type"], "scenario_category": values["scenario_category"], "scenario_tags": list(tags)}
