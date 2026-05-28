#!/usr/bin/env node
/**
 * Neon Database Seeding Script
 * 
 * Usage: node scripts/seed-neon.js [DATABASE_URL]
 * 
 * If DATABASE_URL is not provided as argument, it will use the DATABASE_URL env var.
 * 
 * This script executes the biblical_characters_seed.sql file against a Neon database.
 */

import { Pool } from '@neondatabase/serverless';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function seedDatabase() {
  const dbUrl = process.argv[2] || process.env.DATABASE_URL;
  
  if (!dbUrl) {
    console.error('Error: DATABASE_URL not provided');
    console.error('Usage: node seed-neon.js "postgresql://user:pass@host/db?sslmode=require"');
    console.error('   or: DATABASE_URL=postgresql://... node seed-neon.js');
    process.exit(1);
  }

  console.log('Connecting to database...');
  const pool = new Pool({ connectionString: dbUrl });

  try {
    // Read SQL file
    const sqlFilePath = path.join(__dirname, '..', 'backend', 'biblical_characters_seed.sql');
    
    if (!fs.existsSync(sqlFilePath)) {
      console.error(`Error: SQL file not found: ${sqlFilePath}`);
      process.exit(1);
    }
    
    console.log(`Reading SQL file: ${sqlFilePath}`);
    const sql = fs.readFileSync(sqlFilePath, 'utf8');
    
    // Simple parsing: split by semicolons that are at end of line
    const statements = sql
      .split(';')
      .map(s => s.trim())
      .filter(s => s.length > 0 && !s.startsWith('--') && !s.startsWith('/*'));
    
    console.log(`Found ${statements.length} SQL statements to execute`);
    console.log('Executing...\n');
    
    let successCount = 0;
    let errorCount = 0;
    const errors = [];
    
    for (let i = 0; i < statements.length; i++) {
      const statement = statements[i];
      const preview = statement.slice(0, 50).replace(/\n/g, ' ');
      
      try {
        await pool.query(statement + ';');
        successCount++;
        process.stdout.write(`[${i + 1}/${statements.length}] ✓ ${preview}...\n`);
      } catch (err) {
        errorCount++;
        errors.push({ statement: preview, error: err.message });
        process.stdout.write(`[${i + 1}/${statements.length}] ✗ ${preview}...\n`);
        process.stdout.write(`  Error: ${err.message}\n`);
      }
    }
    
    console.log('\n-------------------------------------------');
    console.log('Seeding completed!');
    console.log(`Total statements: ${statements.length}`);
    console.log(`Successful: ${successCount}`);
    console.log(`Errors: ${errorCount}`);
    
    // Verify data
    console.log('\nVerifying data...');
    const verifyResults = await Promise.all([
      pool.query('SELECT COUNT(*) as count FROM biblical_characters'),
      pool.query('SELECT COUNT(*) as count FROM character_themes'),
      pool.query('SELECT COUNT(*) as count FROM character_tags'),
      pool.query('SELECT COUNT(*) as count FROM character_follow_points'),
      pool.query('SELECT COUNT(*) as count FROM character_scriptures')
    ]);
    
    console.log('\nData loaded:');
    console.log(`  - Characters: ${verifyResults[0].rows[0].count}`);
    console.log(`  - Themes: ${verifyResults[1].rows[0].count}`);
    console.log(`  - Tags: ${verifyResults[2].rows[0].count}`);
    console.log(`  - Follow points: ${verifyResults[3].rows[0].count}`);
    console.log(`  - Scriptures: ${verifyResults[4].rows[0].count}`);
    
    if (errorCount > 0) {
      console.log('\nErrors encountered:');
      errors.forEach((e, i) => {
        console.log(`  ${i + 1}. ${e.statement}...`);
        console.log(`     ${e.error}`);
      });
    }
    
    await pool.end();
    
    if (errorCount > 0) {
      process.exit(1);
    }
    
    console.log('\n✅ Database seeded successfully!');
    
  } catch (error) {
    console.error('\n❌ Fatal error:', error.message);
    try {
      await pool.end();
    } catch (e) {
      // Ignore
    }
    process.exit(1);
  }
}

seedDatabase();
