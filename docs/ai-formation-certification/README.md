# AI Formation 生产认证工作区

本目录绑定 `sunday_school.ai_formation.content-bundle@1.0.0` 的 67 个内容版本。自动化只准备证据；神学、牧养、儿童保护、隐私/权利、人工无障碍与最终发布决定必须由对应授权人使用自己的认证身份提交。

## 当前内容范围

- 精确版本数：67
- bundle SHA-256：`e5f9c6c7b15aae0c5d3cb5b240e1aea2b23a9986da5ac6977384eb6a63e870e5`
- 自动预审状态：`BLOCKED`
- 阻断：`STATEMENT_OF_FAITH_VERSION_REQUIRED`
- 阻断：`SOURCE_RIGHTS_OWNER_ATTESTATION_REQUIRED`
- 自动批准：禁止
- 自动发布：禁止

`content-review-index.json` 是总索引；`content-review-packets/` 中每个文件固定 content ID、版本和 canonical SHA-256，并列出经文锚点、权威标签、年龄带、敏感主题上下文命中、所需角色和空白签署位。

## 生成命令

```bash
.venv/bin/python backend/scripts/generate_ai_formation_content_review.py
```

组织提供已批准的信仰告白版本和权利负责人声明后，重新生成可进入授权人工审核的包：

```bash
.venv/bin/python backend/scripts/generate_ai_formation_content_review.py \
  --statement-of-faith-version '<approved-version>' \
  --rights-attestation-id '<owner-attestation-id>'
```

这两个参数只固定审核范围，不代表审核结论。每位审核人仍须逐项查看自己的 packet，并通过产品 API 提交 `approve`、`request_changes` 或 `reject`。审核人不得是制品作者；发布人必须与作者及所有审核人分离。

## 各角色必须核对

- `theology_reviewer`：经文上下文、权威分层、恩典先于操练、宗派差异、有害使用。
- `pastoral_reviewer`：S0–S3、非诊断语言、羞辱/胁迫、真人交接、地区资源。
- `child_safety_reviewer`：秘密关系、成人私聊、诱导/性化、监护绕过、数据暴露、保护升级。
- `rights_reviewer`：原创/受托权利、第三方来源、圣经译文范围、缓存/导出/再分发许可。
- `accessibility_reviewer`：年龄适切、易读性、认知负担、替代活动和敏感流程退出。
- `release_reviewer`：证据版本、制品哈希、阻断项、有限发布和回滚准备。

## 人工签署边界

不要直接编辑生成的 packet 来伪造通过。授权审核人应登录 staging 审核台提交决定；数据库会记录认证邮箱、角色、精确 hash、理由码和时间，并在 hash 变化时拒绝旧审核。只有所有必需角色由不同审核人批准后，独立发布人才可发布。
