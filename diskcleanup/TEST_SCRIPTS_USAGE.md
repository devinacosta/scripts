# Disk Cleanup Test Scripts

This directory contains scripts to help validate your disk cleanup functionality.

## Scripts

### `generate_test_files.sh`
Creates test files based on your `diskcleanup.yaml` configuration to validate cleanup scenarios.

**What it creates:**
- Files with target extensions (`.tar.gz`, `.gz`, date patterns)
- Large files exceeding the 2 GiB limit
- Old files exceeding the 30-day age limit
- ABRT crash files in `/var/log/crash/abrt`
- Specific monitored log files
- Directory-specific pattern files
- Control files that should be preserved

### `cleanup_test_files.sh`
Removes all test files and directories created by the generator script.

## Usage

1. **Generate test files:**
   ```bash
   sudo ./generate_test_files.sh
   ```
   (sudo is needed for creating files in `/var/log` and other system directories)

2. **Run your disk cleanup script:**
   ```bash
   sudo python diskcleanup.py
   ```

3. **Verify results:**
   Check that appropriate files were cleaned up and preserved files remain

4. **Clean up test files:**
   ```bash
   sudo ./cleanup_test_files.sh
   ```

## Expected Results

After running your disk cleanup script, you should see:

**Files that SHOULD be cleaned up:**
- `/var/log/old_backup.tar.gz` (35 days old)
- `/var/log/compressed_log.gz` (40 days old)
- `/var/log/logfile-20240101` (45 days old)
- `/var/log/huge_log_old.log` (3 GiB, 35 days old)
- `/var/log/huge_log_recent.log` (3 GiB, recent)
- `/var/log/very_old_file.txt` (50 days old)
- `/var/log/old_file.txt` (35 days old)
- ABRT directories with 35+ day age OR 80MB+ size (directory names use dynamic dates)
- `/var/log/mysqld.log` (truncated if over 5 MiB)
- `/var/log/haproxy/haproxy-old.log` and `/var/log/haproxy/haproxy-very-old.log` (over 10 days)
- `/var/log/kibana-1/kibana-old.log` and `/var/log/kibana-1/kibana-very-old.log` (over 3 days)

**Files that SHOULD be preserved:**
- `/var/log/recent_backup.tar.gz` (5 days old, under 30-day limit)
- `/var/log/recent_compressed.gz` (10 days old, under 30-day limit)
- `/var/log/logfile-20241215` (2 days old, under 30-day limit)
- `/var/log/recent_file.txt` (5 days old, under 30-day limit)
- `/var/log/recent_important.log` (1 day old, under size/age limits)
- `/var/log/medium_recent.txt` (5 days old, under 30-day limit)
- `/var/log/recent_system.log` (2 days old, under size/age limits)
- `/var/log/haproxy/haproxy-recent.log` (2 days old, under 10-day limit)
- `/var/log/kibana-1/kibana-recent.log` (1 day old, under 3-day limit)
- One ABRT directory (3 days old, 10MB - under both limits)
- Files not matching cleanup patterns

## Notes

- The scripts handle both Linux and macOS date commands
- Some operations may require sudo privileges
- Files are created with realistic sizes and timestamps
- The generator creates both positive and negative test cases 