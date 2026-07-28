# EMD-OS：BEFORE_MORE_USERS 五项 + 删除传播实机验证

Date: 2026-07-28

五项里有四项的终点是人的判断，一项的终点是有人真的去按开关。所以这一轮做的是**把人以外的部分全部做完**，
并且刻意让这些工具**无法自己宣布完成**——样本不够就返回 `INSUFFICIENT_SAMPLE`，法律问题没答就永远是
`DRAFT`，DRY_RUN 永远只返回 `DRY_RUN_ONLY`。

一个会自我背书的工具比没有工具更糟。

---

## 1. 删除传播：真实数据库验证

沙箱里装不了 PostgreSQL（无 root，pglite / testing.postgresql 都依赖系统 PG）。所以做了两件能做的事：

**离线做到极限**（`tests/test_emd_erasure_schema_verification.py`，36 个用例）

- 用 `pglast`（libpg_query，PostgreSQL 真正的解析器）解析全部 12 个 EMD 迁移与 rollback——语法错误现在会在 CI 挂掉，而不是部署时
- 从 501 张表的 DDL 重建目录，离线回放 `erasure_coverage_gaps()` 的集合逻辑，断言零缺口
- 排除清单是**从迁移文件里解析出来的**，不是抄进测试的，两者无法漂移

**这一轮又查出一个假绿**：原来的列名正则是行首锚定的，而 EMD 迁移把多个列写在同一行——

```sql
id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, email TEXT NOT NULL,
```

`email` 从来没被识别到，"个人表集合"是空集，于是 `personal ⊆ erase_list` 恒成立。**那条删除传播断言一直在比较空集。**
解析器已重写（顶层逗号切分），共享到两个套件，并加了一条专门钉住这个 bug 的用例。真实数字是 330 张 email 键表、27 张 user_id 键表。

**仍需你做**：`DATABASE_URL=... python3 backend/scripts/verify_emd_erasure.py`
一条命令，输出逐项 PASS/FAIL，退出码 0 表示每张个人表都在删除路径内。`--read-only` 跳过写入。

---

## 2. 红队：14 个攻击面自动化

`tests/test_emd_red_team.py`，45 个用例，真实中文攻击载荷打真实代码路径。

**查出两个真问题：**

**① `validate_safe_text` 接受 `<script>` 与 `<img onerror=>`**
`ATTACK_SURFACES` 里明写着 `REPORT_INJECTION: 群体反馈包含脚本或 HTML`，实现却只查禁用措辞、不查标记。
而这些文本会出现在群体反馈与牧养摘要里——是要被渲染的。已加标记拦截（script / iframe / 事件处理器 / js: / 模板表达式），
同时确认 `成本 < 100 且 > 50` 这类正常中文不受影响。

**② `_set_state` 不带 owner 谓词**
每个调用方都先调了 `_load_session(email, session_id)`，所以今天没有 IDOR。但这依赖每个未来的调用方都记得这个顺序，
而跨租户写入是零容忍项。已把 email 谓词下沉进 `_set_state` 本身——忘记的调用方现在更新零行，而不是改到别人的会话。

**顺带修正了一个设计张力**：`validate_ui_payload` 会把用户自己输入的"总分"两个字判成违规，
等于任何打了这两个字的用户都会把自己的页面弄成 invalid，反而逼前端绕过契约。
现在区分「系统的断言」与「回显用户原话」，禁用**键**仍然全局拦截。

**仍需你做**：接上真实模型与 RAG 后重跑一轮。这套只证明确定性层成立，证明不了模型层。

---

## 3–4. 认知访谈与评分一致性

`formation_twin/emotional_maturity_psychometrics.py`

**访谈**：四步法协议（复述 → 回忆 → 决策 → 难点，顺序是方法的一部分——先看到选项就再也看不到他原本的理解了）、
8 个已知歧义词（「真我」「顺服」「放下」「最近」…）、选题策略（先回访出过问题的，再补未覆盖维度）、
findings 分析（同一题两次阻断性发现 = 必须改写）。

**一致性**：Cohen's κ 而不只是百分比。六个有序阶段 + 分布不均时，两个都习惯给 E2 的评分者能靠巧合刷出 70% 一致率——
`chance_inflated` 就是拆穿这个的。相邻分歧（E2/E3）与跨级分歧（E1/E4）分开统计：前者是锚点措辞问题，可以改；
后者说明锚点根本没落在可观察行为上，靠培训解决不了。

**仍需你做**：跑访谈（5–10 人 × 30 分钟）；第二位评分者独立评 30 条。
单人评分只会得到 `INSUFFICIENT_DATA`，工具不会替你放行。

---

## 5. 事故演练

`formation_twin/emotional_maturity_incident_drill.py`

10 步 SEV1 流程，三种模式：`DRY_RUN`（默认，只跑决策链）、`STAGING`、`PRODUCTION`（**直接拒绝**）。
5 步可在代码里断言，5 步必须人确认——未确认的返回 `NEEDS_HUMAN`，不会静默通过。
熔断姿态与 `pilot_gate` 真实会执行的 flags 对齐，有测试盯着两者一致。

**仍需你做**：对 staging 实跑一次 STAGING 模式，逐一确认那五个人工步骤。

---

## 6. 隐私影响评估

`formation_twin/emotional_maturity_privacy_assessment.py`

从迁移自动推导：74 张 EMD 表 → 10 个数据类别，其中 22 张属特殊类别（宗教信仰 / 危机 / 家庭史 / 健康信号）。
映射 PIPL 第 28/29/31/38-39/44-47/55-56 条与 GDPR Art. 6/8/9/13-14/15-22/22/35/44-49，共 14 条。
9 项已实现控制措施各自指向代码证据位置。

**8 个法律问题标为 `NEEDS_LEGAL_REVIEW`，工具永远不填**，状态恒为 `DRAFT_PENDING_LEGAL_REVIEW`。
其中最需要人的一条：牧养关系中的权力不对等会影响同意是否「自由给出」——那是判断题，不是配置项。

---

## 附带修掉的一个真 bug：`/openapi.json` 整个构建不出来

装上 `requirements.txt` 里本来就有的 `slowapi` 之后，`main.app.openapi()` 直接抛 `PydanticUserError`。
也就是 `/docs`、`/openapi.json`、客户端代码生成**全都是坏的**。

之前看不出来，是因为沙箱缺 slowapi 时 `core/ratelimit.py` 会退化成 stub limiter，不包装函数。

根因：`routers/media.py` 有 `from __future__ import annotations`（注解变成字符串）+ `@limiter.limit`（slowapi 用
`functools.wraps` 包装）+ `= Body(Model)`。FastAPI 跟着 `__wrapped__` 拿到原函数的字符串注解，却在 slowapi 的
命名空间里解析——那里没有 `ScriptTTSRequest`。全仓库只有 media.py 同时满足这三个条件，所以一直藏着。

修法：直接去掉 `media.py` 的 `from __future__ import annotations`，并在文件顶部写明为什么不能加回来。
（先前那个 `core.ratelimit.rate_limit()` 包装器已删除——问题从源头解决后它就成了没有调用方的死代码。）

**守卫**：`test_no_router_combines_postponed_annotations_with_a_limited_body_model` 全仓扫描这三要素的组合，
1.4 秒跑完，每次提交都跑；把 bug 人为放回去，会有 3 条用例立刻失败（已实测）。
判断用的是真正的 import 语句而不是子串——否则 media.py 里那句解释性注释自己就会被误判。
另有一条 scoped openapi 测试（只构建 media router）保证 schema 真的能出；全应用版本 ~40s，标 `slow` 供 CI 跑。

---

## 自审：在自己新写的代码里查出的 4 个 bug

新写的模块只有它们自己的测试看过，所以用同样的方式又审了一遍。

**① 安全校验器可被字段命名绕过**（真 bug）
`_is_user_authored` 用子串匹配，于是任何以用户字段名开头的系统字段都被当成「用户写的」跳过检查——
`accepted_stage`、`notes_from_system`、`echo_verdict` 全部逃逸。
一个换个字段名就能绕过的校验器不是校验器。改成按路径段精确匹配。

**② κ 为负被读成「轻微一致」**（真 bug）
两位评分者系统性相反时 κ = -1.0，`interpret_kappa` 归进 `SLIGHT`，读起来是「有点一致」——完全相反的结论。
新增 `SYSTEMATIC_DISAGREEMENT` 档，且负 κ 直接 `BLOCKED`，提示先确认是不是有人把量表方向看反了。

**③ 训练退出把「他动手做饭」判成危机级**（真 bug）
裸词 `动手`、`打` 命中一切。过度保护看起来安全，实际有两个代价：真正的 P4 淹没在噪音里，
大量正常文本也永远无法交给模型辅助整理。改成要求受害语境（`动手打` / `对我动手` / `打我(?!电话)`），
同时补回被我一并删掉的 `不想活|活不下去`——自杀意念必须是 P4。
15 条正反用例钉住边界：「他昨天又打我」是 P4，「打我电话」不是。

**④ 隐私评估自带了第二个 DDL 解析器**（潜在漂移）
就是我刚修过的那一类。今天两者判断一致纯属运气。解析器已提到 `core/schema_catalog.py`，
生产与测试共用一份，并加了一条断言禁止出现第二份。

---

## 状态

```
2176 tests passed, 0 failed
ready_for_pilot_use: true
auto_verified: SAFETY_E2E, DELETION_PROPAGATION, MODEL_TRAINING_OPTOUT,
               UI_LABELS, SHARING_OFF, RED_TEAM_LIGHT
```

四项仍标 TODO 且**不会**被自动核验（`auto_verified: false`），各自写明 `still_needs_humans`：
认知访谈、评分一致性、隐私评估、事故演练。
