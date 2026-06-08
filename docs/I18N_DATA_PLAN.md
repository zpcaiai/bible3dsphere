# 业务数据彻底国际化 —— 方案与改动清单

> 目标：英文模式下，连**数据库/内置业务数据**也显示英文（界面静态文案已由前端 `t()` 覆盖）。
> 结论：**不**对全部表加 `lang` 字段 + 双行存储（对 UGC 是反模式，破坏外键/计数/作者归属）。
> 采用**分类处理**：参考/种子内容走「并列双列 `_zh/_en` + 回填」；UGC 走「单列 `lang` 标记 + 按需翻译」。

---

## 1. 全表分类（依据 47 个迁移实际表结构）

### A. 参考/种子内容 —— 双列 `_zh/_en`，缺英文则回填（一次性翻译）
这些是平台内置、所有用户共享、英文用户会直接看到的内容。

| 表 / 数据源 | 现状 | 待办 |
|---|---|---|
| `geo_entities` / `entity_names` / `geo_events` / `geo_relations` / `historical_routes` / `scripture_geo_mappings`（圣经地理 0007–0017） | 已有 `name_zh/name_en` 等双列，前端 `bibleGeoSource.js` 已按 `name_en` 取值 | 抽查回填缺失 `name_en`/`*_en` |
| `bible_territories` / `bible_events` / `bible_prophecies` / `bible_campaigns`（圣经地图集 0039） | 名称类有 `name`(英)/`name_zh`、`title/title_zh`、`commander/commander_zh`，但 **`description` 仅中文** | 加 `description_en`，回填；前端按语言取 |
| `seekers_class_courses`（慕道班 0023） | `title/scripture/description` **全单列中文** | 加 `title_en/scripture_en/description_en`，回填 |
| 前端内置参考数据 `src/data/*.js`（`bibleGazetteer`、`bibleJourneys`、`bibleMapsData`、`characterJourneys`、`exodusStations`、`jerusalemChronology`、`jerusalemEras`、`kingsTimeline`） | 多为中文字段 | 补 `_en` 字段或并入翻译表；前端按语言取 |
| 前端 assets `mirror_characters.json`（镜鉴 231 人）、`hymns.json`（诗歌）、`books.json`（书目） | 中文为主 | 补 `_en` 字段，回填 |

### B. 用户生成内容 UGC —— 单列 `lang` 标记（不双行、不预存翻译）
用户用一种语言写的，加 `lang text DEFAULT 'zh'` 记录写作语言，跨语言查看用「翻译」按钮按需机翻。

`chat_messages`、`guardian_messages`、`guardian_memories`、`guardian_devotion_entries`、`guardian_prayer_entries`、
`guardian_spiritual_checkins`、`community_posts`、`community_comments`、`examen_entries`、`gratitude_entries`、
`memory_verses`、`waiting_cases/practices/reflections`、`attachment_*`、`accountability_*`、`book_marks`、
`habit_daily_notes`、`pilgrim_visits`、`user_verse_feedback`、`reading_plan_*`、`voice_groups`(群名)、`churches`(教会名)。

### C. AI 生成内容 —— 生成时按用户当前语言产出（推荐），或存一份 + 按需翻译
`gospel_diagnoses`、`daily_dew`、`spiritual_checkups`、`decision_discernments`、`disciple_assessments`、
`guardian_messages`(AI 回复部分)。引擎入口接收 `lang` 参数，按语言生成 prompt/输出。

### D. 无需翻译（基础设施）
`schema_migrations`、`domain_events`、`agent_runs`、`artifact_manifests`、`mvfe_pipeline_stats`、
`retrieval_eval_runs`、`route_cache`、`push_subscriptions`、`admin_audit_log`、几何/坐标列、各种 id/枚举/时间戳。

---

## 2. 数据库改动清单

### 2.1 参考表补 `_en` 列（迁移 0048）
```sql
-- migrations/0048_i18n_reference_en.sql
ALTER TABLE bible_territories   ADD COLUMN IF NOT EXISTS description_en text;
ALTER TABLE bible_events        ADD COLUMN IF NOT EXISTS description_en text;
ALTER TABLE bible_prophecies    ADD COLUMN IF NOT EXISTS description_en text;
ALTER TABLE seekers_class_courses ADD COLUMN IF NOT EXISTS title_en       text DEFAULT '';
ALTER TABLE seekers_class_courses ADD COLUMN IF NOT EXISTS scripture_en   text DEFAULT '';
ALTER TABLE seekers_class_courses ADD COLUMN IF NOT EXISTS description_en text DEFAULT '';
-- geo 系列抽查后按需补（多数已具 _en）
```
> 注意：`bible_*` 的英文名已存在裸 `name`/`title` 列；中文在 `*_zh`。前端取值规则见 §4。

### 2.2 UGC 表加 `lang` 标记（迁移 0049，全部幂等）
```sql
-- migrations/0049_i18n_ugc_lang.sql
ALTER TABLE chat_messages       ADD COLUMN IF NOT EXISTS lang text DEFAULT 'zh';
ALTER TABLE guardian_messages   ADD COLUMN IF NOT EXISTS lang text DEFAULT 'zh';
ALTER TABLE community_posts      ADD COLUMN IF NOT EXISTS lang text DEFAULT 'zh';
ALTER TABLE community_comments   ADD COLUMN IF NOT EXISTS lang text DEFAULT 'zh';
ALTER TABLE examen_entries       ADD COLUMN IF NOT EXISTS lang text DEFAULT 'zh';
ALTER TABLE gratitude_entries    ADD COLUMN IF NOT EXISTS lang text DEFAULT 'zh';
-- …其余 UGC 表同样模式（清单见 §1.B）
```
- 写入路径：相关 POST 端点把当前请求语言（前端传 `X-Lang` 头或 body `lang`）写入该列；缺省 `zh`。
- 不改任何外键、不复制行、不影响点赞/评论/计数。

### 2.3 一次性回填脚本（机翻 zh→en，仅参考表）
```
backend/scripts/i18n_backfill.py
- 读 settings 里的 GEMINI/DEEPSEEK/SILICONFLOW key（已配）
- 对 §A 各表 _zh / 单中文列，批量翻译写入对应 _en（空值才译，可重复运行）
- 速率限制 + 失败重试 + 进度日志；译完人工抽检关键术语（圣经专名用受控词表）
```
> 圣经专名（人名/地名/书卷名）建议先建一张 `term_glossary(zh,en)` 受控词表，喂给翻译模型保证一致（如「以法莲→Ephraim」）。

---

## 3. 后端接口改动

- **读接口**：参考内容接口（geo / bible-map / seekers-class / layout）在返回里**同时给出 `_zh` 和 `_en`**（已大多如此），由前端按语言选；不在后端按 header 裁剪，便于前端切换语言无需重新请求 + 利于缓存。
- **UGC 写接口**：接收并存 `lang`（前端在 axios/fetch 默认头注入 `X-Lang: zh|en`）。
- **翻译接口（新增）**：`POST /api/translate { text, target }` → 调已配的模型翻译，结果**带缓存**（`route_cache` 同款或 `translations_cache(hash,target,text)` 表），供 UGC「翻译」按钮按需调用，避免重复机翻。
- **AI 引擎**：入口加 `lang` 参数，按语言选 system prompt 与输出语言。

---

## 4. 前端改动

### 4.1 统一取值助手
```js
// src/i18n/pickLang.js
import { getRuntimeLang } from './runtime'
// 优先英文列，空则回退中文列；兼容 (base+'_en' / base+'_zh') 与 (base / base+'_zh') 两种命名
export function pick(row, base) {
  if (!row) return ''
  const en = row[`${base}_en`] ?? row[base]      // bible_* 英文在裸列
  const zh = row[`${base}_zh`] ?? row[base]
  return getRuntimeLang() === 'en' ? (en || zh || '') : (zh || en || '')
}
```
- 把读取 DB/内置参考内容的组件（圣经地图、地图集、慕道班、镜鉴、诗歌、书库等）的 `row.name_zh` 等改为 `pick(row,'name')`。

### 4.2 内置参考 JS/JSON 数据补 `_en`
`src/data/*.js`、`mirror_characters.json`、`hymns.json`、`books.json` 增加 `_en` 字段（脚本批量翻译生成），组件用 `pick()` 取。

### 4.3 UGC「翻译」按钮
聊天/社区/群聊消息气泡下，当 `msg.lang !== 当前语言` 时显示「翻译」按钮 → 调 `/api/translate` → 行内展示译文（前端内存缓存）。原文不变、不入库。

### 4.4 写入带语言
统一在 api 层给所有 POST 注入 `X-Lang: getRuntimeLang()`。

---

## 5. 分阶段实施（按性价比，可逐段上线）

- **阶段 1（最高价值，纯增量）**：参考内容双语
  - 0048 迁移 + 回填脚本 + 受控词表；前端 `pick()` + 内置 JS/JSON 补 `_en`。
  - 效果：英文用户在圣经地图/地图集/慕道班/镜鉴/诗歌/书库看到英文。**不碰 UGC，零破坏风险。**
- **阶段 2**：UGC `lang` 标记 + 写入注入 + `/api/translate` + 翻译按钮（0049 迁移）。
- **阶段 3**：AI 引擎按 `lang` 生成。

每阶段独立可回滚（加列幂等、回填空值才写、前端 `pick` 回退中文）。

---

## 6. 取舍说明

- 不用「lang 行 + 双份」：UGC 无第二语言原文，机翻私人属灵文字失真；且每个外键/点赞/计数都要 dedup，迁移 47 表风险极高。
- 参考内容用双列而非翻译表：本项目已有 253 处 `name_zh`/107 处 `name_en` 的既定双列约定，沿用一致、查询简单。
- 若将来语言 >2 种，再考虑把 `_zh/_en` 收敛为 `entity_translations(entity_id, field, lang, value)` 翻译表（当前两语言不必要）。
