# ESP32 SHTC3 Home Assistant MQTT Firmware

Production-grade MicroPython firmware for ESP32 DevKit v1 with SHTC3 temperature/humidity sensor, WS2812B LED ring, and full Home Assistant integration.

## 📋 Table of Contents

- [Features](#features)
- [Hardware Requirements](#hardware-requirements)
- [Wiring Diagram](#wiring-diagram)
- [Software Requirements](#software-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [MQTT Topics](#mqtt-topics)
- [Home Assistant Integration](#home-assistant-integration)
- [OTA Updates](#ota-updates)
- [Failsafe Mode](#failsafe-mode)
- [LED Effects](#led-effects)
- [Troubleshooting](#troubleshooting)
- [Test Plan](#test-plan)
- [API Reference](#api-reference)

## ✨ Features

### Core Features
- ✅ **SHTC3 Sensor**: Temperature and humidity monitoring with calibration offsets
- ✅ **WS2812B LED Ring**: 12 RGB LEDs with multiple effects
- ✅ **Wi-Fi Manager**: Support for 2 profiles with automatic rotation
- ✅ **Captive Portal**: Web-based configuration interface with responsive design
- ✅ **MQTT Client**: Full MQTT support with Last Will Testament (LWT)
- ✅ **Home Assistant Discovery**: Automatic entity creation via MQTT discovery
- ✅ **OTA Updates**: Over-the-air firmware updates with SHA-256 verification
- ✅ **Failsafe Mode**: Boot loop detection and recovery interface
- ✅ **mDNS Discovery**: Automatic MQTT broker discovery
- ✅ **Watchdog Timer**: Automatic recovery from hangs
- ✅ **Non-blocking Architecture**: Cooperative scheduler for smooth operation

### Advanced Features
- **Atomic Configuration Writes**: Safe configuration persistence with backup
- **Boot Loop Protection**: Automatic failsafe after 3 failed boots in 60s
- **Exponential Backoff**: Smart reconnection logic for Wi-Fi and MQTT
- **Significant Change Detection**: Immediate publishing on threshold breach
- **Memory Management**: Automatic garbage collection and monitoring
- **Rich Diagnostics**: Web-based diagnostics page in failsafe mode
- **LED Status Indicators**: Visual feedback for system state
- **Remote Configuration**: Update settings via MQTT
- **Sensor Retries**: Automatic retry logic for sensor errors

## 🔧 Hardware Requirements

### Required Components
1. **ESP32 DevKit v1** (ESP-WROOM-32)
   - 30-pin development board
   - USB micro connector for programming
   
2. **SHTC3 Sensor Module**
   - I2C temperature/humidity sensor
   - Operating voltage: 3.3V
   - I2C address: 0x70

3. **WS2812B LED Ring**
   - 12 LEDs (can be adjusted in config)
   - 5V power supply
   - Data input on single wire

### Optional Components
- Level shifter (for LED data line 3.3V → 5V)
- 1000µF capacitor (for LED power stability)
- 470Ω resistor (for LED data line)

## 🔌 Wiring Diagram

### SHTC3 Sensor (I2C)
```
SHTC3          ESP32
-----          -----
VCC    →       3.3V
GND    →       GND
SDA    →       GPIO21 (SDA)
SCL    →       GPIO22 (SCL)
```

### WS2812B LED Ring
```
LED Ring       ESP32/Power
--------       -----------
VCC    →       5V (external recommended for 12 LEDs)
GND    →       GND (common ground with ESP32)
DIN    →       GPIO15 (through 470Ω resistor)
```

### Power Considerations
- ESP32 can be powered via USB (5V) during development
- For production, use a 5V power supply (≥1A for LEDs)
- WS2812B draws ~60mA per LED at full brightness (white)
- 12 LEDs at full brightness = ~720mA

### Recommended Connections
```
       ┌─────────────────┐
       │   ESP32 DevKit  │
       │                 │
 USB ──┤ MICRO-USB       │
       │                 │
       │ GPIO21 ─────────┼──── SDA (SHTC3)
       │ GPIO22 ─────────┼──── SCL (SHTC3)
       │ GPIO15 ─────┐   │
       │             │   │
       │ 3.3V ───────┼───┼──── VCC (SHTC3)
       │ GND ────────┼───┼──── GND (SHTC3 + LEDs)
       └─────────────┼───┘
                     │
                 470Ω │
                     │
    ┌────────────────┴────────┐
    │  WS2812B LED Ring       │
    │  12 LEDs                │
    │                         │
    │  DIN ←─────────────────┘
    │  VCC ←───── 5V (external)
    │  GND ←───── GND (common)
    └─────────────────────────┘
```

## 💻 Software Requirements

### Development Tools
1. **Python 3.x** (for esptool and rshell)
2. **esptool.py** (for flashing firmware)
3. **rshell** or **ampy** (for file transfer)
4. **MicroPython firmware** (ESP32 build)

### Installation of Tools

```bash
# Install esptool
pip install esptool

# Install rshell
pip install rshell

# Alternative: Install ampy
pip install adafruit-ampy
```

### MicroPython Firmware
Download the latest ESP32 MicroPython firmware from:
https://micropython.org/download/esp32/

Recommended: ESP32_GENERIC-20231005-v1.21.0.bin or newer

## 📥 Installation

### Step 1: Flash MicroPython Firmware

```bash
# Erase flash (first time only)
esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash

# Flash MicroPython firmware
esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x1000 ESP32_GENERIC-*.bin
```

**Note**: Replace `/dev/ttyUSB0` with your actual port:
- Linux: `/dev/ttyUSB0` or `/dev/ttyACM0`
- macOS: `/dev/cu.usbserial-*`
- Windows: `COM3`, `COM4`, etc.

### Step 2: Upload Firmware Files

#### Option A: Using rshell

```bash
# Connect to device
rshell --port /dev/ttyUSB0

# Copy all files
cp *.py /pyboard/

# Verify files
ls /pyboard/

# Exit
exit
```

#### Option B: Using ampy

```bash
# Upload each file
for file in *.py; do
    ampy --port /dev/ttyUSB0 put $file
done

# List files to verify
ampy --port /dev/ttyUSB0 ls
```

#### Option C: Using Thonny IDE

1. Open Thonny IDE
2. Select MicroPython (ESP32) interpreter
3. Connect to device
4. Upload files via file browser

### Step 3: Configure Credentials

Create `secrets.py` from template:

```bash
cp secrets_template.py secrets.py
```

Edit `secrets.py` with your credentials:

```python
WIFI_PROFILES = [
    {
        \"ssid\": \"YourWiFiSSID\",
        \"password\": \"YourWiFiPassword\",
        \"priority\": 1
    }
]

MQTT_BROKER = \"192.168.1.100\"  # Your MQTT broker IP
MQTT_PORT = 1883
MQTT_USERNAME = \"mqtt_user\"
MQTT_PASSWORD = \"mqtt_password\"

DEVICE_LOCATION = \"living_room\"
```

Upload secrets.py:
```bash
ampy --port /dev/ttyUSB0 put secrets.py
```

### Step 4: Reboot Device

```bash
# Using rshell
rshell --port /dev/ttyUSB0 repl
# Press Ctrl+D to reboot

# Or use the EN button on the ESP32
```

## ⚙️ Configuration

### Configuration Methods

1. **secrets.py**: Pre-configure before upload (recommended)
2. **Captive Portal**: Configure via web interface on first boot
3. **MQTT Commands**: Update configuration remotely

### Configuration File Structure

The device uses `config.json` for persistent configuration:

```json
{
  \"device\": {
    \"name\": \"ESP32-SHTC3-abc123\",
    \"location\": \"living_room\",
    \"firmware_version\": \"1.0.0\"
  },
  \"wifi\": {
    \"profiles\": [
      {\"ssid\": \"WiFi1\", \"password\": \"pass1\", \"priority\": 1},
      {\"ssid\": \"WiFi2\", \"password\": \"pass2\", \"priority\": 2}
    ]
  },
  \"mqtt\": {
    \"enabled\": true,
    \"broker\": \"192.168.1.100\",
    \"port\": 1883,
    \"username\": \"mqtt_user\",
    \"password\": \"mqtt_password\",
    \"base_topic\": \"home/living_room/abc123\"
  },
  \"sensor\": {
    \"read_interval\": 10,
    \"publish_interval\": 30,
    \"temp_offset\": 0.0,
    \"humidity_offset\": 0.0
  },
  \"led\": {
    \"enabled\": true,
    \"brightness\": 128,
    \"effect\": \"solid\",
    \"color\": [255, 255, 255]
  },
  \"ota\": {
    \"enabled\": true,
    \"auto_update\": false
  }
}
```

### Captive Portal Configuration

If no Wi-Fi credentials are configured, device starts in AP mode:

1. **Connect to AP**:
   - SSID: `ESP32-SHTC3-XXXX` (XXXX = last 4 chars of MAC)
   - Password: `configure123`

2. **Open Browser**:
   - Navigate to: `http://192.168.4.1`
   - Configuration page loads automatically

3. **Configure Settings**:
   - Select Wi-Fi network(s) from scan results
   - Enter passwords
   - Configure MQTT broker (optional)
   - Set device location
   - Click \"Save Configuration\"

4. **Device Reboots**:
   - Connects to configured Wi-Fi
   - Starts MQTT client
   - Publishes Home Assistant discovery

## 🚀 Usage

### Monitoring Output

Connect to serial console to see logs:

```bash
# Using screen
screen /dev/ttyUSB0 115200

# Using minicom
minicom -D /dev/ttyUSB0 -b 115200

# Using rshell
rshell --port /dev/ttyUSB0 repl
```

### Expected Boot Sequence

```
==================================================
ESP32 SHTC3 Firmware - Boot Sequence
==================================================
[BOOT] Boot #1 in window
[BOOT] Normal boot sequence
[BOOT] Boot sequence complete, starting main.py...

==================================================
Device: ESP32-SHTC3-abc123
Device ID: abc123
Firmware: ESP32-SHTC3-HA v1.0.0
Build Date: 2026-02-13
Reset Cause: Power on
Frequency: 240 MHz
Free Memory: 98304 bytes
==================================================

[MAIN] Initializing components...
[LED] Initialized 12 LEDs on pin 15
[I2C] Found devices: ['0x70']
[SHTC3] Sensor ID verified: 0x0807
[SHTC3] Sensor initialized
[WIFI] Loaded 1 profiles from secrets
[WIFI] Attempting to connect to 'YourWiFi'...
[WIFI] Connected to 'YourWiFi'
[WIFI] IP: 192.168.1.150
[MQTT] Connecting to 192.168.1.100:1883...
[MQTT] Connected
[HA] Publishing discovery messages...
[MAIN] Initialization complete
[SCHEDULER] Starting with 6 tasks
[SENSOR] Published: T=22.5°C, H=45.2%
```

### Testing Sensor Readings

Sensor data is published every 30 seconds (configurable):

```
[SENSOR] Published: T=22.5°C, H=45.2%
[SENSOR] Published: T=22.6°C, H=45.5%
```

Immediate publish on significant change (>0.5°C or >2% humidity):
```
[SENSOR] Significant change detected
[SENSOR] Published: T=25.1°C, H=52.3%
```

## 📡 MQTT Topics

### Base Topic Format
```
home/<location>/<device_id>
```

Example: `home/living_room/abc123`

### Published Topics

| Topic | QoS | Retain | Description |
|-------|-----|--------|-------------|
| `.../status` | 0 | Yes | Device availability (online/offline) |
| `.../state` | 0 | No | Sensor data (temp, humidity, rssi, uptime) |
| `.../led/state` | 0 | Yes | LED state (on/off, color, effect) |

### Subscribed Topics

| Topic | Description |
|-------|-------------|
| `.../command` | General commands (restart, scan_wifi) |
| `.../config` | Configuration updates |
| `.../led/command` | LED control commands |
| `.../ota` | OTA update triggers |

### State Payload Example

```json
{
  \"temperature\": 22.5,
  \"humidity\": 45.2,
  \"rssi\": -65,
  \"uptime\": 3600,
  \"timestamp\": 1707840000
}
```

## 🏠 Home Assistant Integration

### Automatic Discovery

Device automatically publishes MQTT discovery messages for:

1. **Temperature Sensor**
   - Entity ID: `sensor.esp32_shtc3_abc123_temperature`
   - Device Class: `temperature`
   - Unit: `°C`

2. **Humidity Sensor**
   - Entity ID: `sensor.esp32_shtc3_abc123_humidity`
   - Device Class: `humidity`
   - Unit: `%`

3. **RSSI Sensor**
   - Entity ID: `sensor.esp32_shtc3_abc123_rssi`
   - Device Class: `signal_strength`
   - Unit: `dBm`

4. **Uptime Sensor**
   - Entity ID: `sensor.esp32_shtc3_abc123_uptime`
   - Unit: `s`

5. **LED Light**
   - Entity ID: `light.esp32_shtc3_abc123_led`
   - Features: RGB, Brightness, Effects

### Manual Configuration

If auto-discovery doesn't work, add to `configuration.yaml`:

```yaml
mqtt:
  sensor:
    - name: \"Living Room Temperature\"
      state_topic: \"home/living_room/abc123/state\"
      value_template: \"{{ value_json.temperature }}\"
      unit_of_measurement: \"°C\"
      device_class: \"temperature\"
      
    - name: \"Living Room Humidity\"
      state_topic: \"home/living_room/abc123/state\"
      value_template: \"{{ value_json.humidity }}\"
      unit_of_measurement: \"%\"
      device_class: \"humidity\"
  
  light:
    - name: \"Living Room LED\"
      command_topic: \"home/living_room/abc123/led/command\"
      state_topic: \"home/living_room/abc123/led/state\"
      schema: \"json\"
      brightness: true
      rgb: true
      effect: true
      effect_list:
        - \"solid\"
        - \"rainbow\"
        - \"breathing\"
        - \"humidity_gauge\"
        - \"temperature_gauge\"
```

### Controlling the LED

Via Home Assistant UI or automations:

```yaml
# Turn on with color
service: light.turn_on
target:
  entity_id: light.esp32_shtc3_abc123_led
data:
  brightness: 200
  rgb_color: [255, 0, 0]
  effect: \"rainbow\"

# Turn off
service: light.turn_off
target:
  entity_id: light.esp32_shtc3_abc123_led
```

## 🔄 OTA Updates

### Preparing Update Package

1. Create firmware package (main.py or full bundle)
2. Calculate SHA-256 hash:
   ```bash
   sha256sum main.py
   ```

3. Host on HTTP server:
   ```bash
   python3 -m http.server 8000
   ```

### Triggering OTA Update

Via MQTT:

```bash
mosquitto_pub -h localhost -t \"home/living_room/abc123/ota\" -m '{
  \"url\": \"http://192.168.1.100:8000/main.py\",
  \"sha256\": \"abc123def456...\"
}'
```

### OTA Process

1. Device receives OTA command
2. Downloads firmware to temporary file
3. Verifies SHA-256 hash
4. Creates backup of current firmware
5. Replaces main.py with new version
6. Reboots device

### Rollback

If new firmware fails to boot 3 times, device enters failsafe mode where you can:
- View diagnostics
- Reset boot counter
- Clear configuration
- Manually restore backup

## 🛡️ Failsafe Mode

### Triggering Failsafe

Failsafe mode activates when:
- 3 boot failures within 60 seconds
- Manual trigger via `failsafe.flag` file

### Accessing Failsafe

1. **Connect to Failsafe AP**:
   - SSID: `ESP32-SHTC3-XXXX-FAILSAFE`
   - Password: `failsafe123`

2. **Open Browser**:
   - Navigate to: `http://192.168.4.1`

3. **Diagnostics Page Shows**:
   - Error reason and timestamp
   - System information
   - Memory usage
   - Reset cause

4. **Recovery Actions**:
   - **Reset Boot Counter**: Clear boot loop detection
   - **Clear Configuration**: Remove all settings
   - **Reboot Device**: Restart system
   - **View Logs**: See detailed error logs

### Exiting Failsafe

- Reset boot counter and reboot
- Or fix the issue and clear `failsafe.flag`

## 💡 LED Effects

### Available Effects

1. **solid**: Static color
2. **rainbow**: Rotating rainbow pattern
3. **breathing**: Fade in/out effect
4. **humidity_gauge**: Blue bar showing humidity level
5. **temperature_gauge**: Color gradient showing temperature

### Controlling via MQTT

```bash
# Solid red
mosquitto_pub -h localhost -t \"home/living_room/abc123/led/command\" -m '{
  \"state\": \"ON\",
  \"brightness\": 255,
  \"color\": {\"r\": 255, \"g\": 0, \"b\": 0},
  \"effect\": \"solid\"
}'

# Rainbow effect
mosquitto_pub -h localhost -t \"home/living_room/abc123/led/command\" -m '{
  \"state\": \"ON\",
  \"brightness\": 128,
  \"effect\": \"rainbow\"
}'

# Turn off
mosquitto_pub -h localhost -t \"home/living_room/abc123/led/command\" -m '{
  \"state\": \"OFF\"
}'
```

### Status Indicators

- **Blue blinking**: Wi-Fi disconnected
- **Red blinking**: Failsafe mode
- **Orange**: Captive portal active
- **Off**: Idle (when MQTT connected)

## 🔍 Troubleshooting

### Device Not Booting

1. Check serial output for errors
2. Verify MicroPython firmware is flashed correctly
3. Re-flash firmware if needed
4. Check for boot loop (failsafe should activate)

### Wi-Fi Connection Issues

1. Verify SSID and password in `secrets.py`
2. Check Wi-Fi signal strength
3. Ensure 2.4GHz network (ESP32 doesn't support 5GHz)
4. Try captive portal for configuration
5. Check router settings (MAC filtering, DHCP)

### SHTC3 Sensor Not Detected

1. Verify wiring (SDA, SCL, VCC, GND)
2. Check I2C address (should be 0x70):
   ```python
   from machine import I2C, Pin
   i2c = I2C(0, scl=Pin(22), sda=Pin(21))
   print(i2c.scan())  # Should show [112] (0x70)
   ```
3. Try different I2C frequency
4. Check sensor module for damage

### LED Ring Not Working

1. Verify wiring (DIN to GPIO15, VCC to 5V, GND)
2. Check color order setting (RGB vs GRB)
3. Ensure adequate power supply
4. Test LEDs individually
5. Try different GPIO pin

### MQTT Not Connecting

1. Verify broker IP and port
2. Check broker is running and accessible
3. Test with mosquitto_sub:
   ```bash
   mosquitto_sub -h 192.168.1.100 -t \"#\" -v
   ```
4. Check firewall settings
5. Verify username/password if authentication enabled

### Memory Errors

1. Reduce sensor read frequency
2. Increase GC frequency in config
3. Disable unused features
4. Check for memory leaks

### OTA Update Fails

1. Verify firmware URL is accessible
2. Check SHA-256 hash matches
3. Ensure sufficient free flash space
4. Try smaller update package
5. Check network stability during download

## 🧪 Test Plan

### Unit Tests

#### 1. Hardware Tests

**SHTC3 Sensor**
```python
from shtc3 import create_shtc3
sensor = create_shtc3()
temp, hum = sensor.read()
print(f\"T: {temp}°C, H: {hum}%\")
# Expected: Valid temperature and humidity readings
```

**LED Ring**
```python
from led_ring import create_led_ring
led = create_led_ring()
led.fill(255, 0, 0)  # Red
# Expected: All LEDs turn red
```

#### 2. Network Tests

**Wi-Fi Connection**
```python
from wifi_manager import create_wifi_manager
wifi = create_wifi_manager()
wifi.connect()
print(wifi.get_connection_info())
# Expected: Connected with valid IP
```

**MQTT Connection**
```python
from mqtt_client import create_mqtt_client
mqtt = create_mqtt_client(config)
mqtt.connect()
mqtt.publish(\"test/topic\", \"Hello\")
# Expected: Message received by broker
```

#### 3. Feature Tests

**Captive Portal**
- Boot without Wi-Fi credentials
- Expected: AP starts, web interface accessible

**Boot Loop Detection**
- Trigger 3 reboots within 60 seconds
- Expected: Failsafe mode activates

**OTA Update**
- Publish OTA command
- Expected: Firmware downloads and applies

#### 4. Integration Tests

**Full Boot Sequence**
1. Flash firmware
2. Configure via captive portal
3. Verify Wi-Fi connection
4. Verify MQTT connection
5. Verify sensor readings
6. Verify Home Assistant discovery
7. Control LED via MQTT

**Recovery Tests**
1. Enter failsafe mode
2. Access diagnostics
3. Reset boot counter
4. Exit failsafe
5. Verify normal operation

### Test Checklist

- [ ] MicroPython firmware flashes successfully
- [ ] All files upload without errors
- [ ] Device boots and shows startup messages
- [ ] SHTC3 sensor detected on I2C
- [ ] LED ring lights up
- [ ] Wi-Fi connects to configured network
- [ ] MQTT connects to broker
- [ ] Home Assistant discovers all entities
- [ ] Temperature sensor updates in HA
- [ ] Humidity sensor updates in HA
- [ ] LED control works from HA
- [ ] LED effects work correctly
- [ ] Captive portal accessible when no Wi-Fi configured
- [ ] Configuration saves and persists across reboots
- [ ] Boot loop protection activates after 3 failures
- [ ] Failsafe mode accessible and functional
- [ ] OTA update completes successfully
- [ ] Watchdog timer prevents hangs
- [ ] Memory management works (no crashes)
- [ ] Reconnection logic works for Wi-Fi and MQTT

## 📚 API Reference

### Storage Module

```python
from storage import load_config, save_config, update_config

# Load configuration
config = load_config()

# Save configuration
save_config(config)

# Update specific fields
update_config({'led': {'brightness': 200}})
```

### WiFi Manager

```python
from wifi_manager import WiFiManager

wifi = WiFiManager(profiles=[...])
wifi.connect()
wifi.scan()
wifi.disconnect()
```

### MQTT Client

```python
from mqtt_client import MQTTClientWrapper

mqtt = MQTTClientWrapper(config)
mqtt.connect()
mqtt.publish(\"topic\", \"payload\")
mqtt.subscribe(\"topic\", callback)
mqtt.check_msg()
```

### LED Ring

```python
from led_ring import LEDRing

led = LEDRing(pin=15, num_leds=12)
led.set_effect(\"rainbow\")
led.set_brightness(128)
led.update()  # Call in main loop
```

### SHTC3 Sensor

```python
from shtc3 import SHTC3

sensor = SHTC3(i2c)
temp, hum = sensor.read()
```

## 📝 License

This project is provided as-is for educational and personal use.

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

## 📧 Support

For questions and support, please open an issue on the project repository.

---

**Built with ❤️ for the Home Assistant community**
