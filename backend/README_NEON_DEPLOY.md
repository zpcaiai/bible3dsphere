# Neon Database 部署指南

## 镜鉴人物数据库 (Biblical Characters)

### 自动部署到 Vercel + Neon

#### 方法一：使用 Vercel Dashboard 自动部署

1. **添加 SQL 文件到项目**
   
   确保 `backend/biblical_characters_seed.sql` 已提交到 git：
   ```bash
   git add backend/biblical_characters_seed.sql
   git commit -m "feat: add biblical characters seed data for Neon"
   git push
   ```

2. **在 Vercel 项目设置中添加数据库连接**
   
   - 进入 Vercel Dashboard → 你的项目 → Settings → Environment Variables
   - 添加 Neon 数据库连接字符串：
     ```
     DATABASE_URL = postgresql://username:password@hostname.neon.tech/dbname?sslmode=require
     ```

3. **使用 Vercel Cron Job 或 Build Hook 自动执行**

   在项目根目录创建 `vercel.json`：
   ```json
   {
     "crons": [
       {
         "path": "/api/db-seed",
         "schedule": "0 0 * * 0"
       }
     ]
   }
   ```

4. **创建 API 端点执行 SQL**

   创建 `api/db-seed.js`（见下方代码）

#### 方法二：手动执行 SQL（推荐首次部署）

1. **获取 Neon 数据库连接信息**
   
   在 Neon Dashboard 中：
   - 点击你的项目
   - 点击 "Connection String" 标签
   - 复制 PostgreSQL 连接字符串

2. **使用 psql 执行 SQL 文件**
   
   ```bash
   # 本地有 psql 的情况
   psql "postgresql://username:password@hostname.neon.tech/dbname?sslmode=require" -f backend/biblical_characters_seed.sql
   
   # 或使用 Neon SQL Editor
   # 1. 在 Neon Dashboard 打开 SQL Editor
   # 2. 复制粘贴 backend/biblical_characters_seed.sql 内容
   # 3. 点击执行
   ```

3. **使用 Neon CLI（可选）**
   
   ```bash
   # 安装 Neon CLI
   npm install -g neonctl
   
   # 登录
   neonctl auth
   
   # 执行 SQL 文件
   neonctl sql --file backend/biblical_characters_seed.sql --database-name your-db-name
   ```

### API 端点代码

创建文件 `api/db-seed.js`：

```javascript
import { Pool } from '@neondatabase/serverless';

export default async function handler(req, res) {
  // 只允许特定 token 或管理员访问
  const authToken = req.headers['x-admin-token'];
  if (authToken !== process.env.ADMIN_TOKEN) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  const pool = new Pool({ connectionString: process.env.DATABASE_URL });
  
  try {
    // 读取 SQL 文件
    const fs = require('fs');
    const path = require('path');
    const sql = fs.readFileSync(
      path.join(process.cwd(), 'backend/biblical_characters_seed.sql'),
      'utf8'
    );
    
    // 分割 SQL 语句并执行
    const statements = sql.split(';').filter(s => s.trim());
    const results = [];
    
    for (const statement of statements) {
      if (statement.trim()) {
        try {
          await pool.query(statement + ';');
          results.push({ status: 'success', statement: statement.slice(0, 50) + '...' });
        } catch (err) {
          results.push({ status: 'error', error: err.message, statement: statement.slice(0, 50) });
        }
      }
    }
    
    await pool.end();
    
    res.json({ 
      success: true, 
      message: 'Database seeded successfully',
      results 
    });
  } catch (error) {
    await pool.end();
    res.status(500).json({ 
      success: false, 
      error: error.message 
    });
  }
}
```

### 环境变量配置

在 Vercel Dashboard 中添加以下环境变量：

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `DATABASE_URL` | Neon 数据库连接字符串 | `postgresql://user:pass@host.neon.tech/db?sslmode=require` |
| `ADMIN_TOKEN` | 用于保护 seed API 的 token | `your-secure-random-token` |

### 数据库表结构

| 表名 | 记录数 | 说明 |
|------|--------|------|
| `biblical_characters` | 231 | 圣经人物主表 |
| `character_tags` | ~462 | 人物标签关联表 |
| `character_follow_points` | ~800 | 效法要点表 |
| `character_caution_points` | ~500 | 警戒要点表 |
| `character_applications` | ~1200 | 实际应用表 |
| `character_scriptures` | ~900 | 相关经文表 |
| `character_themes` | 15 | 主题合集表 |
| `character_theme_mappings` | ~800 | 人物-主题关联表 |

### 验证部署

执行 SQL 后，可以运行验证查询：

```sql
-- 查看人物统计
SELECT era, COUNT(*) as count 
FROM biblical_characters 
GROUP BY era 
ORDER BY count DESC;

-- 查看主题
SELECT id, name, emoji FROM character_themes;

-- 查看完整人物信息（使用视图）
SELECT * FROM v_character_full LIMIT 5;
```

### 更新数据流程

当 `mirrorData.js` 有更新时：

1. 重新生成 SQL：
   ```bash
   python3 scripts/generate_character_sql.py
   ```

2. 提交更改：
   ```bash
   git add backend/biblical_characters_seed.sql
   git commit -m "data: update biblical characters seed data"
   git push
   ```

3. 重新执行 SQL 到 Neon 数据库（使用方法一或方法二）

### 注意事项

1. **ID 冲突处理**：SQL 使用 `ON CONFLICT DO NOTHING` 或 `ON CONFLICT DO UPDATE`，可以安全地重复执行
2. **事务安全**：每个 INSERT 语句独立执行，部分失败不会影响其他数据
3. **Neon 限制**：免费版有连接数限制，大量数据插入可能需要分批执行
