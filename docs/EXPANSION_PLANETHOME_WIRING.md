# 属灵星球「大陆入口」接线指南（延迟接线 · 合并后再贴）

> 目的：把扩充模块（**哀歌 / 与基督联合 / 基督徒知足**，以及可选其余）挂进 `PlanetHome.jsx`
> 的大陆卡片 chips。**现在不要贴**——并行进程正在改 `PlanetHome.jsx`。等他们那批前端合并进 main
> 之后，按下面 3 步贴一次即可。全部改动都是**加法**，不删他们任何 chip。

## 前置（已就绪，无需改动）
- `src/expansion/ExpansionLauncher.jsx` 已在 `main.jsx` 自挂载，并暴露 `window.__expansionOpen(featureKey)`。
- `src/expansion/planetEntries.js` 已提供 `withExpansionChips()` 与 `handleExpansionTarget()`。
- 深链 featureKey：`lament`(哀歌) `union`(联合) `contentment`(知足) `affections` `tender` `knowgod`
  `delight` `liturgy` `eh` `resources`。

## 合并后，改 `src/PlanetHome.jsx` 三处

**① 顶部加一行 import：**
```js
import { withExpansionChips, handleExpansionTarget } from './expansion/planetEntries'
```

**② `act()` 最前面认 `exp:` 前缀（一行）：**
```js
// 原：
const act = (target) => { if (target === '_close') onClose(); else go(target) }
// 改为：
const act = (target) => {
  if (target === '_close') return onClose()
  if (handleExpansionTarget(target)) return          // ← 新增：命中 exp: 前缀则深链打开扩充面板
  go(target)
}
```

**③ 渲染时用 `withExpansionChips` 包一层（把 CONTINENTS 换成包装后的）：**
```js
// 原：
{CONTINENTS.map((c, i) => (
// 改为（默认只挂用户指定的 哀歌/联合/知足）：
{withExpansionChips(CONTINENTS).map((c, i) => (
// 若想把其余不重叠模块也挂上：
{withExpansionChips(CONTINENTS, { includeOptional: true }).map((c, i) => (
```

## 默认挂载的三个入口
| 大陆 | 新增 chip | 深链 |
|---|---|---|
| 回到福音 | 与基督联合 › | `exp:union` |
| 认识自己 | 基督徒知足 › | `exp:contentment` |
| 等候上帝 | 哀歌 · 向神倾诉 › | `exp:lament` |

## ⚠️ 一处重叠须知
「等候上帝」大陆已有他们的 **十架哀歌 (cross-lament-hope，客户端引擎)**。本包的 **哀歌 (exp:lament，
服务端 /api/lament·Vroegop 四步)** 与之主题重叠。合并时二选一或并存由你/他们决定——
本指南默认加上，删掉这一行 chip 即可撤销。

## 回退
撤销只需还原上面 3 处（或删 `EXPANSION_CHIPS` 里对应行）。零副作用、不影响其它大陆。
