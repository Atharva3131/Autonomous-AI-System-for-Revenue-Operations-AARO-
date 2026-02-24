#!/usr/bin/env python3
"""
Database migration script for ABOA system.
Handles database schema creation, updates, and data migrations.
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path
from typing import List, Dict, Any
import logging

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from aboa.core.config import get_settings
from aboa.core.logging import setup_logging, get_logger

# Migration versions and their corresponding SQL files
MIGRATIONS = {
    "001": "001_initial_schema.sql",
    "002": "002_add_indexes.sql", 
    "003": "003_add_audit_tables.sql",
}

logger = get_logger(__name__)


class DatabaseMigrator:
    """Handles database migrations for the ABOA system."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.migrations_dir = Path(__file__).parent / "migrations"
        self.migrations_dir.mkdir(exist_ok=True)
        
    async def get_connection(self):
        """Get database connection based on URL type."""
        if self.database_url.startswith("postgresql"):
            import asyncpg
            return await asyncpg.connect(self.database_url)
        elif self.database_url.startswith("sqlite"):
            import aiosqlite
            db_path = self.database_url.replace("sqlite:///", "")
            # Create directory if it doesn't exist
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            return await aiosqlite.connect(db_path)
        else:
            raise ValueError(f"Unsupported database URL: {self.database_url}")
    
    async def create_migration_table(self, conn):
        """Create the migrations tracking table."""
        if self.database_url.startswith("postgresql"):
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(50) PRIMARY KEY,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    checksum VARCHAR(64)
                )
            """)
        else:  # SQLite
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    checksum TEXT
                )
            """)
    
    async def get_applied_migrations(self, conn) -> List[str]:
        """Get list of already applied migrations."""
        try:
            if self.database_url.startswith("postgresql"):
                rows = await conn.fetch("SELECT version FROM schema_migrations ORDER BY version")
                return [row['version'] for row in rows]
            else:  # SQLite
                async with conn.execute("SELECT version FROM schema_migrations ORDER BY version") as cursor:
                    rows = await cursor.fetchall()
                    return [row[0] for row in rows]
        except Exception:
            # Table doesn't exist yet
            return []
    
    async def apply_migration(self, conn, version: str, sql_content: str):
        """Apply a single migration."""
        import hashlib
        
        checksum = hashlib.sha256(sql_content.encode()).hexdigest()
        
        logger.info(f"Applying migration {version}")
        
        if self.database_url.startswith("postgresql"):
            # PostgreSQL supports transactions for DDL
            async with conn.transaction():
                await conn.execute(sql_content)
                await conn.execute(
                    "INSERT INTO schema_migrations (version, checksum) VALUES ($1, $2)",
                    version, checksum
                )
        else:  # SQLite
            # Execute SQL statements one by one for SQLite
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            for statement in statements:
                await conn.execute(statement)
            
            await conn.execute(
                "INSERT INTO schema_migrations (version, checksum) VALUES (?, ?)",
                (version, checksum)
            )
            await conn.commit()
        
        logger.info(f"Migration {version} applied successfully")
    
    async def run_migrations(self):
        """Run all pending migrations."""
        conn = await self.get_connection()
        
        try:
            await self.create_migration_table(conn)
            applied_migrations = await self.get_applied_migrations(conn)
            
            # Check if we should run the initial schema
            if not applied_migrations:
                logger.info("No migrations found, running initial schema setup")
                init_sql_path = Path(__file__).parent / "init-db.sql"
                if init_sql_path.exists():
                    with open(init_sql_path, 'r') as f:
                        sql_content = f.read()
                    await self.apply_migration(conn, "000_initial", sql_content)
            
            # Run additional migrations
            for version, filename in sorted(MIGRATIONS.items()):
                if version not in applied_migrations:
                    migration_path = self.migrations_dir / filename
                    if migration_path.exists():
                        with open(migration_path, 'r') as f:
                            sql_content = f.read()
                        await self.apply_migration(conn, version, sql_content)
                    else:
                        logger.warning(f"Migration file not found: {migration_path}")
            
            logger.info("All migrations completed successfully")
            
        finally:
            await conn.close()
    
    async def rollback_migration(self, version: str):
        """Rollback a specific migration (if rollback script exists)."""
        rollback_path = self.migrations_dir / f"{version}_rollback.sql"
        if not rollback_path.exists():
            raise ValueError(f"No rollback script found for migration {version}")
        
        conn = await self.get_connection()
        
        try:
            with open(rollback_path, 'r') as f:
                sql_content = f.read()
            
            logger.info(f"Rolling back migration {version}")
            
            if self.database_url.startswith("postgresql"):
                async with conn.transaction():
                    await conn.execute(sql_content)
                    await conn.execute(
                        "DELETE FROM schema_migrations WHERE version = $1", version
                    )
            else:  # SQLite
                statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
                for statement in statements:
                    await conn.execute(statement)
                
                await conn.execute(
                    "DELETE FROM schema_migrations WHERE version = ?", (version,)
                )
                await conn.commit()
            
            logger.info(f"Migration {version} rolled back successfully")
            
        finally:
            await conn.close()
    
    async def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status."""
        conn = await self.get_connection()
        
        try:
            await self.create_migration_table(conn)
            applied_migrations = await self.get_applied_migrations(conn)
            
            status = {
                "applied_migrations": applied_migrations,
                "pending_migrations": [],
                "total_migrations": len(MIGRATIONS)
            }
            
            for version in sorted(MIGRATIONS.keys()):
                if version not in applied_migrations:
                    status["pending_migrations"].append(version)
            
            return status
            
        finally:
            await conn.close()


async def main():
    """Main migration script entry point."""
    parser = argparse.ArgumentParser(description="ABOA Database Migration Tool")
    parser.add_argument(
        "command",
        choices=["migrate", "rollback", "status", "create"],
        help="Migration command to execute"
    )
    parser.add_argument(
        "--version",
        help="Migration version (for rollback command)"
    )
    parser.add_argument(
        "--name",
        help="Migration name (for create command)"
    )
    parser.add_argument(
        "--database-url",
        help="Database URL (overrides config)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging("INFO", "text", None)
    
    # Get database URL
    settings = get_settings()
    database_url = args.database_url or settings.database_url
    
    if not database_url:
        logger.error("No database URL provided. Set DATABASE_URL environment variable or use --database-url")
        sys.exit(1)
    
    migrator = DatabaseMigrator(database_url)
    
    try:
        if args.command == "migrate":
            await migrator.run_migrations()
        
        elif args.command == "rollback":
            if not args.version:
                logger.error("Version required for rollback command")
                sys.exit(1)
            await migrator.rollback_migration(args.version)
        
        elif args.command == "status":
            status = await migrator.get_migration_status()
            print(f"Applied migrations: {len(status['applied_migrations'])}")
            print(f"Pending migrations: {len(status['pending_migrations'])}")
            if status['pending_migrations']:
                print(f"Pending: {', '.join(status['pending_migrations'])}")
        
        elif args.command == "create":
            if not args.name:
                logger.error("Name required for create command")
                sys.exit(1)
            
            # Generate next version number
            next_version = str(len(MIGRATIONS) + 1).zfill(3)
            filename = f"{next_version}_{args.name.replace(' ', '_').lower()}.sql"
            migration_path = migrator.migrations_dir / filename
            
            # Create migration template
            template = f"""-- Migration: {args.name}
-- Version: {next_version}
-- Created: {asyncio.get_event_loop().time()}

-- Add your migration SQL here

"""
            
            with open(migration_path, 'w') as f:
                f.write(template)
            
            print(f"Created migration: {migration_path}")
    
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())