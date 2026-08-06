-- Require independent theology, pastoral, child-safety, rights and content
-- quality review for every one of the 67 AI Formation content versions.

ALTER TABLE sunday_school_ai_formation_content_reviews
    DROP CONSTRAINT IF EXISTS sunday_school_ai_formation_content_reviews_reviewer_role_check;
ALTER TABLE sunday_school_ai_formation_content_reviews
    ADD CONSTRAINT sunday_school_ai_formation_content_reviews_reviewer_role_check
    CHECK(reviewer_role IN(
        'theology_reviewer','pastoral_reviewer','child_safety_reviewer',
        'rights_reviewer','content_reviewer','accessibility_reviewer','release_reviewer'
    ));

UPDATE sunday_school_ai_formation_content
SET required_reviews_json =
        '["theology_reviewer","pastoral_reviewer","child_safety_reviewer","rights_reviewer","content_reviewer"]'::jsonb
        || CASE WHEN required_reviews_json ? 'accessibility_reviewer'
            THEN '["accessibility_reviewer"]'::jsonb ELSE '[]'::jsonb END
        || CASE WHEN required_reviews_json ? 'release_reviewer'
            THEN '["release_reviewer"]'::jsonb ELSE '[]'::jsonb END,
    review_status = CASE WHEN review_status='approved' THEN 'theology_review' ELSE review_status END,
    retired_at = CASE WHEN published_at IS NOT NULL THEN COALESCE(retired_at,NOW()) ELSE retired_at END,
    published_at = NULL,
    updated_at = NOW();

COMMENT ON COLUMN sunday_school_ai_formation_content.required_reviews_json IS
    'Exact-hash independent human roles; all content requires theology, pastoral, child safety, rights and content quality review.';
