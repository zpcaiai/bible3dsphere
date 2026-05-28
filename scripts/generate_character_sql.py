#!/usr/bin/env python3
"""Generate SQL INSERT statements from mirrorData.js for Neon database deployment."""

import json
import re
import os

SQL_ESCAPES = {
    "\\": "\\\\",
    "'": "''",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
}


def escape_sql(value):
    """Escape string for SQL."""
    if value is None:
        return "NULL"
    if not isinstance(value, str):
        value = str(value)
    for old, new in SQL_ESCAPES.items():
        value = value.replace(old, new)
    return f"'{value}'"


def parse_mirror_data():
    """Parse mirrorData.js and return characters and themes."""
    filepath = "emotion-sphere-ui/src/mirrorData.js"

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract MIRROR_CHARACTERS - use more flexible pattern
    chars_match = re.search(r"export const MIRROR_CHARACTERS = (\[[\s\S]*?\]);\s*\n\s*export const MIRROR_THEMES", content)
    if not chars_match:
        # Fallback pattern
        chars_match = re.search(r"export const MIRROR_CHARACTERS = (\[[\s\S]*?\]);", content)
    if not chars_match:
        raise ValueError("Could not find MIRROR_CHARACTERS")

    chars_json = chars_match.group(1)
    # Fix trailing commas before ] or }
    chars_json = re.sub(r",(\s*[}\]])", r"\1", chars_json)

    characters = json.loads(chars_json)

    # Extract MIRROR_THEMES
    themes_match = re.search(r"export const MIRROR_THEMES = (\[[\s\S]*?\]);\s*$", content)
    if not themes_match:
        themes_match = re.search(r"export const MIRROR_THEMES = (\[[\s\S]*?\]);", content)
    if not themes_match:
        raise ValueError("Could not find MIRROR_THEMES")

    themes_json = themes_match.group(1)
    # Fix trailing commas before ] or }
    themes_json = re.sub(r",(\s*[}\]])", r"\1", themes_json)

    themes = json.loads(themes_json)

    return characters, themes


def generate_character_inserts(characters):
    """Generate SQL INSERT statements for characters and related tables."""

    # Main character inserts
    char_lines = [
        "-- Insert biblical characters",
        "INSERT INTO biblical_characters (id, name, name_en, era, role, kingdom, character_type, lesson, summary, witness, scripture_ref, prayer, is_active) VALUES"
    ]

    char_values = []
    for c in characters:
        kingdom = escape_sql(c.get("kingdom"))
        values = (
            c["id"],
            escape_sql(c["name"]),
            escape_sql(c["en"]),
            escape_sql(c["era"]),
            escape_sql(c["role"]),
            kingdom if kingdom != "NULL" else "NULL",
            escape_sql(c["type"]),
            escape_sql(c["lesson"]),
            escape_sql(c["summary"]),
            escape_sql(c["witness"]),
            escape_sql(c["ref"]),
            escape_sql(c["prayer"]),
            "true"
        )
        char_values.append(f"    ({', '.join(str(v) for v in values)})")

    char_lines.append(",\n".join(char_values) + " ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, name_en=EXCLUDED.name_en, era=EXCLUDED.era, role=EXCLUDED.role, kingdom=EXCLUDED.kingdom, character_type=EXCLUDED.character_type, lesson=EXCLUDED.lesson, summary=EXCLUDED.summary, witness=EXCLUDED.witness, scripture_ref=EXCLUDED.scripture_ref, prayer=EXCLUDED.prayer, is_active=EXCLUDED.is_active;")

    # Tag inserts
    tag_lines = ["", "-- Insert character tags", "INSERT INTO character_tags (character_id, tag) VALUES"]
    tag_values = []
    for c in characters:
        for tag in c.get("tags", []):
            tag_values.append(f"    ({c['id']}, {escape_sql(tag)})")
    tag_lines.append(",\n".join(tag_values) + " ON CONFLICT (character_id, tag) DO NOTHING;")

    # Follow points inserts
    follow_lines = ["", "-- Insert follow points", "INSERT INTO character_follow_points (character_id, content, sort_order) VALUES"]
    follow_values = []
    for c in characters:
        for i, item in enumerate(c.get("follow", []), 1):
            follow_values.append(f"    ({c['id']}, {escape_sql(item)}, {i})")
    if follow_values:
        follow_lines.append(",\n".join(follow_values) + ";")
    else:
        follow_lines = ["", "-- No follow points to insert"]

    # Caution points inserts
    caution_lines = ["", "-- Insert caution points", "INSERT INTO character_caution_points (character_id, content, sort_order) VALUES"]
    caution_values = []
    for c in characters:
        for i, item in enumerate(c.get("caution", []), 1):
            caution_values.append(f"    ({c['id']}, {escape_sql(item)}, {i})")
    if caution_values:
        caution_lines.append(",\n".join(caution_values) + ";")
    else:
        caution_lines = ["", "-- No caution points to insert"]

    # Applications inserts
    app_lines = ["", "-- Insert applications", "INSERT INTO character_applications (character_id, content, sort_order) VALUES"]
    app_values = []
    for c in characters:
        for i, item in enumerate(c.get("applications", []), 1):
            app_values.append(f"    ({c['id']}, {escape_sql(item)}, {i})")
    if app_values:
        app_lines.append(",\n".join(app_values) + ";")
    else:
        app_lines = ["", "-- No applications to insert"]

    # Scriptures inserts
    script_lines = ["", "-- Insert scriptures", "INSERT INTO character_scriptures (character_id, reference, sort_order) VALUES"]
    script_values = []
    for c in characters:
        for i, item in enumerate(c.get("scriptures", []), 1):
            script_values.append(f"    ({c['id']}, {escape_sql(item)}, {i})")
    if script_values:
        script_lines.append(",\n".join(script_values) + ";")
    else:
        script_lines = ["", "-- No scriptures to insert"]

    return "\n".join(char_lines + tag_lines + follow_lines + caution_lines + app_lines + script_lines)


def generate_theme_inserts(themes):
    """Generate SQL INSERT statements for themes and mappings."""

    # Theme inserts - include all fields
    theme_lines = [
        "",
        "-- Insert themes",
        "INSERT INTO character_themes (id, name, emoji, scripture, intro, summary, how_to_apply) VALUES"
    ]

    def to_pg_array(arr):
        """Convert Python list to PostgreSQL array literal format."""
        if not arr:
            return "'{}'"
        # Escape special characters in array elements
        escaped = []
        for item in arr:
            # Replace backslashes first, then quotes
            item = str(item).replace("\\", "\\\\").replace('"', '\\"')
            escaped.append(f'"{item}"')
        return "'{" + ", ".join(escaped) + "}'"

    theme_values = []
    for t in themes:
        how_to_apply = to_pg_array(t.get("howToApply", []))
        values = (
            escape_sql(t["id"]),
            escape_sql(t["title"]),
            escape_sql(t.get("emoji", "")),
            escape_sql(t.get("scripture", "")),
            escape_sql(t.get("intro", "")),
            escape_sql(t.get("summary", "")),
            how_to_apply  # PostgreSQL array literal, not escaped
        )
        theme_values.append(f"    ({', '.join(values)})")

    theme_lines.append(",\n".join(theme_values) + " ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, emoji=EXCLUDED.emoji, scripture=EXCLUDED.scripture, intro=EXCLUDED.intro, summary=EXCLUDED.summary, how_to_apply=EXCLUDED.how_to_apply;")

    # Theme mappings
    mapping_lines = ["", "-- Insert theme mappings", "INSERT INTO character_theme_mappings (character_id, theme_id, sort_order) VALUES"]
    mapping_values = []
    for t in themes:
        theme_id = t["id"]
        for i, char_id in enumerate(t.get("characterIds", []), 1):
            mapping_values.append(f"    ({char_id}, {escape_sql(theme_id)}, {i})")

    if mapping_values:
        mapping_lines.append(",\n".join(mapping_values) + " ON CONFLICT DO NOTHING;")
    else:
        mapping_lines = ["", "-- No theme mappings to insert"]

    return "\n".join(theme_lines + mapping_lines)


def main():
    print("Parsing mirrorData.js...")
    characters, themes = parse_mirror_data()
    print(f"Found {len(characters)} characters and {len(themes)} themes")

    # Generate SQL
    char_sql = generate_character_inserts(characters)
    theme_sql = generate_theme_inserts(themes)

    # Read schema file
    with open("backend/biblical_characters_schema.sql", "r", encoding="utf-8") as f:
        schema = f.read()

    # Combine all SQL
    full_sql = f"""-- ============================================================================
-- Biblical Characters Schema + Seed Data for Neon/Vercel Deployment
-- Generated: {__import__('datetime').datetime.now().isoformat()}
-- Characters: {len(characters)} | Themes: {len(themes)}
-- ============================================================================

-- First, ensure we have the UUID extension available in Neon
CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";

{schema}

-- ============================================================================
-- SEED DATA
-- ============================================================================

{char_sql}

{theme_sql}

-- ============================================================================
-- Verify data loaded
-- ============================================================================
SELECT 'Characters loaded: ' || COUNT(*)::text as status FROM biblical_characters;
SELECT 'Tags loaded: ' || COUNT(*)::text as status FROM character_tags;
SELECT 'Follow points loaded: ' || COUNT(*)::text as status FROM character_follow_points;
SELECT 'Caution points loaded: ' || COUNT(*)::text as status FROM character_caution_points;
SELECT 'Applications loaded: ' || COUNT(*)::text as status FROM character_applications;
SELECT 'Scriptures loaded: ' || COUNT(*)::text as status FROM character_scriptures;
SELECT 'Themes loaded: ' || COUNT(*)::text as status FROM character_themes;
SELECT 'Theme mappings loaded: ' || COUNT(*)::text as status FROM character_theme_mappings;
"""

    # Write output
    output_path = "backend/biblical_characters_seed.sql"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_sql)

    print(f"SQL file generated: {output_path}")
    print(f"File size: {len(full_sql)} characters")


if __name__ == "__main__":
    main()
