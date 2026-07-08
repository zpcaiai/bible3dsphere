#!/usr/bin/env bash
# B10–B12 提交脚本 —— 在你自己的 Mac 终端运行(非沙箱;沙箱禁止删除 .git/index.lock)。
# 运行前请确认没有 git GUI / 其它 git 进程在这两个仓库里跑。
set -uo pipefail

BACKEND="/Users/stephen/Documents/Projects/DoctorPro/bible3dsphere"
FRONTEND="/Users/stephen/Documents/Projects/DoctorPro/bible3dsphereWeb"

echo "════════ 后端 (bible3dsphere → hf) ════════"
cd "$BACKEND" || exit 1
rm -f .git/index.lock
# 仅暂存本轮 B10–B12 的文件;有意排除 bible_bilingual_metadata.pkl(二进制,非本轮改动)
git add \
  .github/workflows/quality.yml backend/main.py backend/core/tenancy.py backend/b12_smoke.py \
  backend/routers/ai_tutor.py backend/routers/spiritual_memory.py backend/routers/analytics.py \
  backend/routers/org_console.py backend/routers/billing.py backend/routers/platform_admin.py \
  backend/routers/productization.py backend/routers/accountability_group.py backend/routers/church_integration.py \
  backend/routers/daily_soul_question.py backend/routers/discipleship.py backend/routers/journal.py \
  backend/routers/mentor.py backend/routers/personal_notes.py \
  backend/migrations/0121_formation_analytics.sql backend/migrations/0122_productization.sql \
  backend/migrations/0123_spiritual_memory.sql backend/migrations/0124_ai_tutor_threads.sql \
  backend/migrations/0125_community_org_scope.sql backend/migrations/0126_billing_moderation.sql \
  backend/tests/test_org_console_contracts.py backend/tests/test_church_checkin_org_contracts.py \
  backend/tests/test_billing_webhook_contracts.py backend/tests/test_platform_admin_contracts.py \
  B12_TENANCY_TEST_CHECKLIST.md CHANGES_B10_B12.md SAFETY_AUDIT_B1-13.md docs/isolation-architecture.svg
git commit -m "B10–B12: AI tutor+memory, analytics charts, true multi-tenant isolation

- B10: ai_tutor + spiritual_memory routers (crisis gate, consent, LLM fallback); migrations 0123/0124
- B11: analytics /series + dependency-free SVG charts; safety audit hardens 3 free-text intakes
- B12: core/tenancy enforcement layer, org_console (11 endpoints), billing (Stripe), platform_admin
       create-with-org on community routers; migrations 0125/0126
- tests: b12_smoke.py (40 invariants) + contract tests (org_console/church/billing/platform = 25); CI gates"
echo "  → 准备 push 到 HuggingFace Space(会触发重建):"
git push hf main

echo ""
echo "════════ 前端 (bible3dsphereWeb → origin) ════════"
echo "  注意:该仓库当前有 ~128 个改动文件(含非本轮的并行改动)。"
echo "  下面只暂存本轮 B10–B12 的 8 个文件;其余请你自行 review 后决定。"
cd "$FRONTEND" || exit 1
rm -f .git/index.lock
git add \
  src/api.js src/components/SoulDashboard.jsx \
  src/AITutorChatPage.jsx src/SpiritualMemoryPage.jsx src/FormationChartsPage.jsx \
  src/OrgConsolePage.jsx src/BillingPage.jsx src/PlatformAdminPage.jsx
git commit -m "B10–B12 frontend: AI tutor, spiritual memory, formation charts, org console (tabs), billing, platform admin"
git push origin main

echo ""
echo "✅ 完成。建议 push 前/后本地校验(注意:都要在 backend/ 目录里跑,否则 'No module named core'):"
echo "   cd \"$BACKEND/backend\""
echo "   # 无需数据库,现在就能跑:"
echo "   python b12_smoke.py"
echo "   python -m pytest tests/test_*_contracts.py -q"
echo "   # 迁移仅在你有真实 Postgres 时手动跑(push 到 HF Space 后,Space 启动会自动应用 0123–0126):"
echo "   export DATABASE_URL='postgresql://USER:PASS@HOST:5432/DBNAME'  &&  python -m core.migrations"
echo "   # 若报 ModuleNotFoundError: fastapi → pip install fastapi pydantic pytest psycopg2-binary"
echo "   cd \"$FRONTEND\"  &&  npm run build"
