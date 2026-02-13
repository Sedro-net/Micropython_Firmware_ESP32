# boot.py - Safe boot with boot loop detection
# Runs before main.py to detect boot loops and trigger failsafe mode

import machine
import time
import ujson as json
import os
import main as main_py

BOOT_COUNT_FILE = "boot_count.json"
BOOT_LOOP_THRESHOLD = 3
BOOT_LOOP_WINDOW = 60  # seconds
FAILSAFE_FLAG_FILE = "failsafe.flag"

def load_boot_record():
    """Load boot count record from file."""
    try:
        with open(BOOT_COUNT_FILE, 'r') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"count": 0, "first_boot": time.time()}

def save_boot_record(record):
    """Save boot count record to file."""
    try:
        with open(BOOT_COUNT_FILE, 'w') as f:
            json.dump(record, f)
    except OSError:
        pass

def clear_boot_record():
    """Clear boot count record."""
    try:
        os.remove(BOOT_COUNT_FILE)
    except OSError:
        pass

def set_failsafe_flag(reason="boot_loop"):
    """Set failsafe flag to trigger failsafe mode."""
    try:
        with open(FAILSAFE_FLAG_FILE, 'w') as f:
            json.dump({"reason": reason, "timestamp": time.time()}, f)
    except OSError:
        pass

def check_boot_loop():
    """Check if boot loop is detected and trigger failsafe if needed."""
    record = load_boot_record()
    current_time = time.time()
    
    # Check if we're in the same boot window
    time_since_first = current_time - record.get("first_boot", 0)
    
    if time_since_first > BOOT_LOOP_WINDOW:
        # Reset counter if outside window
        record = {"count": 1, "first_boot": current_time}
    else:
        # Increment counter within window
        record["count"] += 1
    
    save_boot_record(record)
    
    # Check if threshold exceeded
    if record["count"] >= BOOT_LOOP_THRESHOLD:
        print(f"[BOOT] Boot loop detected: {record['count']} boots in {time_since_first:.1f}s")
        set_failsafe_flag("boot_loop")
        clear_boot_record()  # Reset counter
        return True
    
    print(f"[BOOT] Boot #{record['count']} in window")
    return False

def main():
    """Main boot sequence."""
    print("="*50)
    print("ESP32 SHTC3 Firmware - Boot Sequence")
    print("="*50)
    
    # Check for boot loop
    in_boot_loop = check_boot_loop()
    
    if in_boot_loop:
        print("[BOOT] Entering failsafe mode...")
    else:
        print("[BOOT] Normal boot sequence")
    
    # Optional: Enable WebREPL or other boot-time configurations
    # import webrepl
    # webrepl.start()
    
    print("[BOOT] Boot sequence complete, starting main.py...\n")

    main_py.main_sequence()

if __name__ == "__main__":
    main()
