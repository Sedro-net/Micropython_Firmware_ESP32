# secrets_template.py - Template for user credentials
# Copy this file to 'secrets.py' and fill in your actual credentials
# secrets.py is gitignored for security

# ============================================================================
# WIFI CREDENTIALS
# ============================================================================
# You can configure up to 2 Wi-Fi profiles
# The device will try them in order with 10s timeout each

WIFI_PROFILES = [
    {
        "ssid": "YourWiFiSSID",
        "password": "YourWiFiPassword",
        "priority": 1  # Higher priority tried first
    },
    # Uncomment and configure second profile if needed
    # {
    #     "ssid": "BackupWiFiSSID",
    #     "password": "BackupWiFiPassword",
    #     "priority": 2
    # }
]

# ============================================================================
# MQTT CREDENTIALS
# ============================================================================
# Configure your MQTT broker details
# Leave broker empty to enable mDNS auto-discovery

MQTT_BROKER = ""  # e.g., "192.168.1.100" or "mqtt.example.com" or "" for auto-discovery
MQTT_PORT = 1883
MQTT_USERNAME = ""  # Leave empty if no authentication
MQTT_PASSWORD = ""

# ============================================================================
# DEVICE CONFIGURATION
# ============================================================================
# Optional: Override default device settings

DEVICE_LOCATION = "living_room"  # Used in MQTT topic: home/<location>/<device_id>

# ============================================================================
# OTA CONFIGURATION
# ============================================================================
# Optional: Configure OTA update server

OTA_SERVER_URL = ""  # e.g., "http://192.168.1.100:8000/firmware"

# ============================================================================
# NOTES
# ============================================================================
# - This file should be renamed to 'secrets.py' and uploaded to your ESP32
# - Never commit secrets.py to version control
# - You can also configure Wi-Fi and MQTT via the captive portal
# - If secrets.py is missing, device will start in AP mode for configuration
