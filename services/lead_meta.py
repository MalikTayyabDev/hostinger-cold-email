"""Lead field helpers — work with or without opener_angle DB column."""
from database.db import column_exists_cached

ANGLE_TAG_PREFIX = "angle:"


def normalize_opener_angle(value):
    return (value or "auto").strip().lower() or "auto"


def encode_angle_in_tags(angle, tags=""):
    angle = normalize_opener_angle(angle)
    parts = [
        p.strip()
        for p in (tags or "").split(",")
        if p.strip() and not p.strip().startswith(ANGLE_TAG_PREFIX)
    ]
    if angle != "auto":
        parts.insert(0, f"{ANGLE_TAG_PREFIX}{angle}")
    return ",".join(parts)


def opener_angle_from_row(row):
    if row is None:
        return "auto"
    keys = row.keys()
    if "opener_angle" in keys and row["opener_angle"]:
        return normalize_opener_angle(row["opener_angle"])
    tags = row["tags"] if "tags" in keys else ""
    for part in (tags or "").split(","):
        part = part.strip()
        if part.startswith(ANGLE_TAG_PREFIX):
            return normalize_opener_angle(part[len(ANGLE_TAG_PREFIX) :])
    return "auto"


def lead_has_opener_angle_column(con):
    return column_exists_cached(con, "leads", "opener_angle")


def campaign_has_signature_column(con):
    return column_exists_cached(con, "campaigns", "signature_id")
