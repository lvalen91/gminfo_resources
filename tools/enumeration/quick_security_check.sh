#!/bin/bash
#
# Quick Security Check - GM AAOS
# Rapid assessment of key security properties
#

echo "=== GM AAOS Quick Security Check ==="
echo ""

# Check ADB connection
if ! adb devices | grep -q "device$"; then
    echo "ERROR: No ADB device connected"
    exit 1
fi

echo "[*] Device: $(adb shell getprop ro.product.device 2>/dev/null)"
echo "[*] Build:  $(adb shell getprop ro.build.id 2>/dev/null)"
echo ""

echo "=== KERNEL ==="
adb shell cat /proc/version 2>/dev/null | head -1
echo ""

echo "=== SECURITY PATCH ==="
adb shell getprop ro.build.version.security_patch
echo ""

echo "=== SELINUX ==="
echo -n "Mode: "
adb shell getenforce 2>/dev/null
echo -n "Enforce value: "
adb shell cat /sys/fs/selinux/enforce 2>/dev/null
echo ""

echo "=== VERIFIED BOOT ==="
echo -n "State: "
adb shell getprop ro.boot.verifiedbootstate
echo -n "Locked: "
adb shell getprop ro.boot.flash.locked
echo -n "Verity: "
adb shell getprop ro.boot.veritymode
echo ""

echo "=== BOOTLOADER ==="
echo -n "Version: "
adb shell getprop ro.bootloader
echo -n "Slot: "
adb shell getprop ro.boot.slot_suffix
echo ""

echo "=== ROLLBACK/DOWNGRADE PROTECTION ==="
echo -n "AVB Rollback Index: "
adb shell getprop ro.boot.avb.rollback_index 2>/dev/null || echo "Not set"
echo -n "OEM Unlock Allowed: "
adb shell getprop sys.oem_unlock_allowed
echo -n "Build Date (UTC): "
adb shell getprop ro.build.date.utc
echo -n "Vendor Build Date: "
adb shell getprop ro.vendor.build.date
echo ""
echo "Downgrade Assessment:"
ROLLBACK_IDX=$(adb shell getprop ro.boot.avb.rollback_index 2>/dev/null)
OEM_UNLOCK=$(adb shell getprop sys.oem_unlock_allowed 2>/dev/null)
if [ -z "$ROLLBACK_IDX" ] || [ "$ROLLBACK_IDX" = "0" ]; then
    echo "  [+] No rollback index detected - downgrade MAY be possible"
else
    echo "  [-] Rollback index: $ROLLBACK_IDX - downgrade may be BLOCKED"
fi
if [ "$OEM_UNLOCK" = "0" ]; then
    echo "  [-] OEM unlock disabled - cannot bypass via bootloader unlock"
else
    echo "  [+] OEM unlock may be available"
fi
echo ""

echo "=== DEBUG STATUS ==="
echo -n "ro.debuggable: "
adb shell getprop ro.debuggable
echo -n "ro.secure: "
adb shell getprop ro.secure
echo -n "ro.adb.secure: "
adb shell getprop ro.adb.secure
echo ""

echo "=== CURRENT USER ==="
adb shell id
echo ""

echo "=== ROOT CHECK ==="
echo -n "su binary: "
adb shell "which su 2>/dev/null || ls /system/xbin/su /system/bin/su /sbin/su 2>/dev/null || echo 'Not found'"
echo ""

echo "=== INTERESTING PORTS ==="
adb shell "netstat -tlnp 2>/dev/null || ss -tln 2>/dev/null" | grep LISTEN | head -10
echo ""

echo "=== MCP2200 UART ==="
adb shell "ls -la /dev/ttyACM* /dev/ttyUSB* /dev/ttyS* 2>/dev/null | head -5 || echo 'No serial devices visible from ADB'"
echo ""

echo "=== UART PROBE (via ADB) ==="
# Quick probe of ttyACM devices
for dev in /dev/ttyACM0 /dev/ttyACM1; do
    echo -n "Probing $dev: "
    # Check if accessible
    PERMS=$(adb shell "ls -la $dev 2>/dev/null" | grep -o '^[crwx-]*')
    if [ -n "$PERMS" ]; then
        echo -n "[$PERMS] "
        # Try quick read
        RESP=$(adb shell "timeout 1 cat $dev 2>/dev/null | head -c 100" 2>&1)
        if [ -n "$RESP" ] && ! echo "$RESP" | grep -qi "error\|denied"; then
            echo "GOT DATA!"
            echo "$RESP" | head -2
        else
            # Try sending newline
            adb shell "echo '' > $dev 2>/dev/null"
            RESP2=$(adb shell "timeout 1 cat $dev 2>/dev/null | head -c 100" 2>&1)
            if [ -n "$RESP2" ] && ! echo "$RESP2" | grep -qi "error\|denied"; then
                echo "Responds to probe!"
            else
                echo "No response (may need trigger/different baud)"
            fi
        fi
    else
        echo "Not found or not accessible"
    fi
done
echo ""
echo "Manual UART test:"
echo "  adb shell 'cat /dev/ttyACM1 &'"
echo "  adb shell 'echo test > /dev/ttyACM1'"
echo ""

echo "=== FASTBOOT TEST ==="
echo "To test fastboot access, run:"
echo "  adb reboot bootloader"
echo "  fastboot devices"
echo "  fastboot getvar all"
echo ""
