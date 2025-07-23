#!/bin/bash

# Cleanup script to remove all test files created by generate_test_files.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Test File Cleanup Script ===${NC}"
echo "This script will remove all test files created by generate_test_files.sh"
echo

# Function to safely remove directory if it exists
remove_dir() {
    local dir="$1"
    if [[ -d "$dir" ]]; then
        echo -e "${YELLOW}Removing directory: $dir${NC}"
        sudo rm -rf "$dir" 2>/dev/null || rm -rf "$dir" 2>/dev/null || {
            echo -e "${RED}Warning: Could not remove $dir${NC}"
        }
    fi
}

# Function to safely remove file if it exists
remove_file() {
    local file="$1"
    if [[ -f "$file" ]]; then
        echo -e "${YELLOW}Removing file: $file${NC}"
        sudo rm -f "$file" 2>/dev/null || rm -f "$file" 2>/dev/null || {
            echo -e "${RED}Warning: Could not remove $file${NC}"
        }
    fi
}

echo -e "${GREEN}Removing test directories and files...${NC}"

# Remove ABRT test directories (using wildcards since dates are dynamic)
echo -e "${YELLOW}Removing ABRT test directories...${NC}"
sudo rm -rf /var/log/crash/abrt/ccpp-* 2>/dev/null || true
sudo rm -rf /var/log/crash/abrt/python3-* 2>/dev/null || true
sudo rm -rf /var/log/crash/abrt/httpd-* 2>/dev/null || true
sudo rm -rf /var/log/crash/abrt/mysqld-* 2>/dev/null || true
sudo rm -rf /var/log/crash/abrt/nginx-* 2>/dev/null || true
remove_dir "/var/log/crash/abrt"
remove_dir "/var/log/haproxy"
remove_dir "/var/log/kibana-1"

# Remove specific test files from /var/log/
remove_file "/var/log/old_backup.tar.gz"
remove_file "/var/log/recent_backup.tar.gz"
remove_file "/var/log/compressed_log.gz"
remove_file "/var/log/recent_compressed.gz"
remove_file "/var/log/logfile-20240101"
remove_file "/var/log/logfile-20241215"
remove_file "/var/log/huge_log_old.log"
remove_file "/var/log/huge_log_recent.log"
remove_file "/var/log/very_old_file.txt"
remove_file "/var/log/old_file.txt"
remove_file "/var/log/recent_file.txt"
remove_file "/var/log/recent_important.log"
remove_file "/var/log/medium_recent.txt"
remove_file "/var/log/recent_system.log"
remove_file "/var/log/mysqld.log"

# Remove other monitored directories and files
remove_dir "/var/log/mysql"
remove_dir "/var/log/ringcentral"
remove_dir "/var/log/kibana"

# Remove any remaining crash directory if empty
if [[ -d "/var/log/crash" ]]; then
    rmdir "/var/log/crash" 2>/dev/null || true
fi

echo
echo -e "${GREEN}=== Test File Cleanup Complete ===${NC}"
echo "All test files and directories have been removed."
echo -e "${YELLOW}Note: Original system files and directories were preserved.${NC}" 