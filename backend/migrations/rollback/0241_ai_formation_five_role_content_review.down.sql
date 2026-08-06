-- Restore the original Batch-specific review-role policy. This does not
-- recreate any publication invalidated by the forward migration.

UPDATE sunday_school_ai_formation_content
SET required_reviews_json = CASE
    WHEN batch_id='04' THEN '["theology_reviewer","pastoral_reviewer","child_safety_reviewer","rights_reviewer"]'::jsonb
    WHEN batch_id IN ('07','08','10') THEN '["theology_reviewer","pastoral_reviewer","child_safety_reviewer","accessibility_reviewer"]'::jsonb
    WHEN batch_id='09' THEN '["theology_reviewer","pastoral_reviewer","rights_reviewer","accessibility_reviewer"]'::jsonb
    WHEN batch_id='12' THEN '["theology_reviewer","pastoral_reviewer","child_safety_reviewer","rights_reviewer","accessibility_reviewer","release_reviewer"]'::jsonb
    ELSE '["theology_reviewer","pastoral_reviewer"]'::jsonb
END,
updated_at=NOW();

ALTER TABLE sunday_school_ai_formation_content_reviews
    DROP CONSTRAINT IF EXISTS sunday_school_ai_formation_content_reviews_reviewer_role_check;
ALTER TABLE sunday_school_ai_formation_content_reviews
    ADD CONSTRAINT sunday_school_ai_formation_content_reviews_reviewer_role_check
    CHECK(reviewer_role IN(
        'theology_reviewer','pastoral_reviewer','child_safety_reviewer',
        'rights_reviewer','accessibility_reviewer','release_reviewer'
    ));

COMMENT ON COLUMN sunday_school_ai_formation_content.required_reviews_json IS NULL;
