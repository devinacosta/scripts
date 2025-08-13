#!/usr/bin/env python3
"""
Password Migration Helper Script

This script helps migrate from explicit passwords to environment-based passwords
in the elastic_servers.yml configuration file.

Usage:
    python3 migrate_passwords.py [--dry-run] [--backup]
    
Options:
    --dry-run    Show what would be changed without making changes
    --backup     Create a backup of the original file
"""

import yaml
import argparse
import os
from datetime import datetime
from collections import defaultdict

def load_config(config_file):
    """Load the YAML configuration file."""
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)

def save_config(config, config_file):
    """Save the YAML configuration file."""
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

def analyze_passwords(config):
    """Analyze current password usage and suggest environment groupings."""
    servers = config.get('servers', [])
    password_analysis = defaultdict(list)
    
    for server in servers:
        if 'elastic_password' in server:
            env = server.get('env', 'unknown')
            username = server.get('elastic_username', 'unknown')
            password = server['elastic_password']
            
            key = f"{env}.{username}"
            password_analysis[key].append({
                'name': server.get('name'),
                'password': password,
                'env': env,
                'username': username
            })
    
    return password_analysis

def suggest_password_section(password_analysis):
    """Suggest a passwords section based on current usage."""
    suggested_passwords = defaultdict(dict)
    
    for key, servers in password_analysis.items():
        env, username = key.split('.', 1)
        if env != 'unknown' and username != 'unknown':
            # Use the most common password for this env/username combination
            password_counts = defaultdict(int)
            for server in servers:
                password_counts[server['password']] += 1
            
            most_common_password = max(password_counts, key=password_counts.get)
            suggested_passwords[env][username] = most_common_password
    
    return dict(suggested_passwords)

def create_migration_plan(config, dry_run=True):
    """Create a migration plan."""
    print("🔍 Analyzing current password configuration...\n")
    
    password_analysis = analyze_passwords(config)
    suggested_passwords = suggest_password_section(password_analysis)
    
    print("📊 Password Analysis Results:")
    print("=" * 50)
    
    total_servers = len(config.get('servers', []))
    servers_with_passwords = sum(len(servers) for servers in password_analysis.values())
    
    print(f"Total servers: {total_servers}")
    print(f"Servers with explicit passwords: {servers_with_passwords}")
    print(f"Unique env/username combinations: {len(password_analysis)}")
    print()
    
    # Show current password usage
    for key, servers in password_analysis.items():
        env, username = key.split('.', 1)
        print(f"🔑 {key}:")
        print(f"   Servers: {', '.join([s['name'] for s in servers])}")
        
        # Check for password consistency
        passwords = set(s['password'] for s in servers)
        if len(passwords) > 1:
            print(f"   ⚠️  WARNING: Multiple passwords found for same env/username!")
            for i, password in enumerate(passwords, 1):
                matching_servers = [s['name'] for s in servers if s['password'] == password]
                print(f"   Password {i}: {password[:20]}... (servers: {', '.join(matching_servers)})")
        else:
            print(f"   Password: {list(passwords)[0][:20]}...")
        print()
    
    print("💡 Suggested passwords section:")
    print("=" * 50)
    print("passwords:")
    for env, usernames in suggested_passwords.items():
        print(f"  {env}:")
        for username, password in usernames.items():
            print(f"    {username}: \"{password}\"")
    print()
    
    # Show migration plan for servers
    print("🔄 Server migration plan:")
    print("=" * 50)
    
    migration_count = 0
    for server in config.get('servers', []):
        name = server.get('name')
        env = server.get('env')
        username = server.get('elastic_username')
        
        if 'elastic_password' in server and env and env != 'unknown' and username:
            migration_count += 1
            print(f"✅ {name}: Can migrate to environment-based password")
            print(f"   Current: explicit password")
            print(f"   New: use_env_password: true (will use passwords.{env}.{username})")
            print()
        elif 'elastic_password' in server:
            print(f"⚠️  {name}: Requires manual review")
            if not env:
                print(f"   Issue: No 'env' field specified")
            if not username:
                print(f"   Issue: No 'elastic_username' field specified")
            print()
    
    print(f"📈 Migration Summary:")
    print(f"   Servers ready for auto-migration: {migration_count}")
    print(f"   Servers requiring manual review: {servers_with_passwords - migration_count}")
    
    return suggested_passwords, migration_count > 0

def perform_migration(config, suggested_passwords, backup_file=None):
    """Perform the actual migration."""
    if backup_file:
        print(f"💾 Creating backup: {backup_file}")
        save_config(config, backup_file)
    
    # Add or update passwords section
    config['passwords'] = suggested_passwords
    
    # Update servers to use environment-based passwords
    migrated_count = 0
    for server in config.get('servers', []):
        env = server.get('env')
        username = server.get('elastic_username')
        
        if 'elastic_password' in server and env and username:
            if env in suggested_passwords and username in suggested_passwords[env]:
                # Remove explicit password and add use_env_password flag
                del server['elastic_password']
                server['use_env_password'] = True
                migrated_count += 1
                print(f"✅ Migrated {server.get('name')} to environment-based password")
    
    print(f"\n🎉 Migration completed! Migrated {migrated_count} servers.")
    return config

def main():
    parser = argparse.ArgumentParser(description='Migrate to environment-based passwords')
    parser.add_argument('--dry-run', action='store_true', help='Show what would change without making changes')
    parser.add_argument('--backup', action='store_true', help='Create backup before migration')
    parser.add_argument('--config', default='elastic_servers.yml', help='Configuration file path')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.config):
        print(f"❌ Configuration file not found: {args.config}")
        return 1
    
    # Load current configuration
    config = load_config(args.config)
    
    # Create migration plan
    suggested_passwords, can_migrate = create_migration_plan(config, args.dry_run)
    
    if not can_migrate:
        print("ℹ️  No servers are ready for automatic migration.")
        print("   Please review the analysis above and update configurations manually.")
        return 0
    
    if args.dry_run:
        print("🔍 DRY RUN: No changes were made.")
        print("   Run without --dry-run to perform the migration.")
        return 0
    
    # Confirm migration
    response = input("\n❓ Proceed with migration? (y/N): ").strip().lower()
    if response != 'y':
        print("❌ Migration cancelled.")
        return 0
    
    # Perform migration
    backup_file = None
    if args.backup:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{args.config}.backup_{timestamp}"
    
    updated_config = perform_migration(config, suggested_passwords, backup_file)
    
    # Save updated configuration
    save_config(updated_config, args.config)
    print(f"💾 Updated configuration saved to: {args.config}")
    
    print("\n📝 Next steps:")
    print("1. Review the updated configuration file")
    print("2. Test connectivity to a few clusters")
    print("3. Update remaining servers manually as needed")
    print("4. Consider removing old explicit passwords once migration is complete")

if __name__ == '__main__':
    exit(main())
