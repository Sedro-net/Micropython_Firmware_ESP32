# config.py - Configuration defaults, constants, and versioning

import ubinascii
import machine
import network

# ============================================================================
# FIRMWARE INFORMATION
# ============================================================================
FIRMWARE_VERSION = "1.0.0"
FIRMWARE_NAME = "ESP32-SHTC3-HA"
BUILD_DATE = "2026-02-13"

# ============================================================================
# HARDWARE CONFIGURATION
# ============================================================================

# I2C Configuration for SHTC3
I2C_SDA_PIN = 21
I2C_SCL_PIN = 22
I2C_FREQ = 400000  # 400 kHz
SHTC3_ADDRESS = 0x70

# LED Ring Configuration (WS2812B)
LED_PIN = 15
LED_COUNT = 12
LED_COLOR_ORDER = "RGB"  # Change to "GRB" if colors are wrong

# ============================================================================
# DEVICE IDENTIFICATION
# ============================================================================

def get_device_id():
    """Generate unique device ID from MAC address."""
    wlan = network.WLAN(network.STA_IF)
    mac = ubinascii.hexlify(wlan.config('mac')).decode()
    return mac[-8:]  # Last 4 bytes (8 hex chars)

def get_ap_ssid():
    """Generate AP SSID from device ID."""
    return f"ESP32-SHTC3-{get_device_id()[-4:]}"

# Device identification
DEVICE_ID = get_device_id()
DEVICE_NAME = f"ESP32-SHTC3-{DEVICE_ID[-4:]}"

# ============================================================================
# WIFI CONFIGURATION
# ============================================================================

# Wi-Fi Connection Settings
WIFI_CONNECT_TIMEOUT = 10  # seconds per profile
WIFI_MAX_PROFILES = 2
WIFI_RETRY_DELAY = 5  # seconds between full rotation retries

# Access Point Configuration
AP_SSID = get_ap_ssid()
AP_PASSWORD = "configure123"  # Default AP password
AP_CHANNEL = 6
AP_AUTHMODE = 3  # WPA2
AP_IP = "192.168.4.1"
AP_SUBNET = "255.255.255.0"
AP_GATEWAY = "192.168.4.1"

# Captive Portal Settings
CAPTIVE_PORTAL_PORT = 80
CAPTIVE_PORTAL_TIMEOUT = 300  # 5 minutes before giving up

# ============================================================================
# MQTT CONFIGURATION
# ============================================================================

# MQTT Connection Settings
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60
MQTT_RECONNECT_DELAY = 5  # seconds
MQTT_MAX_RECONNECT_DELAY = 60  # seconds

# MQTT Topics
def get_base_topic(location="living_room"):
    """Get base MQTT topic."""
    return f"home/{location}/{DEVICE_ID}"

MQTT_BASE_TOPIC = get_base_topic()
MQTT_LWT_TOPIC = f"{MQTT_BASE_TOPIC}/status"
MQTT_STATE_TOPIC = f"{MQTT_BASE_TOPIC}/state"
MQTT_COMMAND_TOPIC = f"{MQTT_BASE_TOPIC}/command"
MQTT_CONFIG_TOPIC = f"{MQTT_BASE_TOPIC}/config"
MQTT_LED_COMMAND_TOPIC = f"{MQTT_BASE_TOPIC}/led/command"
MQTT_LED_STATE_TOPIC = f"{MQTT_BASE_TOPIC}/led/state"
MQTT_OTA_TOPIC = f"{MQTT_BASE_TOPIC}/ota"

# Home Assistant Discovery
HA_DISCOVERY_PREFIX = "homeassistant"
HA_DISCOVERY_ENABLED = True

# ============================================================================
# SENSOR CONFIGURATION
# ============================================================================

# Sensor Reading Settings
SENSOR_READ_INTERVAL = 10  # seconds between reads
SENSOR_PUBLISH_INTERVAL = 30  # seconds between publishes
SENSOR_RETRY_COUNT = 3
SENSOR_RETRY_DELAY = 1  # seconds

# Significant change thresholds for immediate publish
TEMP_CHANGE_THRESHOLD = 0.5  # °C
HUMIDITY_CHANGE_THRESHOLD = 2.0  # %

# ============================================================================
# LED CONFIGURATION
# ============================================================================

# LED Status Indicators
LED_STATUS_DISCONNECTED = (0, 0, 128)  # Blue blinking
LED_STATUS_FAILSAFE = (128, 0, 0)  # Red blinking
LED_STATUS_CONNECTING = (128, 128, 0)  # Yellow blinking
LED_STATUS_OFF = (0, 0, 0)  # Off when idle

# LED Effect Settings
LED_EFFECT_SPEED = 50  # milliseconds per frame
LED_BRIGHTNESS_DEFAULT = 128  # 0-255

# Available LED effects
LED_EFFECTS = [
    "solid",
    "rainbow",
    "breathing",
    "humidity_gauge",
    "temperature_gauge"
]

# ============================================================================
# OTA CONFIGURATION
# ============================================================================

OTA_ENABLED = True
OTA_TIMEOUT = 60  # seconds
OTA_CHUNK_SIZE = 4096  # bytes
OTA_VERIFY_SHA256 = True
OTA_BACKUP_ENABLED = True

# ============================================================================
# FAILSAFE CONFIGURATION
# ============================================================================

FAILSAFE_FLAG_FILE = "failsafe.flag"
FAILSAFE_LOG_FILE = "failsafe.log"
FAILSAFE_MAX_LOG_SIZE = 10240  # 10 KB

# ============================================================================
# STORAGE CONFIGURATION
# ============================================================================

CONFIG_FILE = "config.json"
SECRETS_FILE = "secrets.py"

# Default configuration
DEFAULT_CONFIG = {
    "device": {
        "name": DEVICE_NAME,
        "location": "living_room",
        "firmware_version": FIRMWARE_VERSION
    },
    "wifi": {
        "profiles": []  # Will be populated from secrets or captive portal
    },
    "mqtt": {
        "enabled": True,
        "broker": "",
        "port": MQTT_PORT,
        "username": "",
        "password": "",
        "client_id": DEVICE_ID,
        "base_topic": MQTT_BASE_TOPIC,
        "discovery_enabled": HA_DISCOVERY_ENABLED
    },
    "sensor": {
        "read_interval": SENSOR_READ_INTERVAL,
        "publish_interval": SENSOR_PUBLISH_INTERVAL,
        "temp_offset": 0.0,
        "humidity_offset": 0.0
    },
    "led": {
        "enabled": True,
        "brightness": LED_BRIGHTNESS_DEFAULT,
        "effect": "solid",
        "color": [255, 255, 255]
    },
    "ota": {
        "enabled": OTA_ENABLED,
        "auto_update": False
    }
}

# ============================================================================
# SYSTEM CONFIGURATION
# ============================================================================

# Watchdog Timer
WDT_TIMEOUT = 30000  # 30 seconds (milliseconds)
WDT_ENABLED = True

# Cooperative Scheduler
SCHEDULER_TICK_MS = 100  # 100ms tick resolution

# mDNS Configuration
MDNS_ENABLED = True
MDNS_SERVICE_TYPE = "_mqtt._tcp"
MDNS_TIMEOUT = 5  # seconds

# Memory Management
GC_THRESHOLD = 50000  # bytes, trigger GC below this
GC_INTERVAL = 60  # seconds between forced GC

# Logging
LOG_LEVEL_DEBUG = 10
LOG_LEVEL_INFO = 20
LOG_LEVEL_WARNING = 30
LOG_LEVEL_ERROR = 40
LOG_LEVEL = LOG_LEVEL_INFO  # Default log level

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_reset_cause():
    """Get human-readable reset cause."""
    causes = {
        machine.PWRON_RESET: "Power on",
        machine.HARD_RESET: "Hard reset",
        machine.WDT_RESET: "Watchdog",
        machine.DEEPSLEEP_RESET: "Deep sleep",
        machine.SOFT_RESET: "Soft reset"
    }
    cause = machine.reset_cause()
    return causes.get(cause, f"Unknown ({cause})")

def print_system_info():
    """Print system information."""
    import gc
    import os
    
    print("\n" + "="*50)
    print(f"Device: {DEVICE_NAME}")
    print(f"Device ID: {DEVICE_ID}")
    print(f"Firmware: {FIRMWARE_NAME} v{FIRMWARE_VERSION}")
    print(f"Build Date: {BUILD_DATE}")
    print(f"Reset Cause: {get_reset_cause()}")
    print(f"Frequency: {machine.freq() // 1000000} MHz")
    
    # Memory info
    gc.collect()
    print(f"Free Memory: {gc.mem_free()} bytes")
    print(f"Used Memory: {gc.mem_alloc()} bytes")
    
    # Flash info
    try:
        stat = os.statvfs('/')
        flash_size = stat[0] * stat[2]
        flash_free = stat[0] * stat[3]
        print(f"Flash: {flash_free}/{flash_size} bytes free")
    except:
        pass
    
    print("="*50 + "\n")
