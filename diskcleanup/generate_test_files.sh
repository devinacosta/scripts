#!/bin/bash

# Test file generator for diskcleanup validation
# This script creates various files to test different cleanup scenarios

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Disk Cleanup Test File Generator ===${NC}"
echo "This script will create test files based on your diskcleanup.yaml configuration"
echo

# Function to create directory if it doesn't exist
create_dir() {
    local dir="$1"
    if [[ ! -d "$dir" ]]; then
        echo -e "${YELLOW}Creating directory: $dir${NC}"
        sudo mkdir -p "$dir" 2>/dev/null || mkdir -p "$dir"
    fi
}

# Function to create file with specific size
create_file_with_size() {
    local filepath="$1"
    local size="$2"
    local age_days="$3"
    
    echo "Creating file: $filepath (size: $size, age: $age_days days)"
    
    # Create directory if needed
    local dir=$(dirname "$filepath")
    create_dir "$dir"
    
    # Create file with specified size
    if [[ "$size" == *"GiB"* ]]; then
        local size_bytes=$(echo "$size" | sed 's/GiB//' | awk '{print $1 * 1024 * 1024 * 1024}')
        dd if=/dev/zero of="$filepath" bs=1M count=$((size_bytes / 1024 / 1024)) 2>/dev/null || \
        head -c "$size_bytes" /dev/zero > "$filepath"
    elif [[ "$size" == *"MiB"* ]] || [[ "$size" == *"MB"* ]]; then
        local size_bytes=$(echo "$size" | sed 's/MiB\|MB//' | awk '{print $1 * 1024 * 1024}')
        head -c "$size_bytes" /dev/zero > "$filepath" 2>/dev/null || \
        dd if=/dev/zero of="$filepath" bs=1024 count=$((size_bytes / 1024)) 2>/dev/null
    else
        # Default small file
        echo "Test file created on $(date)" > "$filepath"
    fi
    
    # Set file age if specified
    if [[ "$age_days" -gt 0 ]]; then
        local timestamp=$(date -d "$age_days days ago" "+%Y%m%d%H%M.%S" 2>/dev/null || \
                         date -j -v-${age_days}d "+%Y%m%d%H%M.%S" 2>/dev/null || \
                         echo "202401010000.00")
        touch -t "$timestamp" "$filepath" 2>/dev/null || true
    fi
}

echo -e "${GREEN}1. Creating files for main cleanup rules${NC}"

echo -e "${YELLOW}Creating files with target extensions (.tar.gz, .gz, date patterns) directly in /var/log${NC}"
create_file_with_size "/var/log/old_backup.tar.gz" "10MiB" 35
create_file_with_size "/var/log/recent_backup.tar.gz" "5MiB" 5
create_file_with_size "/var/log/compressed_log.gz" "8MiB" 40
create_file_with_size "/var/log/recent_compressed.gz" "3MiB" 10
create_file_with_size "/var/log/logfile-20240101" "6MiB" 45
create_file_with_size "/var/log/logfile-20241215" "4MiB" 2

echo -e "${YELLOW}Creating large files (over 2 GiB limit) directly in /var/log${NC}"
create_file_with_size "/var/log/huge_log_old.log" "3GiB" 35
create_file_with_size "/var/log/huge_log_recent.log" "3GiB" 5

echo -e "${YELLOW}Creating old files (over 30 day limit) directly in /var/log${NC}"
create_file_with_size "/var/log/very_old_file.txt" "1MiB" 50
create_file_with_size "/var/log/old_file.txt" "1MiB" 35
create_file_with_size "/var/log/recent_file.txt" "1MiB" 5

echo -e "${GREEN}2. Creating ABRT crash directories${NC}"
create_dir "/var/log/crash/abrt"

echo -e "${YELLOW}Creating ABRT directories (over 30 days and over 50 MB)${NC}"

# Create ABRT directories with proper date patterns and files inside
create_abrt_dir() {
    local dir_name="$1"
    local size="$2"
    local age_days="$3"
    
    local dir_path="/var/log/crash/abrt/$dir_name"
    create_dir "$dir_path"
    create_file_with_size "$dir_path/coredump" "$size" "$age_days"
    create_file_with_size "$dir_path/backtrace" "1KiB" "$age_days"
    create_file_with_size "$dir_path/dso_list" "1KiB" "$age_days"
    
    # Set directory timestamp to match the files
    if [[ "$age_days" -gt 0 ]]; then
        local timestamp=$(date -d "$age_days days ago" "+%Y%m%d%H%M.%S" 2>/dev/null || \
                         date -j -v-${age_days}d "+%Y%m%d%H%M.%S" 2>/dev/null || \
                         echo "202401010000.00")
        touch -t "$timestamp" "$dir_path" 2>/dev/null || true
    fi
}

# Create directories with proper ABRT naming patterns
# Use current date minus the intended age for realistic directory names
current_date=$(date "+%Y-%m-%d")
old_date_35=$(date -d "35 days ago" "+%Y-%m-%d" 2>/dev/null || date -j -v-35d "+%Y-%m-%d" 2>/dev/null || echo "2024-05-19")
old_date_40=$(date -d "40 days ago" "+%Y-%m-%d" 2>/dev/null || date -j -v-40d "+%Y-%m-%d" 2>/dev/null || echo "2024-05-14")
old_date_5=$(date -d "5 days ago" "+%Y-%m-%d" 2>/dev/null || date -j -v-5d "+%Y-%m-%d" 2>/dev/null || echo "2024-07-18")
old_date_3=$(date -d "3 days ago" "+%Y-%m-%d" 2>/dev/null || date -j -v-3d "+%Y-%m-%d" 2>/dev/null || echo "2024-07-20")

create_abrt_dir "ccpp-${old_date_35}-10-30-45-1234" "60MiB" 35
create_abrt_dir "python3-${old_date_40}-15-20-30-5678" "70MiB" 40  
create_abrt_dir "httpd-${old_date_5}-09-45-15-9999" "80MiB" 5
create_abrt_dir "mysqld-${old_date_35}-14-10-25-3333" "10MiB" 35
create_abrt_dir "nginx-${old_date_3}-11-30-50-7777" "10MiB" 3

echo -e "${GREEN}3. Creating specific monitored files${NC}"

echo -e "${YELLOW}Creating mysqld.log (over 5 MiB limit)${NC}"
create_file_with_size "/var/log/mysqld.log" "8MiB" 10

echo -e "${YELLOW}Creating other monitored log files${NC}"
create_file_with_size "/var/log/mysql/mysql-slow.log" "15MiB" 20
create_file_with_size "/var/log/ringcentral/lss/logstash-plain.log" "25MiB" 25
create_file_with_size "/var/log/kibana/kibana.log" "12MiB" 15

echo -e "${GREEN}4. Creating files in specific monitored directories${NC}"

echo -e "${YELLOW}Creating files in haproxy directory (10-day age limit, pattern: haproxy-.*)${NC}"
create_dir "/var/log/haproxy"
create_file_with_size "/var/log/haproxy/haproxy-old.log" "5MiB" 15
create_file_with_size "/var/log/haproxy/haproxy-very-old.log" "8MiB" 20
create_file_with_size "/var/log/haproxy/haproxy-recent.log" "3MiB" 2
create_file_with_size "/var/log/haproxy/other-log.log" "2MiB" 15

echo -e "${YELLOW}Creating files in kibana-1 directory (3-day age limit, pattern: kibana-.*)${NC}"
create_dir "/var/log/kibana-1"
create_file_with_size "/var/log/kibana-1/kibana-old.log" "6MiB" 5
create_file_with_size "/var/log/kibana-1/kibana-very-old.log" "8MiB" 10
create_file_with_size "/var/log/kibana-1/kibana-recent.log" "4MiB" 1
create_file_with_size "/var/log/kibana-1/other-log.log" "2MiB" 10

echo -e "${GREEN}5. Creating control files (should NOT be cleaned up)${NC}"

echo -e "${YELLOW}Creating recent files that should be preserved${NC}"
create_file_with_size "/var/log/recent_important.log" "100MiB" 1
create_file_with_size "/var/log/medium_recent.txt" "500MiB" 5
create_file_with_size "/var/log/recent_system.log" "50MiB" 2

echo
echo -e "${GREEN}=== Test File Generation Complete ===${NC}"
echo -e "${YELLOW}Summary of created test scenarios:${NC}"
echo "✓ Files with target extensions (.tar.gz, .gz, date patterns)"
echo "✓ Large files (over 2 GiB limit)"
echo "✓ Old files (over 30 days)"
echo "✓ ABRT crash files (over size/age limits)"
echo "✓ Specific monitored log files"
echo "✓ Directory-specific pattern files"
echo "✓ Control files (should be preserved)"
echo
echo -e "${GREEN}You can now run your diskcleanup script to validate it works correctly!${NC}"
echo -e "${YELLOW}Expected behavior:${NC}"
echo "- Old and large files should be cleaned up"
echo "- Recent and small files should be preserved"
echo "- Files matching specific patterns in monitored directories should be cleaned"
echo "- Control files should remain untouched"
echo
echo -e "${RED}Note: Some files were created with sudo. You may need sudo to run diskcleanup.${NC}" 
