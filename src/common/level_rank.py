"""
Computes the level_rank integer for a class's education level targeting.
Rank table (ascending):
  primary-1=1, primary-2=2, primary-3=3, primary-4=4, primary-5=5,
  middle-1=6, middle-2=7, middle-3=8, middle-4=9,
  high-1=10, high-2=11, high-3=12,
  university=13
Returns None if level_scope is 'age_range' or 'all_levels'.
"""

_RANK_MAP: dict[str, int] = {
    "primary-1": 1, "primary-2": 2, "primary-3": 3, "primary-4": 4, "primary-5": 5,
    "middle-1": 6, "middle-2": 7, "middle-3": 8, "middle-4": 9,
    "high-1": 10, "high-2": 11, "high-3": 12,
    "university": 13,
}


def compute_level_rank(
    level_scope: str,
    education_stage: str,
    education_year: int | None,
) -> int | None:
    if level_scope in ("age_range", "all_levels"):
        return None
    if education_stage == "university":
        return _RANK_MAP.get("university")
    if education_stage == "all":
        return None
    if education_year is None:
        return None
    key = f"{education_stage}-{education_year}"
    return _RANK_MAP.get(key)


def validate_level_targeting(
    level_scope: str,
    education_stage: str,
    education_year: int | None,
    min_age: int | None,
    max_age: int | None,
) -> list[dict]:
    """
    Returns a list of field-level error dicts (empty = valid).
    Mirrors frontend Zod validation for server-side enforcement.
    """
    errors = []

    if level_scope == "age_range":
        if min_age is None and max_age is None:
            errors.append({
                "field": "minAge",
                "message": "At least one of minAge or maxAge is required for age_range scope."
            })
        if min_age is not None and max_age is not None and max_age < min_age:
            errors.append({"field": "maxAge", "message": "maxAge must be >= minAge."})

    elif level_scope in ("specific", "stage_and_above"):
        if not education_stage or education_stage == "all":
            errors.append({
                "field": "educationStage",
                "message": "educationStage is required for this levelScope."
            })
        elif education_stage in ("primary", "middle", "high") and not education_year:
            errors.append({
                "field": "educationYear",
                "message": "educationYear is required for this stage."
            })

    return errors
