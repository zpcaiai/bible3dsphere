#!/bin/bash
# ============================================================================
# SFDS Database Migration Script
# ============================================================================
# Usage: ./sfds_migration.sh [command]
# Commands:
#   setup       - Full setup (core schema + indexes + seed data)
#   migrate     - Run core schema + indexes
#   seed        - Load seed data only
#   reset       - Reset all SFDS tables (WARNING: Data loss!)
#   verify      - Verify installation
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-bible_sphere}"
DB_USER="${DB_USER:-postgres}"
DB_URL="${DATABASE_URL:-postgresql://${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  SFDS Database Migration Tool${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo -e "${RED}Error: psql is not installed${NC}"
    exit 1
fi

# Check database connection
echo -e "${YELLOW}Checking database connection...${NC}"
if ! psql "$DB_URL" -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${RED}Error: Cannot connect to database${NC}"
    echo "Please check your DATABASE_URL or set DB_HOST, DB_PORT, DB_NAME, DB_USER"
    exit 1
fi
echo -e "${GREEN}✓ Database connection successful${NC}"
echo ""

# Function to execute SQL file
execute_sql() {
    local file=$1
    local description=$2
    
    echo -e "${YELLOW}Executing: $description${NC}"
    if psql "$DB_URL" -f "$file" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ $description completed${NC}"
        return 0
    else
        echo -e "${RED}✗ $description failed${NC}"
        return 1
    fi
}

# Function to check if tables exist
check_tables() {
    local result=$(psql "$DB_URL" -t -c "
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE 'sfds_%'
    " 2>/dev/null | xargs)
    echo "$result"
}

# Setup command - Full installation
setup() {
    echo -e "${BLUE}Running full SFDS setup...${NC}"
    echo ""
    
    # Check if already installed
    local existing_tables=$(check_tables)
    if [ "$existing_tables" -gt 0 ]; then
        echo -e "${YELLOW}Warning: $existing_tables SFDS tables already exist${NC}"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Setup cancelled"
            exit 0
        fi
    fi
    
    # Execute in order
    execute_sql "$SCRIPT_DIR/sfds_schema_core.sql" "Core schema (tables)" || exit 1
    execute_sql "$SCRIPT_DIR/sfds_schema_indexes_triggers.sql" "Indexes and triggers" || exit 1
    execute_sql "$SCRIPT_DIR/sfds_schema_seed_data.sql" "Seed data" || exit 1
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  SFDS Setup Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    verify
}

# Migrate command - Core schema only
migrate() {
    echo -e "${BLUE}Running migration (schema + indexes)...${NC}"
    echo ""
    
    execute_sql "$SCRIPT_DIR/sfds_schema_core.sql" "Core schema" || exit 1
    execute_sql "$SCRIPT_DIR/sfds_schema_indexes_triggers.sql" "Indexes and triggers" || exit 1
    
    echo ""
    echo -e "${GREEN}Migration completed successfully${NC}"
}

# Seed command - Load seed data
seed() {
    echo -e "${BLUE}Loading seed data...${NC}"
    echo ""
    
    execute_sql "$SCRIPT_DIR/sfds_schema_seed_data.sql" "Seed data" || exit 1
    
    echo ""
    echo -e "${GREEN}Seed data loaded successfully${NC}"
}

# Reset command - Drop and recreate
reset() {
    echo -e "${RED}WARNING: This will DELETE all SFDS data!${NC}"
    read -p "Are you sure? Type 'RESET' to confirm: " confirm
    
    if [ "$confirm" != "RESET" ]; then
        echo "Reset cancelled"
        exit 0
    fi
    
    echo -e "${YELLOW}Dropping SFDS tables...${NC}"
    
    psql "$DB_URL" << 'EOF'
-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS sfds_audit_log CASCADE;
DROP TABLE IF EXISTS sfds_user_patterns CASCADE;
DROP TABLE IF EXISTS sfds_spiritual_metrics CASCADE;
DROP TABLE IF EXISTS sfds_decision_reviews CASCADE;
DROP TABLE IF EXISTS sfds_decision_principles CASCADE;
DROP TABLE IF EXISTS sfds_guidance_outputs CASCADE;
DROP TABLE IF EXISTS sfds_discernment_results CASCADE;
DROP TABLE IF EXISTS sfds_motive_analyses CASCADE;
DROP TABLE IF EXISTS sfds_emotion_logs CASCADE;
DROP TABLE IF EXISTS sfds_state_snapshots CASCADE;
DROP TABLE IF EXISTS sfds_spiritual_principles CASCADE;
DROP TABLE IF EXISTS sfds_decision_events CASCADE;
DROP TABLE IF EXISTS sfds_users CASCADE;

-- Drop views
DROP VIEW IF EXISTS sfds_user_decision_summary CASCADE;
DROP VIEW IF EXISTS sfds_high_risk_decisions CASCADE;
DROP VIEW IF EXISTS sfds_recent_emotion_patterns CASCADE;
DROP VIEW IF EXISTS sfds_spiritual_health_trends CASCADE;
DROP VIEW IF EXISTS sfds_motive_distribution CASCADE;
DROP VIEW IF EXISTS sfds_source_distribution CASCADE;
DROP VIEW IF EXISTS sfds_principle_effectiveness CASCADE;

-- Drop functions
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
DROP FUNCTION IF EXISTS update_user_decision_count() CASCADE;
DROP FUNCTION IF EXISTS update_principle_reference_count() CASCADE;
DROP FUNCTION IF EXISTS update_principle_search_vector() CASCADE;
DROP FUNCTION IF EXISTS calculate_decision_readiness(INTEGER, INTEGER, INTEGER, INTEGER, INTEGER) CASCADE;
EOF
    
    echo -e "${GREEN}✓ Tables dropped${NC}"
    echo ""
    
    # Re-run setup
    setup
}

# Verify command - Check installation
verify() {
    echo -e "${BLUE}Verifying SFDS installation...${NC}"
    echo ""
    
    local tables=$(psql "$DB_URL" -t -c "
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE 'sfds_%'
        ORDER BY table_name
    " 2>/dev/null | xargs -I {} echo "  {}")
    
    local table_count=$(check_tables)
    
    echo -e "${GREEN}Found $table_count SFDS tables:${NC}"
    echo "$tables"
    echo ""
    
    # Check views
    local views=$(psql "$DB_URL" -t -c "
        SELECT table_name 
        FROM information_schema.views 
        WHERE table_schema = 'public' 
        AND table_name LIKE 'sfds_%'
        ORDER BY table_name
    " 2>/dev/null | xargs -I {} echo "  {}")
    
    echo -e "${GREEN}SFDS Views:${NC}"
    echo "$views"
    echo ""
    
    # Check seed data
    local principle_count=$(psql "$DB_URL" -t -c "SELECT COUNT(*) FROM sfds_spiritual_principles" 2>/dev/null | xargs)
    local user_count=$(psql "$DB_URL" -t -c "SELECT COUNT(*) FROM sfds_users WHERE email = 'demo@sfds.example'" 2>/dev/null | xargs)
    local decision_count=$(psql "$DB_URL" -t -c "SELECT COUNT(*) FROM sfds_decision_events" 2>/dev/null | xargs)
    
    echo -e "${GREEN}Seed Data:${NC}"
    echo "  Spiritual Principles: $principle_count"
    echo "  Demo Users: $user_count"
    echo "  Demo Decisions: $decision_count"
    echo ""
    
    # Check pgvector
    local pgvector_installed=$(psql "$DB_URL" -t -c "SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector'" 2>/dev/null | xargs)
    if [ "$pgvector_installed" -eq 1 ]; then
        echo -e "${GREEN}✓ pgvector extension installed${NC}"
    else
        echo -e "${RED}✗ pgvector extension NOT installed${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}Verification complete${NC}"
}

# Help command
help() {
    cat << 'EOF'
Usage: ./sfds_migration.sh [command]

Commands:
  setup       Full setup (tables + indexes + seed data)
  migrate     Run schema migration only (tables + indexes)
  seed        Load seed data only
  reset       Reset all tables and recreate (WARNING: Data loss!)
  verify      Verify installation status
  help        Show this help message

Environment Variables:
  DATABASE_URL    Full PostgreSQL connection URL
  DB_HOST         Database host (default: localhost)
  DB_PORT         Database port (default: 5432)
  DB_NAME         Database name (default: bible_sphere)
  DB_USER         Database user (default: postgres)

Examples:
  ./sfds_migration.sh setup
  DATABASE_URL=postgres://user:pass@localhost/db ./sfds_migration.sh migrate
  ./sfds_migration.sh verify

EOF
}

# Main command handler
case "${1:-help}" in
    setup)
        setup
        ;;
    migrate)
        migrate
        ;;
    seed)
        seed
        ;;
    reset)
        reset
        ;;
    verify)
        verify
        ;;
    help|--help|-h)
        help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        help
        exit 1
        ;;
esac
