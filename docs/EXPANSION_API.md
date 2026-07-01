# 内容与神学扩充 · API 调用文档（12 模块，供前端直接对接）

> 后端已上线于本仓库（迁移 0130–0141，聚合器 `routers/expansion_pack.py`，在 `main.py` 末尾注册）。
> 前端可直接 `import { ... } from './expansion/expansionEndpoints'`（已备好，50 个导出），或按本表自行封装。

## 通用约定
- **Base**：`/api`（同 `src/api.js` 的 `API_BASE`）。
- **鉴权**：`Authorization: Bearer <token>`，`token` 取自 `src/auth.js` 的 `getToken()`。`/meta`、`/resources/books|hymns` 可匿名。
- **每个模块 4 端点**：`GET /<prefix>/meta`（框架/量表）· `POST /<prefix>/<action>`（主操作）· `GET /<prefix>/history?limit=`（历史）· `GET /<prefix>/latest`（最近一次）。
- **POST 返回**：`{ ok:true, ...引擎结果 }`。文本类模块结果含 `crisis`(bool) 与 `crisis_note`（命中自伤词时的温柔求助提示，务必优先展示）。formation 事件由后端自动回流，无需前端处理。
- **请求体**统一可带 `use_ai:true`（默认走确定性，配置了 LLM 才增强；失败自动回退）。

## 12 模块一览
| # | 模块 | prefix | 主 POST | 请求体 | 备好的调用 |
|---|---|---|---|---|---|
| 1 | 哀歌(Vroegop) | `lament` | `/lament/compose` | `{text, situation?}` | `lamentCompose(text, situation, token)` |
| 2 | 情感真伪辨(爱德华兹) | `affections` | `/affections/assess` | `{ratings:{key:0..1}, text?}` | `affectionsAssess(ratings, text, token)` |
| 3 | 失序之爱重排(奥古斯丁) | `ordo` | `/ordo/analyze` | `{loves:[], text?}` | `ordoAnalyze(loves, text, token)` |
| 4 | 温柔谦卑(Ortlund) | `tender` | `/tender/comfort` | `{text}` | `tenderComfort(text, token)` |
| 5 | 文化礼仪→反礼仪(Smith) | `liturgy` | `/liturgy/analyze` | `{habit}` | `liturgyAnalyze(habit, token)` |
| 6 | 诸灵分辨 安慰/枯竭(依纳爵) | `spirits` | `/spirits/discern` | `{text}` | `spiritsDiscern(text, token)` |
| 7 | 与基督联合 | `union` | `/union/assess` | `{struggle}` | `unionAssess(struggle, token)` |
| 8 | 以神为乐(派博) | `delight` | `/delight/reframe` | `{duty}` | `delightReframe(duty, token)` |
| 9 | 情感健康属灵(Scazzero) | `eh` | `/eh/assess` | `{ratings:{key:0..1}, text?}` | `ehAssess(ratings, text, token)` |
| 10 | 基督徒知足(伯罗斯) | `contentment` | `/contentment/analyze` | `{lack}` | `contentmentAnalyze(lack, token)` |
| 11 | 认识神·属性默想(巴刻/陶恕) | `knowgod` | `/knowgod/meditate` | `{need?, attribute?}` | `knowgodMeditate({need,attribute}, token)` |
| 12 | 推荐书目/圣诗 | `resources` | — | — | `resourceBooks(continent?, token)` / `resourceHymns(token)` |
| 13 | 心意更新(魏乐德 VIM) | `renovation` | `/renovation/assess` | `{ratings:{key:0..1}, text?}` | `renovationAssess(ratings, text, token)` |
| 14 | 华人本土灵修 | `chinese` | `/chinese/meditate` | `{need}`（另 `GET /chinese/search?q=`） | `chineseMeditate(need, token)` / `chineseSearch(q, author, token)` |

> **ratings 的 key 从 `/meta` 拿**：affections → `meta.true_signs[].key`；eh / renovation → `meta.dimensions[].key`。
> **knowgod**：可传 `need`（自由文本，自动匹配属性）或 `attribute`（属性 key，取自 `meta.attributes[].key`）。

## ⚠️ 命名须知
`ordo` 前缀是 **/api/ordo**（本批次奥古斯丁「失序之爱→重排」引擎，表 `ordo_amoris_entries`）。
它与既有 **/api/ordo-amoris**（爱之秩序星图，表 `ordo_amoris_records`）是两套，勿混。

## 资源端点
| 端点 | 说明 | 调用 |
|---|---|---|
| `GET /resources/meta` | 大陆/数量/版权提示 | `resourceMeta(token)` |
| `GET /resources/books?continent=A..H` | 推荐书目（按大陆过滤，可选） | `resourceBooks(continent, token)` |
| `GET /resources/hymns` | 圣诗目录 | `resourceHymns(token)` |
| `POST /resources/bookmark` `{slug, kind}` | 收藏（需登录） | `resourceBookmark(slug, kind, token)` |
| `GET /resources/bookmarks` | 我的收藏 | `resourceBookmarks(token)` |

## 若想手写进 `src/api.js`（对齐既有风格）
```js
export async function lamentCompose(text, situation, token) {
  const res = await fetch(`${API_BASE}/lament/compose`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify({ text, situation, use_ai: true }),
  })
  const d = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(d.detail || '生成失败')
  return d  // { ok, movements:[{key,name,verb,guidance,draft,scripture}], prayer, themes, crisis, crisis_note, ... }
}
```
其余 11 个模块同构，只需替换 path / 请求体字段（见上表）。或直接用 `expansionEndpoints.js`。

## 深链打开扩充面板（无需自建 UI）
`ExpansionLauncher` 已暴露全局：`window.__expansionOpen('lament' | 'union' | 'contentment' | 'knowgod' | ...)`，
任意按钮 `onClick` 调用即可打开对应模块面板。PlanetHome 接线见 `EXPANSION_PLANETHOME_WIRING.md`。
