# util.py - Utility functions for backoff, timing, scheduling, formatting

import time
import gc

# ============================================================================
# TIMING UTILITIES
# ============================================================================

class Timer:
    """Simple timer for tracking elapsed time."""
    
    def __init__(self):
        self.start_time = time.ticks_ms()
    
    def reset(self):
        """Reset timer to current time."""
        self.start_time = time.ticks_ms()
    
    def elapsed_ms(self):
        """Get elapsed time in milliseconds."""
        return time.ticks_diff(time.ticks_ms(), self.start_time)
    
    def elapsed_s(self):
        """Get elapsed time in seconds."""
        return self.elapsed_ms() / 1000
    
    def has_elapsed(self, ms):
        """Check if specified time has elapsed."""
        return self.elapsed_ms() >= ms

class IntervalTimer:
    """Timer that fires at regular intervals."""
    
    def __init__(self, interval_ms):
        self.interval_ms = interval_ms
        self.last_fire = time.ticks_ms()
    
    def check(self):
        """Check if interval has elapsed and reset if so."""
        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_fire) >= self.interval_ms:
            self.last_fire = now
            return True
        return False
    
    def reset(self):
        """Reset timer."""
        self.last_fire = time.ticks_ms()
    
    def set_interval(self, interval_ms):
        """Change interval."""
        self.interval_ms = interval_ms

# ============================================================================
# BACKOFF UTILITIES
# ============================================================================

class ExponentialBackoff:
    """Exponential backoff for retry logic."""
    
    def __init__(self, initial_delay=1, max_delay=60, multiplier=2, jitter=0.1):
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter
        self.current_delay = initial_delay
        self.attempt = 0
    
    def get_delay(self):
        """Get current delay value."""
        # Add jitter to prevent thundering herd
        import random
        jitter_amount = self.current_delay * self.jitter * (random.random() * 2 - 1)
        return max(0, self.current_delay + jitter_amount)
    
    def next(self):
        """Move to next backoff delay."""
        self.attempt += 1
        self.current_delay = min(self.current_delay * self.multiplier, self.max_delay)
        return self.get_delay()
    
    def reset(self):
        """Reset backoff to initial state."""
        self.current_delay = self.initial_delay
        self.attempt = 0

# ============================================================================
# SCHEDULER
# ============================================================================

class Task:
    """Scheduled task."""
    
    def __init__(self, name, callback, interval_ms, enabled=True):
        self.name = name
        self.callback = callback
        self.interval_ms = interval_ms
        self.enabled = enabled
        self.last_run = time.ticks_ms()
        self.run_count = 0
        self.error_count = 0
    
    def should_run(self):
        """Check if task should run."""
        if not self.enabled:
            return False
        return time.ticks_diff(time.ticks_ms(), self.last_run) >= self.interval_ms
    
    def run(self):
        """Execute task callback."""
        try:
            self.callback()
            self.run_count += 1
            self.last_run = time.ticks_ms()
            return True
        except Exception as e:
            self.error_count += 1
            print(f"[SCHEDULER] Task '{self.name}' error: {e}")
            import sys
            sys.print_exception(e)
            return False

class Scheduler:
    """Simple cooperative scheduler."""
    
    def __init__(self):
        self.tasks = []
        self.running = False
    
    def add_task(self, name, callback, interval_ms, enabled=True):
        """Add task to scheduler."""
        task = Task(name, callback, interval_ms, enabled)
        self.tasks.append(task)
        print(f"[SCHEDULER] Added task '{name}' ({interval_ms}ms)")
        return task
    
    def remove_task(self, name):
        """Remove task by name."""
        self.tasks = [t for t in self.tasks if t.name != name]
    
    def enable_task(self, name):
        """Enable task by name."""
        for task in self.tasks:
            if task.name == name:
                task.enabled = True
                return True
        return False
    
    def disable_task(self, name):
        """Disable task by name."""
        for task in self.tasks:
            if task.name == name:
                task.enabled = False
                return True
        return False
    
    def get_task(self, name):
        """Get task by name."""
        for task in self.tasks:
            if task.name == name:
                return task
        return None
    
    def run_once(self):
        """Run one iteration of scheduler."""
        for task in self.tasks:
            if task.should_run():
                task.run()
    
    def run(self, tick_ms=100):
        """Run scheduler loop."""
        self.running = True
        print(f"[SCHEDULER] Starting with {len(self.tasks)} tasks")
        
        while self.running:
            self.run_once()
            time.sleep_ms(tick_ms)
    
    def stop(self):
        """Stop scheduler."""
        self.running = False
        print("[SCHEDULER] Stopped")
    
    def print_stats(self):
        """Print scheduler statistics."""
        print("\n" + "="*50)
        print("Scheduler Statistics")
        print("="*50)
        for task in self.tasks:
            status = "Enabled" if task.enabled else "Disabled"
            print(f"{task.name:20s} | {status:8s} | Runs: {task.run_count:5d} | Errors: {task.error_count:3d}")
        print("="*50 + "\n")

# ============================================================================
# FORMATTING UTILITIES
# ============================================================================

def format_bytes(bytes_val):
    """Format bytes to human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} TB"

def format_uptime(seconds):
    """Format uptime in seconds to human readable string."""
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

def format_mac(mac_bytes):
    """Format MAC address bytes to string."""
    import ubinascii
    return ubinascii.hexlify(mac_bytes, ':').decode().upper()

def format_ip(ip_tuple):
    """Format IP tuple to string."""
    return '.'.join(str(x) for x in ip_tuple)

# ============================================================================
# MEMORY MANAGEMENT
# ============================================================================

def check_memory(threshold=50000, force_gc=True):
    """Check free memory and optionally trigger GC.
    
    Args:
        threshold: Minimum free memory in bytes
        force_gc: Force garbage collection if below threshold
        
    Returns:
        True if memory is sufficient, False otherwise
    """
    free = gc.mem_free()
    
    if free < threshold:
        print(f"[MEMORY] Low memory: {format_bytes(free)} free")
        if force_gc:
            gc.collect()
            free = gc.mem_free()
            print(f"[MEMORY] After GC: {format_bytes(free)} free")
        return free >= threshold
    
    return True

def print_memory_info():
    """Print detailed memory information."""
    gc.collect()
    print(f"Memory: {format_bytes(gc.mem_free())} free, {format_bytes(gc.mem_alloc())} used")

# ============================================================================
# COLOR UTILITIES
# ============================================================================

def rgb_to_int(r, g, b):
    """Convert RGB values (0-255) to single integer."""
    return (r << 16) | (g << 8) | b

def int_to_rgb(color_int):
    """Convert integer color to RGB tuple."""
    r = (color_int >> 16) & 0xFF
    g = (color_int >> 8) & 0xFF
    b = color_int & 0xFF
    return (r, g, b)

def hsv_to_rgb(h, s, v):
    """Convert HSV to RGB.
    
    Args:
        h: Hue (0-360)
        s: Saturation (0-1)
        v: Value (0-1)
        
    Returns:
        Tuple of (r, g, b) values (0-255)
    """
    h = h % 360
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c
    
    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    
    return (int((r + m) * 255), int((g + m) * 255), int((b + m) * 255))

def wheel(pos):
    """Generate rainbow colors across 0-255 positions."""
    if pos < 85:
        return (pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return (255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return (0, pos * 3, 255 - pos * 3)

# ============================================================================
# NETWORK UTILITIES
# ============================================================================

def get_rssi():
    """Get Wi-Fi RSSI (signal strength)."""
    import network
    wlan = network.WLAN(network.STA_IF)
    if wlan.isconnected():
        # RSSI not directly available in MicroPython, return None
        # Some builds may have wlan.status('rssi')
        try:
            return wlan.status('rssi')
        except:
            return None
    return None

def get_mac_address():
    """Get MAC address as string."""
    import network
    import ubinascii
    wlan = network.WLAN(network.STA_IF)
    mac = ubinascii.hexlify(wlan.config('mac')).decode()
    return ':'.join(mac[i:i+2] for i in range(0, len(mac), 2)).upper()

# ============================================================================
# VALIDATION UTILITIES
# ============================================================================

def is_valid_ip(ip_str):
    """Check if string is valid IP address."""
    try:
        parts = ip_str.split('.')
        if len(parts) != 4:
            return False
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False
        return True
    except:
        return False

def clamp(value, min_val, max_val):
    """Clamp value between min and max."""
    return max(min_val, min(max_val, value))
