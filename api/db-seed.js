import { Pool } from '@neondatabase/serverless';
import fs from 'fs';
import path from 'path';

/**
 * Database Seeding API Endpoint
 * 
 * GET /api/db-seed?token=YOUR_ADMIN_TOKEN
 * 
 * This endpoint executes the biblical_characters_seed.sql file against the Neon database.
 * Used for initial deployment and updates to the biblical characters data.
 * 
 * Environment Variables:
 * - DATABASE_URL: Neon PostgreSQL connection string
 * - ADMIN_TOKEN: Secret token to authorize this operation
 */

export default async function handler(req, res) {
  // Only allow GET requests
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Verify admin token
  const { token } = req.query;
  const adminToken = process.env.ADMIN_TOKEN || process.env.DB_SEED_TOKEN;
  
  if (!adminToken) {
    return res.status(500).json({ 
      error: 'Server configuration error: ADMIN_TOKEN not set' 
    });
  }
  
  if (token !== adminToken) {
    return res.status(401).json({ error: 'Unauthorized: Invalid token' });
  }

  // Check database URL
  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) {
    return res.status(500).json({ 
      error: 'Server configuration error: DATABASE_URL not set' 
    });
  }

  const pool = new Pool({ connectionString: dbUrl });
  
  try {
    // Read SQL file
    const sqlFilePath = path.join(process.cwd(), 'backend', 'biblical_characters_seed.sql');
    
    if (!fs.existsSync(sqlFilePath)) {
      return res.status(404).json({ 
        error: 'SQL file not found: backend/biblical_characters_seed.sql' 
      });
    }
    
    const sql = fs.readFileSync(sqlFilePath, 'utf8');
    
    // Parse and execute SQL statements
    // Split by semicolon but be careful with function definitions
    const statements = [];
    let currentStatement = '';
    let inFunction = false;
    
    const lines = sql.split('\n');
    for (const line of lines) {
      const trimmed = line.trim();
      
      // Skip comments and empty lines for statement splitting
      if (trimmed.startsWith('--') || trimmed.startsWith('/*') || trimmed === '') {
        currentStatement += line + '\n';
        continue;
      }
      
      // Track if we're inside a function definition
      if (trimmed.includes('CREATE OR REPLACE FUNCTION') || trimmed.includes('$$')) {
        inFunction = !inFunction;
      }
      
      currentStatement += line + '\n';
      
      // End of statement (semicolon not in function)
      if (trimmed.endsWith(';') && !inFunction) {
        statements.push(currentStatement.trim());
        currentStatement = '';
      }
    }
    
    // Execute statements
    const results = [];
    let successCount = 0;
    let errorCount = 0;
    
    for (const statement of statements) {
      if (!statement || statement.startsWith('--') || statement.startsWith('/*')) {
        continue;
      }
      
      try {
        await pool.query(statement);
        successCount++;
        results.push({ 
          status: 'success', 
          preview: statement.slice(0, 60).replace(/\n/g, ' ') + '...' 
        });
      } catch (err) {
        errorCount++;
        results.push({ 
          status: 'error', 
          error: err.message,
          preview: statement.slice(0, 60).replace(/\n/g, ' ') + '...'
        });
      }
    }
    
    // Verify data was loaded
    const verifyQueries = await Promise.all([
      pool.query('SELECT COUNT(*) as count FROM biblical_characters'),
      pool.query('SELECT COUNT(*) as count FROM character_themes'),
      pool.query('SELECT COUNT(*) as count FROM character_tags')
    ]);
    
    await pool.end();
    
    res.json({ 
      success: true, 
      message: 'Database seeding completed',
      summary: {
        statementsExecuted: successCount + errorCount,
        successful: successCount,
        errors: errorCount,
        dataLoaded: {
          characters: parseInt(verifyQueries[0].rows[0].count),
          themes: parseInt(verifyQueries[1].rows[0].count),
          tags: parseInt(verifyQueries[2].rows[0].count)
        }
      },
      results: results.slice(0, 20), // Limit results in response
      note: errorCount === 0 
        ? 'All statements executed successfully'
        : `${errorCount} statement(s) failed. Check logs for details.`
    });
    
  } catch (error) {
    try {
      await pool.end();
    } catch (e) {
      // Ignore pool end error
    }
    
    res.status(500).json({ 
      success: false, 
      error: error.message,
      stack: process.env.NODE_ENV === 'development' ? error.stack : undefined
    });
  }
}
