-- 0235 — 修正 emd_erasure_coverage() 的统计口径。
--
-- 0233 里的这个函数把「所有 formation_twin_emd_* 表」当分母，却只把
-- personal_email_tables() 里的表算作已覆盖。共享题库 / 题目 / 指标目录这三张表
-- 按设计就没有任何个人标识列（它们是所有人共用的参考数据，删掉会毁掉全体用户的内容），
-- 因此永远进不了 personal_email_tables()，也就永远无法「被覆盖」——
-- 换句话说 `uncovered = []` 在结构上不可能成立，这个自检从上线起就一直是红的。
--
-- 正确口径在同一批次的离线孪生测试里其实早就写明了
-- （tests/test_emd_erasure_schema_verification.py::test_every_emd_table_is_covered：
--  「共享题库/指标目录本就无 email 列，属于预期之外」），只是没同步到 SQL 侧。
--
-- 这里把口径改成：**每一张 EMD 表，要么被擦除覆盖，要么可证明不含个人数据。**
--   · 分母  = 带个人标识列（email / user_id / profile_id）的 EMD 表
--   · 分子  = 真正会被 erase_user_data walk 到的表
--   · 豁免  = 零个人标识列的表，单独作为一列返回，不藏起来
--
-- 口径收紧了而不是放松：profile_id 也算个人标识，所以将来若有人加一张只按
-- profile_id 建的 EMD 表，它会立刻落进 uncovered 而不是悄悄溜过去。
-- 豁免名单一律从 information_schema 实时推导，绝不硬编码数组——0145 的教训就在这里，
-- 0233 自己的测试也明令禁止 `ARRAY[...]` 快照。

CREATE OR REPLACE FUNCTION emd_personal_identifier_columns()
RETURNS TABLE(column_name text) AS $$
    SELECT unnest(ARRAY['email', 'user_id', 'profile_id']::text[]);
$$ LANGUAGE sql IMMUTABLE;

COMMENT ON FUNCTION emd_personal_identifier_columns() IS
    'Columns that make an EMD table personal data. A table with none of these is shared reference data.';

-- 刻意保持 0233 的三列签名不变：改签名就得先 DROP，而同一个库里任何一处重跑 0233
-- 的 CREATE OR REPLACE 都会撞上「Row type defined by OUT parameters is different」。
-- 豁免清单改由下面的独立函数暴露，既看得见，又不牵动既有签名。
CREATE OR REPLACE FUNCTION emd_erasure_coverage()
RETURNS TABLE(
    total_emd_tables bigint,
    covered bigint,
    uncovered text[]
) AS $$
    WITH emd AS (
        SELECT t.table_name::text AS name
        FROM information_schema.tables t
        WHERE t.table_schema = 'public'
          AND t.table_type = 'BASE TABLE'
          AND t.table_name::text LIKE 'formation_twin_emd\_%'
    ),
    -- 零个人标识列 = 共享参考数据，本就不在擦除范围内
    shared AS (
        SELECT e.name FROM emd e
        WHERE NOT EXISTS (
            SELECT 1
            FROM information_schema.columns c
            WHERE c.table_schema = 'public'
              AND c.table_name = e.name
              AND c.column_name IN (SELECT p.column_name FROM emd_personal_identifier_columns() p)
        )
    ),
    in_scope AS (
        SELECT e.name FROM emd e WHERE e.name NOT IN (SELECT s.name FROM shared s)
    ),
    covered AS (
        SELECT i.name FROM in_scope i
        WHERE i.name IN (SELECT p.table_name FROM personal_email_tables() p)
           OR i.name IN (SELECT u.table_name FROM personal_userid_tables() u)
    )
    SELECT
        (SELECT count(*) FROM in_scope),
        (SELECT count(*) FROM covered),
        COALESCE(ARRAY(SELECT i.name FROM in_scope i
                       WHERE i.name NOT IN (SELECT c.name FROM covered c) ORDER BY 1), ARRAY[]::text[]);
$$ LANGUAGE sql STABLE;

COMMENT ON FUNCTION emd_erasure_coverage() IS
    'EMD pilot acceptance: uncovered must be empty and covered must equal total_emd_tables. '
    'total counts only EMD tables carrying a personal identifier (email/user_id/profile_id); '
    'zero-identifier shared catalogs are listed by emd_erasure_excluded_tables().';

-- 豁免不能是隐形的：审计时必须能一眼看到「哪些 EMD 表被判定为不含个人数据」，
-- 并与 Python 侧的 EMD_SHARED_CATALOG_TABLES 逐一对账。
CREATE OR REPLACE FUNCTION emd_erasure_excluded_tables()
RETURNS TABLE(table_name text) AS $$
    SELECT t.table_name::text
    FROM information_schema.tables t
    WHERE t.table_schema = 'public'
      AND t.table_type = 'BASE TABLE'
      AND t.table_name::text LIKE 'formation_twin_emd\_%'
      AND NOT EXISTS (
          SELECT 1
          FROM information_schema.columns c
          WHERE c.table_schema = 'public'
            AND c.table_name = t.table_name
            AND c.column_name IN (SELECT p.column_name FROM emd_personal_identifier_columns() p)
      )
    ORDER BY 1;
$$ LANGUAGE sql STABLE;

COMMENT ON FUNCTION emd_erasure_excluded_tables() IS
    'EMD tables with no personal identifier column — shared reference data, out of erasure scope by construction.';
