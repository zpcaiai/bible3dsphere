# 属灵星球 · 内容与神学扩充建议（第二辑 · 超出已建成版图）

> 与第一辑 `CONTENT_THEOLOGY_EXPANSION_2026-07.md` 配套。
> 方法：**先核实系统真实状态，再只推荐"尚未落地 / 尚未覆盖"的内容**，避免重复已建成的引擎。
> 日期：2026-07-01

---

## 一、重要更正：第一辑的"优先 8 项 + 6 个框架"其实已经建成

核实 `backend/*_engine.py` 的 docstring 后确认：第一辑列为"空白/待建"的推荐，**绝大多数已在 2026-07-01 当天落成对应引擎**。这改变了"还有哪些"的答案——真正的空白要往它们**没覆盖**的方向找。

| 第一辑推荐 | 已建成引擎 | 实现的思想/作者 |
|---|---|---|
| 结构化哀歌模板 | `lament_engine.py` | Vroegop《黑云背后是深恩》四步 |
| 情绪球的神学底座 | `affections_engine.py` | 爱德华兹《宗教情感真伪辨》 |
| 失序之爱 / 重排 | `ordo_amoris_engine.py` | 奥古斯丁 ordo amoris |
| 温柔谦卑 / 托底非定罪 | `tender_heart_engine.py` | Dane Ortlund《温柔谦卑》 |
| 文化礼仪塑造欲望 | `formation_liturgy_engine.py` | James K.A. Smith《你的爱决定你是谁》 |
| Formation OS 全人理论 | `renovation_engine.py` | 达拉斯·魏乐德（VIM 框架） |
| 华人本土灵修 | `chinese_devotion_engine.py` | 倪柝声 / 王明道 / 唐崇荣 / 宋尚节 |
| 诸灵分辨（安慰/枯竭） | `spirits_engine.py` | 依纳爵《神操》 |
| 基督徒享乐主义 | `delight_engine.py` | 派博《渴慕神》 |
| 情感健康的属灵 | `emotionally_healthy_engine.py` | 斯卡吉罗（冰山比喻） |
| 认识神（神论主线） | `know_god_engine.py` | 巴刻 / 陶恕 / 里夫斯 |
| 基督徒的知足 | `contentment_engine.py` | 伯罗斯《基督徒知足的秘诀》 |
| 与基督联合作为脊椎 | `union_engine.py` | Union with Christ（在基督里的身份） |

**结论**：第一辑几乎被完整执行。下面只列**它没覆盖**的内容。

---

## 二、第一辑点名、但目前仍无专属引擎（真待办，先补这几味）

| 主题 | 作品 / 作者 | 现状核实 | 落点 | 优先 |
|---|---|---|---|---|
| **得救的确据** | 辛克莱·傅格森《全备的基督》The Whole Christ（律法主义/反律法主义/确据） | "确据"只在 `confession`/`pilgrim`/`tender_heart` 里零散提到，**无专属引擎** | 新 `assurance_engine`，**直接对接钟马田属灵低潮诊断**（低潮常源于确据缺失） | ⭐⭐⭐ |
| **团契神学** | 潘霍华《团契生活》Life Together | 有 accountability/community **功能**，但**无神学底座** | community 功能的底层；对治"信而不入群体" | ⭐⭐⭐ |
| 真悔改的解剖 | 汤姆·华森《悔改的教义》六要素 | `gospel`/`confession` 触及，无系统化 | 强化"认罪→转向"环 | ⭐ |
| 操练分类学 | 傅士德《属灵操练礼赞》 | 操练页已多，但缺分类学正主 | 操练页的目录学框架 | ⭐ |
| 祷文库 | 《幽谷之旅》Valley of Vision（清教徒祷文集） | 祷告规则/诗篇祷告有流程，缺祷文语料 | 清晨甘露/祷告规则的祷文池 | ⭐⭐ |

---

## 三、超出第一辑的全新大陆（"还有哪些"的核心）

> 按"最能补系统结构性盲点"排序。系统极擅长**向内诊断（心镜）**，两个最大盲点是：**向外转（爱邻舍）**与**节奏/盼望**。核实：`forgive / fellowship / sabbath / assurance / gratitude / holiness / neighbor / justice / hospitality / hope / fear_of / wisdom` 均**无对应引擎**。

### 旗舰 · 向外转：爱邻舍 / 怜悯 / 公义 / 款待

系统几乎全是向内的自我诊断，缺把福音**转向邻舍、仇敌、弱者、陌生人**的操练。这也回应第一辑自己的批评（"重人心诊断，轻…"）。

| 作品 | 作者 | 核心理念 | 落点 | 优先 |
|---|---|---|---|---|
| 《慷慨的正义》Generous Justice | 提摩太·凯勒 | 被恩典改变的心必然流向怜悯与公义 | 新"爱邻舍"大陆的主干；给虚荣/自义一味**向外的解药** | ⭐⭐⭐ |
| 山上宝训伦理 / 《神国的邀请》The Divine Conspiracy | 钟马田 / 达拉斯·魏乐德 | 天国子民的品格与仇敌之爱 | 品格塑造的外向维度（与 virtues 互补） | ⭐⭐⭐ |
| 《带着家门钥匙的福音》The Gospel Comes with a House Key | Rosaria Butterfield | "平凡的款待"作为门徒操练 | 款待/群体的具体操练 | ⭐⭐ |

### 其余新大陆

| # | 主题 | 作品 / 作者 | 落点 | 优先 |
|---|---|---|---|---|
| 1 | **饶恕与和好** | 沃弗《白白的恩典》/《拥抱神学》；Worthington REACH 模型 | **无饶恕引擎**——关系创伤后的牧养药，接在 `crisis`/`suffering` 之后 | ⭐⭐⭐ |
| 2 | **不慌不忙·安息节奏·生活规则** | John Mark Comer《无情地铲除匆忙》；Ruth Haley Barton《神圣的节奏》；毕德生《持续一生的顺服》 | 直接喂 `formation_liturgy`+`cultural`+`emotionally_healthy`+安息日页；一个 **rule-of-life 编排层** | ⭐⭐⭐ |
| 3 | **敬畏神** | 迈克·里夫斯《欢喜而战兢》Rejoice and Tremble | 给 `know_god` 配一条"敬畏 × 喜乐"的平衡轴（现偏慈爱/属性） | ⭐⭐ |
| 4 | **感恩 eucharisteo** | 安·沃斯甘《一千次感谢》One Thousand Gifts | 与 `contentment` 互补：知足对治"缺乏之心"，感恩是"数算恩典"的日更操练 → 清晨甘露 | ⭐⭐ |
| 5 | **成圣 / 圣洁（正面）** | 莱尔《圣洁》Holiness；华特·马歇尔《成圣的福音奥秘》 | 已有欧文"治死"（负面 mortification），缺**正面的圣洁长进 + 与确据相连**；接 `union`+`gospel` | ⭐⭐ |
| 6 | **盼望·永恒·复活** | 赖特《意料之外的盼望》；Randy Alcorn《天堂》 | Baxter 已给"天家安息"，缺**前瞻性复活盼望 + memento mori**；作受苦/等候的终末锚 | ⭐⭐ |
| 7 | **祷告经典** | 慕安得烈《与主同行的祷告学校》；E.M. Bounds；Hallesby《祷告》；Valley of Vision | 祷告有**功能**、缺**经典文本**喂养 → 祷告规则/诗篇祷告祷文库 | ⭐⭐ |
| 8 | **默观的情感线**（附教义提示） | 诺里奇的朱利安《神圣之爱的启示》"凡事都必好"；大德兰《七宝楼台》；《未知之云》 | 已有约翰十字架（枯竭）；补朱利安的**盼望与神的慈爱**；接默想/枯竭之后的安慰 | ⭐ |
| 9 | **道成肉身与"与神性有份"** | 亚他那修《论道成肉身》（公版，路易斯作序） | 深化 `union` 的**古典/东方线**（彼后1:4 与神的性情有份） | ⭐ |
| 10 | **智慧文学·实践智慧** | 箴言 /"敬畏耶和华是智慧开端"的活得有智慧一线 | 平衡以诗篇-情绪为主的现状；给 `decision`/`habit` 加智慧维度 | ⭐ |
| 11 | **全球 / 受苦教会之声** | 霍华德·瑟曼《被剥夺者的耶稣》及多数世界教会 | 继华人声音之后的下一站；接受苦/公义/见证 | ⭐ |

---

## 四、理念级：可直接长成引擎的 5 个新框架

不只是加书；以下框架与现有 engine+router 建法契合，可落成模块：

1. **爱邻舍 / 向外转**——把"向内诊断"补上"向外的果子"：诊断的终点不只是"你在基督里是谁"，还有"因此你如何转向邻舍"。
2. **饶恕与和好**——关系创伤的福音路径（命名伤害 → 分辨 → 交托 → 释放 → 界限 → 走向和好但不强求），是 `crisis` 之后缺的一味。
3. **安息节奏 / 生活规则（rule of life）**——一个**编排层**，把已有的安息日、祷告规则、禁食简朴、操练同在**串成一套可持守的生活节奏**，对治现代匆忙-焦虑。
4. **敬畏 × 喜乐**——给 `know_god` 配平衡轴：认识神既是被慈爱吸引，也是在圣洁前战兢；两者一起才不失衡。
5. **确据（assurance）**——接钟马田-`pilgrim`-`confession`：把"我到底得救了吗"从零散提及，升级为一条有诊断、有牧养的轴线。

---

## 五、敬拜诗歌 / 祷文补充（延续第一辑 I）

- **生活规则相关祷文**：晨祷 / 晚祷（Compline）、Valley of Vision 选段——配合上面第 3 号框架。
- 其余圣诗/当代诗歌扩充见第一辑 I 节（Be Thou My Vision、In Christ Alone、你信实何广大、《我知谁掌管明天》等）。

---

## 六、版权与教义提醒

- **公版优先**：亚他那修、诺里奇的朱利安、大德兰、清教徒（华森、马歇尔）、莱尔、慕安得烈、E.M. Bounds——可收较完整文本。
- **当代著作用授权节选/导读**：Comer、Barton、沃斯甘、沃弗、赖特、Alcorn、里夫斯、Butterfield、凯勒、傅格森、毕德生。
- **跨传统取材**（天主教默观、东正教 theosis、被剥夺者神学）：沿用系统既有的"**不定罪、导向信靠**"措辞，并对争议处加**轻教义提示**，保持**福音中心 + 圣经为最终准绳**。

---

## 附录：第二辑落地记录（2026-07-01 已实现）

以下 8 个引擎已按现有 `*_engine.py` / `routers/*.py` 约定**完整落地**（纯函数确定性核心 + 内置危机检测 + 可选 AI 增强 + `formation_signal` 回流 + best-effort 持久化，缺表不影响 `/analyze`）。已通过引擎级与 FastAPI TestClient 端到端验证（`/meta`、`/analyze` 均 200，危机词命中返回 `crisis_note`，未登录返回 401）。

| 主题 | 引擎文件 | 路由前缀 | 神学来源 |
|---|---|---|---|
| 得救的确据 | `assurance_engine.py` | `/api/assurance` | 傅格森《全备的基督》（律法/反律法/确据） |
| 饶恕与和好 | `forgiveness_engine.py` | `/api/forgiveness` | 沃弗 + Worthington REACH（含施虐处境安全分支） |
| 团契生活 | `fellowship_engine.py` | `/api/fellowship` | 潘霍华《团契生活》 |
| 安息节奏 / 生活规则 | `rule_of_life_engine.py` | `/api/rule-of-life` | Comer / Barton / 毕德生 |
| 敬畏神 | `fear_of_god_engine.py` | `/api/fear-of-god` | 里夫斯《欢喜而战兢》 |
| 感恩 Eucharisteo | `gratitude_engine.py` | `/api/eucharisteo` | 沃斯甘《一千次感谢》（含 hard-eucharisteo 转介哀歌） |
| 成圣与圣洁 | `holiness_engine.py` | `/api/holiness` | 莱尔《圣洁》+ 马歇尔《成圣的福音奥秘》 |
| 爱邻舍·公义·款待 | `neighbor_love_engine.py` | `/api/neighbor-love` | 凯勒《慷慨的正义》+ 山上宝训 + 款待 |

**接线**：`main.py` 已在 gratitude 路由之后幂等插入三处（import / init / include_router）。
**建表**：`expansion_batch2_schema.sql`（8 张 `*_entries` 表，结构统一，含 email+created_at 索引）；持久化为 best-effort，迁移未跑时 `/analyze` 仍正常返回。
**安全加固**：8 个引擎的轻量危机词表补入了「想死」（原 `contentment_engine` 模板遗漏）。

> 每个引擎每个端点：`GET {prefix}/meta`、`POST {prefix}/analyze`（body: `{"text": "...", "use_ai": true}`）、`GET {prefix}/history`、`GET {prefix}/latest`。

---

## 附录二：次要新大陆（5 引擎）+ 前端接入（2026-07-01 已实现）

### 后端第三批（5 个次要大陆引擎）
同一约定（纯函数 + 危机检测 + 可选 AI + `formation_signal` + best-effort 持久化），已通过引擎级 + TestClient 端到端（13/13 全绿）。

| 主题 | 引擎文件 | 路由前缀 | 神学来源 |
|---|---|---|---|
| 复活盼望 | `hope_engine.py` | `/api/hope` | 赖特《意料之外的盼望》+ Alcorn《天堂》+ memento mori |
| 祷告经典 · 祷告的学校 | `prayer_classics_engine.py` | `/api/prayer-school` | 慕安得烈 / E.M. Bounds / Hallesby / 幽谷之旅 |
| 默观 · 在神爱里安息 | `contemplation_engine.py` | `/api/contemplation` | 诺里奇的朱利安 / 大德兰 / 未知之云（附教义护栏） |
| 道成肉身 · 与神性情有份 | `incarnation_engine.py` | `/api/incarnation` | 亚他那修《论道成肉身》+ 彼后1:4 theosis（附教义护栏） |
| 智慧 · 敬畏神地活 | `wisdom_engine.py` | `/api/wisdom` | 箴言 / 传道书 / 雅各 |

接线：`main.py` batch3 三处幂等接线；建表：`expansion_batch3_schema.sql`（5 张表）。

### 前端接入（全部 13 个新引擎）
复用既有 `src/expansion/` 子系统（第一批扩充引擎已建），**无需新建页面/路由**：

- `src/expansion/ExpansionHub.jsx`：`FEATURES` 注册表 +13 条（统一 `kind:'text'` / `action:'analyze'`），`LABELS` 补齐新字段中文标签。通用 `FeatureRunner` 负责 meta 展示 + 文本输入 + `POST /{prefix}/analyze` + 结果渲染（经文/祷告/操练/危机提示自动排版）。
- `📖` 悬浮入口 `ExpansionLauncher` 已在 `src/main.jsx` 全局挂载 → 13 个模块即刻可见可用。
- `src/expansion/planetEntries.js`：新增 `EXPANSION_CHIPS_BATCH2`（13 个大陆入口），并入 `withExpansionChips(includeOptional)`。
- `src/expansion/expansionEndpoints.js`：+13 组 `xxxMeta/xxxAnalyze/xxxHistory/xxxLatest` 与 `EXPANSION_MODULES` 条目。
- 全部改动经 esbuild 转译校验通过；前端 13 个 `prefix` 与后端路由逐一对齐。

### 部署清单
1. 数据库执行 `backend/expansion_batch2_schema.sql` 与 `backend/expansion_batch3_schema.sql`（不执行也能用，只是不落历史）。
2. 后端随 HF Space 部署自动生效（`main.py` 已接线，`/api/<prefix>/meta|analyze|history|latest`）。
3. 前端 push 触发 Vercel 构建即生效；`📖` 入口已展示全部 13 个模块。

---

## 附录三：星球大陆入口接线 + 单元测试（2026-07-01 已实现）

### PlanetHome 大陆入口（13 个默认挂载）
按 `docs/EXPANSION_PLANETHOME_WIRING.md` 完成 `src/PlanetHome.jsx` 三处接线（import + `act()` 认 `exp:` 前缀 + `withExpansionChips(CONTINENTS)` 包裹），并把 `planetEntries.js` 的 `EXPANSION_CHIPS_BATCH2` **重映射到真实的 7 个大陆名**。调整后 `withExpansionChips` 默认即挂载「用户指定 3 个 + 第二辑 13 个」，`includeOptional` 才叠加第一批其余可选项。

| 大陆 | 新增 chip（点击深链 `exp:<key>` → 打开 ExpansionHub 模块） |
|---|---|
| 健康教会九标志 | 团契生活 · 爱邻舍公义款待 |
| 认识自己 | 感恩数算恩典 · 智慧敬畏神地活 |
| 回到福音 | 得救的确据 · 道成肉身 · 敬畏神 |
| 与神同行 | 安息节奏 · 祷告经典 · 默观 |
| 等候上帝 | 复活盼望 |
| 人格塑造 | 成圣治死与穿上 · 饶恕与和好 |

（天路客大陆保持不变。）node 实跑 `withExpansionChips` 确认 13 个 chip 全部挂到真实大陆、`handleExpansionTarget('exp:*')` 正确深链；chip 的 featureKey 与 `ExpansionHub` 的 `FEATURES` key 逐一对应。

### 单元测试
`backend/tests/test_expansion_batch2_engines.py`（遵循 `pytestmark = pytest.mark.no_db` 约定），覆盖 13 引擎的 meta/analyze 契约、危机检测正反、`formation_signal` 形状、确定性、AI 关闭回退、空输入安全，以及分支专项（确据律法/反律法路由、饶恕施虐安全分支、感恩 hard-eucharisteo 转介哀歌、成圣治死/穿上与福音次序、默观&道成肉身教义护栏、智慧敬畏根基等）。**153 个用例全绿**。

### 交付物汇总（第二辑全量）
- 后端：13 引擎 + 13 路由 + 2 schema（13 表）+ `main.py` 接线 + 13 引擎单测。
- 前端：`ExpansionHub` FEATURES +13 / `expansionEndpoints` +13 / `planetEntries` +13 / `PlanetHome` 三处接线；全部 esbuild 校验通过，`📖` 入口与大陆卡片双通道可达。
