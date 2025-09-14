#!/usr/bin/env python3
"""
Migration management script for Bookings Service.
Provides convenient commands for database migrations.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent))

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False

def init_migration(message):
    """Create a new migration."""
    return run_command(
        f'alembic revision --autogenerate -m "{message}"',
        f"Creating migration: {message}"
    )

def upgrade_migration(revision="head"):
    """Apply migrations."""
    return run_command(
        f"alembic upgrade {revision}",
        f"Upgrading database to {revision}"
    )

def downgrade_migration(revision):
    """Downgrade migrations."""
    return run_command(
        f"alembic downgrade {revision}",
        f"Downgrading database to {revision}"
    )

def show_current_revision():
    """Show current database revision."""
    return run_command(
        "alembic current",
        "Showing current database revision"
    )

def show_migration_history():
    """Show migration history."""
    return run_command(
        "alembic history",
        "Showing migration history"
    )

def main():
    parser = argparse.ArgumentParser(description="Bookings Service Migration Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create migration
    create_parser = subparsers.add_parser("create", help="Create a new migration")
    create_parser.add_argument("message", help="Migration message")
    
    # Upgrade
    upgrade_parser = subparsers.add_parser("upgrade", help="Apply migrations")
    upgrade_parser.add_argument("--revision", default="head", help="Target revision (default: head)")
    
    # Downgrade
    downgrade_parser = subparsers.add_parser("downgrade", help="Downgrade migrations")
    downgrade_parser.add_argument("revision", help="Target revision")
    
    # Show current
    subparsers.add_parser("current", help="Show current database revision")
    
    # Show history
    subparsers.add_parser("history", help="Show migration history")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Change to the bookings_service directory
    os.chdir(Path(__file__).parent)
    
    if args.command == "create":
        init_migration(args.message)
    elif args.command == "upgrade":
        upgrade_migration(args.revision)
    elif args.command == "downgrade":
        downgrade_migration(args.revision)
    elif args.command == "current":
        show_current_revision()
    elif args.command == "history":
        show_migration_history()

if __name__ == "__main__":
    main()