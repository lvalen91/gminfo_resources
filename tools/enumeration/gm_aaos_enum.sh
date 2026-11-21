#!/bin/bash
#
# GM AAOS Enumeration Script
# Purpose: Gather system information from gminfo3.7 module via ADB
# Handles permission denials gracefully and continues execution
#

set -o pipefail

# Output directory
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="./gm_enum_${TIMESTAMP}"
REPORT_FILE="${OUTPUT_DIR}/enumeration_report.txt"
RAW_DIR="${OUTPUT_DIR}/raw"
PULLED_DIR="${OUTPUT_DIR}/pulled_files"

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create output directories
mkdir -p "$OUTPUT_DIR" "$RAW_DIR" "$PULLED_DIR"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
    echo "[INFO] $1" >> "$REPORT_FILE"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
    echo "[OK] $1" >> "$REPORT_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    echo "[WARN] $1" >> "$REPORT_FILE"
}

log_error() {
    echo -e "${RED}[DENIED]${NC} $1"
    echo "[DENIED] $1" >> "$REPORT_FILE"
}

log_section() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN} $1${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo "" >> "$REPORT_FILE"
    echo "========================================" >> "$REPORT_FILE"
    echo " $1" >> "$REPORT_FILE"
    echo "========================================" >> "$REPORT_FILE"
}

# Execute ADB command with error handling
# Usage: adb_cmd "description" "command" [output_file]
adb_cmd() {
    local desc="$1"
    local cmd="$2"
    local outfile="$3"

    log_info "Executing: $desc"

    if [ -n "$outfile" ]; then
        result=$(adb shell "$cmd" 2>&1)
        exit_code=$?
    else
        result=$(adb shell "$cmd" 2>&1)
        exit_code=$?
    fi

    # Check for permission denied patterns
    if echo "$result" | grep -qi "permission denied\|not allowed\|operation not permitted\|access denied\|cannot\|inaccessible"; then
        log_error "$desc - Access restricted"
        echo "COMMAND: $cmd" >> "${RAW_DIR}/${outfile:-denied.txt}"
        echo "RESULT: $result" >> "${RAW_DIR}/${outfile:-denied.txt}"
        echo "---" >> "${RAW_DIR}/${outfile:-denied.txt}"
        return 1
    elif [ $exit_code -ne 0 ] && [ -z "$result" ]; then
        log_warn "$desc - No output or command failed"
        return 1
    else
        log_success "$desc"
        if [ -n "$outfile" ]; then
            echo "$result" > "${RAW_DIR}/${outfile}"
        fi
        echo "$result" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
        return 0
    fi
}

# Pull file with error handling
adb_pull() {
    local remote_path="$1"
    local desc="$2"

    log_info "Pulling: $desc ($remote_path)"

    local filename=$(basename "$remote_path")
    result=$(adb pull "$remote_path" "${PULLED_DIR}/${filename}" 2>&1)

    if echo "$result" | grep -qi "error\|failed\|denied\|does not exist"; then
        log_error "Failed to pull $remote_path"
        echo "$remote_path: $result" >> "${OUTPUT_DIR}/pull_failures.txt"
        return 1
    else
        log_success "Pulled $filename"
        return 0
    fi
}

# ============================================
# MAIN ENUMERATION START
# ============================================

echo "GM AAOS Enumeration Script"
echo "Output directory: $OUTPUT_DIR"
echo "Started: $(date)"
echo ""

echo "GM AAOS Enumeration Report" > "$REPORT_FILE"
echo "Generated: $(date)" >> "$REPORT_FILE"
echo "Host: $(hostname)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Check ADB connection
log_section "ADB Connection Check"
if ! adb devices | grep -q "device$"; then
    echo -e "${RED}ERROR: No ADB device connected or not authorized${NC}"
    echo "Please ensure:"
    echo "  1. USB debugging is enabled"
    echo "  2. Device is connected"
    echo "  3. ADB authorization is accepted on device"
    exit 1
fi
adb_cmd "Device serial" "getprop ro.serialno" "serial.txt"

# ============================================
# SYSTEM IDENTIFICATION
# ============================================
log_section "System Identification"

adb_cmd "Device model" "getprop ro.product.device"
adb_cmd "Build fingerprint" "getprop ro.build.fingerprint" "fingerprint.txt"
adb_cmd "Build description" "getprop ro.build.description"
adb_cmd "Build ID" "getprop ro.build.id"
adb_cmd "Build type" "getprop ro.build.type"
adb_cmd "Build date" "getprop ro.build.date"
adb_cmd "Platform" "getprop ro.board.platform"
adb_cmd "Manufacturer" "getprop ro.product.manufacturer"
adb_cmd "Hardware" "getprop ro.hardware"

# ============================================
# KERNEL & SECURITY
# ============================================
log_section "Kernel & Security Information"

adb_cmd "Kernel version" "cat /proc/version" "kernel_version.txt"
adb_cmd "Kernel cmdline" "cat /proc/cmdline" "cmdline.txt"
adb_cmd "Kernel config (if readable)" "cat /proc/config.gz 2>/dev/null | gunzip 2>/dev/null || echo 'Not accessible'" "kernel_config.txt"
adb_cmd "Security patch level" "getprop ro.build.version.security_patch"
adb_cmd "SELinux status" "getenforce" "selinux_status.txt"
adb_cmd "SELinux mode" "cat /sys/fs/selinux/enforce"
adb_cmd "Android version" "getprop ro.build.version.release"
adb_cmd "SDK version" "getprop ro.build.version.sdk"

# ============================================
# BOOTLOADER & VERIFIED BOOT
# ============================================
log_section "Bootloader & Verified Boot"

adb_cmd "Bootloader version" "getprop ro.bootloader"
adb_cmd "Verified boot state" "getprop ro.boot.verifiedbootstate"
adb_cmd "Boot flash locked" "getprop ro.boot.flash.locked"
adb_cmd "Secure boot" "getprop ro.boot.secureboot"
adb_cmd "AVB version" "getprop ro.boot.avb_version"
adb_cmd "Vbmeta digest" "getprop ro.boot.vbmeta.digest"
adb_cmd "Boot slot" "getprop ro.boot.slot_suffix"
adb_cmd "Boot mode" "getprop ro.bootmode"
adb_cmd "OEM unlock allowed" "getprop ro.oem_unlock_supported"
adb_cmd "Unlock status" "getprop ro.boot.veritymode"
adb_cmd "DM-verity mode" "getprop ro.boot.veritymode"

# ============================================
# ROLLBACK & DOWNGRADE PROTECTION
# ============================================
log_section "Rollback & Downgrade Protection"

adb_cmd "AVB rollback index" "getprop ro.boot.avb.rollback_index" "rollback_index.txt"
adb_cmd "AVB rollback index location" "getprop ro.boot.avb.rollback_index_location"
adb_cmd "AVB device state" "getprop ro.boot.vbmeta.device_state"
adb_cmd "AVB hash algorithm" "getprop ro.boot.vbmeta.hash_alg"
adb_cmd "AVB invalidate on error" "getprop ro.boot.vbmeta.invalidate_on_error"
adb_cmd "Boot image security patch" "getprop ro.bootimage.build.date.utc"
adb_cmd "Vendor security patch" "getprop ro.vendor.build.security_patch"
adb_cmd "System security patch" "getprop ro.build.version.security_patch"
adb_cmd "Build UTC timestamp" "getprop ro.build.date.utc"
adb_cmd "Bootimage build date" "getprop ro.bootimage.build.date"
adb_cmd "OEM unlock allowed (sys)" "getprop sys.oem_unlock_allowed"
adb_cmd "OEM unlock supported" "getprop ro.oem_unlock_supported"
adb_cmd "FRP status" "getprop ro.frp.pst"
adb_cmd "Force normal boot" "getprop ro.boot.force_normal_boot"
adb_cmd "Rescue boot count" "getprop sys.rescue_boot_count"
adb_cmd "Rollback properties" "getprop | grep -i rollback" "rollback_props.txt"
adb_cmd "Anti-rollback properties" "getprop | grep -i 'anti\|version\|security'" "antirollback_props.txt"
adb_cmd "Build version incremental" "getprop ro.build.version.incremental"
adb_cmd "Build version codename" "getprop ro.build.version.codename"
adb_cmd "System build version" "getprop ro.system.build.version.release"
adb_cmd "Vendor build version" "getprop ro.vendor.build.version.release"
adb_cmd "Vendor build date" "getprop ro.vendor.build.date"
adb_cmd "GHS version info" "getprop | grep -i ghs" "ghs_props.txt"
adb_cmd "VBMeta partitions" "ls -la /dev/block/by-name/vbmeta* 2>/dev/null"
adb_cmd "Read vbmeta_a header (hex)" "dd if=/dev/block/by-name/vbmeta_a bs=1 count=64 2>/dev/null | xxd 2>/dev/null || echo 'Cannot read vbmeta'"
adb_cmd "Boot partition info" "ls -la /dev/block/by-name/boot* 2>/dev/null"

# Create rollback summary
{
    echo "=== ROLLBACK/DOWNGRADE ASSESSMENT ==="
    echo ""
    echo "Current Build:"
    adb shell "getprop ro.build.fingerprint" 2>/dev/null
    echo ""
    echo "Security Patch Level:"
    adb shell "getprop ro.build.version.security_patch" 2>/dev/null
    echo ""
    echo "Build Date (UTC):"
    adb shell "getprop ro.build.date.utc" 2>/dev/null
    echo ""
    echo "AVB Rollback Index:"
    adb shell "getprop ro.boot.avb.rollback_index" 2>/dev/null || echo "Not available"
    echo ""
    echo "OEM Unlock Status:"
    echo "  sys.oem_unlock_allowed: $(adb shell getprop sys.oem_unlock_allowed 2>/dev/null)"
    echo "  ro.oem_unlock_supported: $(adb shell getprop ro.oem_unlock_supported 2>/dev/null)"
    echo ""
    echo "Verified Boot State:"
    echo "  State: $(adb shell getprop ro.boot.verifiedbootstate 2>/dev/null)"
    echo "  Locked: $(adb shell getprop ro.boot.flash.locked 2>/dev/null)"
    echo ""
    echo "=== DOWNGRADE RISK ASSESSMENT ==="
    echo ""
    echo "If AVB rollback index is set and > 0, downgrade may fail at boot."
    echo "If OEM unlock is disallowed, cannot unlock bootloader to bypass."
    echo "Check if Y177 package has matching or lower rollback index."
    echo ""
} > "${OUTPUT_DIR}/rollback_assessment.txt"
log_success "Rollback assessment saved to rollback_assessment.txt"

# ============================================
# PARTITION INFORMATION
# ============================================
log_section "Partition Information"

adb_cmd "Block devices" "ls -la /dev/block/by-name/ 2>/dev/null || ls -la /dev/block/platform/*/by-name/ 2>/dev/null" "partitions.txt"
adb_cmd "Mount points" "mount" "mounts.txt"
adb_cmd "Disk free" "df -h" "disk_usage.txt"
adb_cmd "Partition table (fdisk)" "cat /proc/partitions" "proc_partitions.txt"
adb_cmd "fstab" "cat /vendor/etc/fstab.* 2>/dev/null || cat /etc/fstab.* 2>/dev/null" "fstab.txt"
adb_cmd "Dynamic partitions" "cat /dev/block/by-name/super 2>&1 | head -c 100 | xxd || echo 'Cannot read super partition'"

# ============================================
# HARDWARE INFORMATION
# ============================================
log_section "Hardware Information"

adb_cmd "CPU info" "cat /proc/cpuinfo" "cpuinfo.txt"
adb_cmd "Memory info" "cat /proc/meminfo" "meminfo.txt"
adb_cmd "USB devices" "cat /sys/kernel/debug/usb/devices 2>/dev/null || lsusb 2>/dev/null || echo 'Cannot enumerate USB'" "usb_devices.txt"
adb_cmd "I2C devices" "ls -la /dev/i2c-* 2>/dev/null" "i2c_devices.txt"
adb_cmd "SPI devices" "ls -la /dev/spi* 2>/dev/null"
adb_cmd "TTY devices" "ls -la /dev/tty* 2>/dev/null | head -50" "tty_devices.txt"
adb_cmd "GPU info" "cat /sys/kernel/debug/dri/0/name 2>/dev/null || dumpsys SurfaceFlinger 2>/dev/null | head -50"
adb_cmd "Thermal zones" "for f in /sys/class/thermal/thermal_zone*/type; do echo -n \"\$f: \"; cat \$f 2>/dev/null; done"
adb_cmd "Display info" "dumpsys display 2>/dev/null | head -100" "display_info.txt"

# ============================================
# NETWORK CONFIGURATION
# ============================================
log_section "Network Configuration"

adb_cmd "Network interfaces" "ip addr" "network_interfaces.txt"
adb_cmd "IP routes" "ip route"
adb_cmd "WiFi info" "dumpsys wifi 2>/dev/null | head -100"
adb_cmd "Bluetooth info" "dumpsys bluetooth_manager 2>/dev/null | head -50"
adb_cmd "Ethernet state" "cat /sys/class/net/eth*/address 2>/dev/null"
adb_cmd "ARP table" "cat /proc/net/arp"
adb_cmd "Open ports" "netstat -tlnp 2>/dev/null || ss -tlnp 2>/dev/null" "open_ports.txt"
adb_cmd "Iptables rules" "iptables -L -n 2>/dev/null" "iptables.txt"

# ============================================
# SERVICES & PROCESSES
# ============================================
log_section "Services & Processes"

adb_cmd "Running processes" "ps -A" "processes.txt"
adb_cmd "Init services" "getprop | grep init.svc" "init_services.txt"
adb_cmd "System services" "service list 2>/dev/null | head -100" "service_list.txt"
adb_cmd "Binder services" "dumpsys -l 2>/dev/null" "binder_services.txt"
adb_cmd "Running as user" "id" "current_user.txt"
adb_cmd "Process capabilities" "cat /proc/self/status | grep -i cap"

# ============================================
# GM/AUTOMOTIVE SPECIFIC
# ============================================
log_section "GM/Automotive Specific"

adb_cmd "Vehicle HAL properties" "dumpsys car_service 2>/dev/null | head -200" "car_service.txt"
adb_cmd "VHAL dump" "dumpsys android.hardware.automotive.vehicle 2>/dev/null | head -100"
adb_cmd "GM properties" "getprop | grep -i gm" "gm_props.txt"
adb_cmd "Harman properties" "getprop | grep -i harman"
adb_cmd "VIP properties" "getprop | grep -i vip"
adb_cmd "Tuner info" "dumpsys media.tuner 2>/dev/null | head -50"
adb_cmd "CarPlay/AA status" "dumpsys activity services CarPlay 2>/dev/null"

# ============================================
# SECURITY ANALYSIS
# ============================================
log_section "Security Analysis"

adb_cmd "SUID binaries" "find /system /vendor -perm -4000 2>/dev/null" "suid_binaries.txt"
adb_cmd "World-writable files" "find /system /vendor -perm -0002 -type f 2>/dev/null | head -50" "world_writable.txt"
adb_cmd "Setuid capabilities" "find / -type f -perm -4000 2>/dev/null | head -20"
adb_cmd "Available shells" "ls -la /system/bin/sh /system/bin/bash /vendor/bin/sh 2>/dev/null"
adb_cmd "Su binary check" "which su 2>/dev/null; ls -la /system/xbin/su /system/bin/su /sbin/su 2>/dev/null"
adb_cmd "Magisk check" "ls -la /data/adb/magisk 2>/dev/null; getprop | grep magisk"
adb_cmd "ADB keys" "cat /data/misc/adb/adb_keys 2>/dev/null" "adb_keys.txt"
adb_cmd "Crypto state" "getprop ro.crypto.state"
adb_cmd "Debug properties" "getprop | grep -i debug" "debug_props.txt"
adb_cmd "Test keys check" "getprop | grep -i testkey"

# ============================================
# FILE SYSTEM EXPLORATION
# ============================================
log_section "File System Exploration"

adb_cmd "/system structure" "ls -la /system/" "system_root.txt"
adb_cmd "/system/bin binaries" "ls -la /system/bin/ | head -100" "system_bin.txt"
adb_cmd "/vendor structure" "ls -la /vendor/" "vendor_root.txt"
adb_cmd "/vendor/bin binaries" "ls -la /vendor/bin/ | head -100" "vendor_bin.txt"
adb_cmd "/data structure" "ls -la /data/ 2>/dev/null" "data_root.txt"
adb_cmd "/data/local/tmp" "ls -la /data/local/tmp/"
adb_cmd "/mnt structure" "ls -la /mnt/"
adb_cmd "/dev structure" "ls -la /dev/ | head -50"
adb_cmd "Init rc files" "ls -la /system/etc/init/ /vendor/etc/init/ 2>/dev/null" "init_rc_files.txt"
adb_cmd "Interesting configs" "ls -la /system/etc/*.conf /vendor/etc/*.conf 2>/dev/null"

# ============================================
# DEBUG INTERFACES
# ============================================
log_section "Debug Interfaces"

adb_cmd "Debugfs mounted" "mount | grep debugfs"
adb_cmd "Tracefs" "ls -la /sys/kernel/tracing/ 2>/dev/null | head -20"
adb_cmd "Kernel debug" "ls -la /sys/kernel/debug/ 2>/dev/null" "kernel_debug.txt"
adb_cmd "Proc readable" "ls -la /proc/ | head -30"
adb_cmd "Kmsg access" "dmesg 2>/dev/null | tail -100" "dmesg.txt"
adb_cmd "Logcat (recent)" "logcat -d -t 200 2>/dev/null" "logcat.txt"
adb_cmd "MCP2200 UART check" "ls -la /dev/ttyACM* /dev/ttyUSB* 2>/dev/null"

# ============================================
# UART PROBING (via ADB)
# ============================================
log_section "UART Device Probing"

# Check for available serial devices
adb_cmd "Serial devices list" "ls -la /dev/ttyACM* /dev/ttyUSB* /dev/ttyS* /dev/ttyHS* 2>/dev/null" "uart_devices.txt"

# Probe each ttyACM device
for dev in $(adb shell "ls /dev/ttyACM* 2>/dev/null" | tr -d '\r'); do
    if [ -n "$dev" ]; then
        log_info "Probing UART device: $dev"

        # Check permissions
        adb_cmd "Permissions for $dev" "ls -la $dev"

        # Try to get stty settings (may fail)
        adb_cmd "Stty settings for $dev" "stty -F $dev 2>/dev/null || echo 'stty not available'"

        # Try non-blocking read (timeout after 2 seconds)
        log_info "Attempting read from $dev (2 second timeout)..."
        UART_READ=$(adb shell "timeout 2 cat $dev 2>/dev/null | head -c 500 | xxd" 2>&1)
        if [ -n "$UART_READ" ] && ! echo "$UART_READ" | grep -qi "timeout\|error\|denied"; then
            log_success "Got data from $dev"
            echo "$UART_READ" > "${RAW_DIR}/uart_${dev##*/}_read.txt"
            echo "$UART_READ" >> "$REPORT_FILE"
        else
            log_warn "No data received from $dev (may need activity trigger)"
        fi

        # Try sending newline and capturing response
        log_info "Sending probe to $dev..."
        UART_PROBE=$(adb shell "echo -e '\r\n' > $dev 2>/dev/null; timeout 2 cat $dev 2>/dev/null | head -c 500" 2>&1)
        if [ -n "$UART_PROBE" ] && ! echo "$UART_PROBE" | grep -qi "timeout\|error\|denied"; then
            log_success "Got response from $dev after probe"
            echo "$UART_PROBE" > "${RAW_DIR}/uart_${dev##*/}_probe_response.txt"
            echo "$UART_PROBE" >> "$REPORT_FILE"
        fi

        # Try sending common commands
        for cmd in "help" "?" "version" "info" "status"; do
            UART_CMD_RESP=$(adb shell "echo '$cmd' > $dev 2>/dev/null; timeout 1 cat $dev 2>/dev/null | head -c 200" 2>&1)
            if [ -n "$UART_CMD_RESP" ] && ! echo "$UART_CMD_RESP" | grep -qi "timeout\|error\|denied"; then
                log_success "Response to '$cmd' on $dev"
                echo "Command: $cmd" >> "${RAW_DIR}/uart_${dev##*/}_commands.txt"
                echo "Response: $UART_CMD_RESP" >> "${RAW_DIR}/uart_${dev##*/}_commands.txt"
                echo "---" >> "${RAW_DIR}/uart_${dev##*/}_commands.txt"
            fi
        done
    fi
done

# Create UART summary
{
    echo "=== UART PROBE SUMMARY ==="
    echo ""
    echo "Devices found:"
    adb shell "ls -la /dev/ttyACM* /dev/ttyUSB* 2>/dev/null"
    echo ""
    echo "World-accessible UART devices:"
    adb shell "ls -la /dev/ttyACM* /dev/ttyUSB* 2>/dev/null | grep 'rw-rw-rw\|rw-rw'"
    echo ""
    echo "NOTE: UART may require specific baud rate or activity trigger."
    echo "Try manual probing with: adb shell cat /dev/ttyACM1 &"
    echo "Then trigger activity on the device."
    echo ""
} > "${OUTPUT_DIR}/uart_summary.txt"
log_success "UART summary saved to uart_summary.txt"

# ============================================
# ALL PROPERTIES DUMP
# ============================================
log_section "Full Properties Dump"

adb_cmd "All system properties" "getprop" "all_properties.txt"

# ============================================
# ATTEMPT FILE PULLS
# ============================================
log_section "Attempting File Pulls"

adb_pull "/system/build.prop" "System build.prop"
adb_pull "/vendor/build.prop" "Vendor build.prop"
adb_pull "/product/build.prop" "Product build.prop"
adb_pull "/default.prop" "Default prop"
adb_pull "/proc/version" "Kernel version"
adb_pull "/proc/cmdline" "Kernel cmdline"
adb_pull "/vendor/etc/fstab.gminfo37" "fstab"
adb_pull "/system/etc/selinux/plat_sepolicy.cil" "SELinux policy"
adb_pull "/vendor/etc/selinux/vendor_sepolicy.cil" "Vendor SELinux"

# ============================================
# SUMMARY
# ============================================
log_section "Enumeration Summary"

echo ""
echo "========================================"
echo " Enumeration Complete"
echo "========================================"
echo ""
echo "Output directory: $OUTPUT_DIR"
echo ""
echo "Key files:"
echo "  - ${REPORT_FILE} (full report)"
echo "  - ${RAW_DIR}/ (individual command outputs)"
echo "  - ${PULLED_DIR}/ (pulled files)"
echo "  - ${OUTPUT_DIR}/pull_failures.txt (failed pulls)"
echo ""

# Count results
DENIED_COUNT=$(grep -c "\[DENIED\]" "$REPORT_FILE" 2>/dev/null || echo 0)
SUCCESS_COUNT=$(grep -c "\[OK\]" "$REPORT_FILE" 2>/dev/null || echo 0)

echo "Results: $SUCCESS_COUNT successful, $DENIED_COUNT access denied"
echo ""
echo "Next steps:"
echo "  1. Review $REPORT_FILE for security findings"
echo "  2. Check kernel_version.txt for exact kernel"
echo "  3. Review debug_props.txt for debug interfaces"
echo "  4. Attempt: adb reboot bootloader"
echo ""

# Create quick reference of key security findings
echo "=== KEY SECURITY FINDINGS ===" > "${OUTPUT_DIR}/security_summary.txt"
echo "" >> "${OUTPUT_DIR}/security_summary.txt"
grep -A1 "Kernel version\|SELinux\|Verified boot\|flash.locked\|oem_unlock\|ro.debuggable\|rollback\|AVB" "$REPORT_FILE" >> "${OUTPUT_DIR}/security_summary.txt" 2>/dev/null
echo "" >> "${OUTPUT_DIR}/security_summary.txt"
echo "=== ROLLBACK SUMMARY ===" >> "${OUTPUT_DIR}/security_summary.txt"
cat "${OUTPUT_DIR}/rollback_assessment.txt" >> "${OUTPUT_DIR}/security_summary.txt" 2>/dev/null

echo "Quick security summary saved to: ${OUTPUT_DIR}/security_summary.txt"
