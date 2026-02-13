# main.py - Main orchestrator with cooperative scheduler

import time
import machine
import gc
import ujson as json

# Import modules
import config
from storage import load_config, save_config, update_config
from util import Scheduler, IntervalTimer, Timer, ExponentialBackoff, check_memory, format_uptime
from wifi_manager import create_wifi_manager
from captive_portal import start_captive_portal
from mqtt_client import create_mqtt_client
from ha_discovery import create_ha_discovery
from shtc3 import create_shtc3
from led_ring import create_led_ring
from ota import perform_ota_update
from failsafe import check_failsafe, start_failsafe

class DeviceController:
    """Main device controller."""
    
    def __init__(self):
        # Print system info
        config.print_system_info()
        
        # Load configuration
        self.config = load_config()
        
        # Components
        self.wifi = None
        self.mqtt = None
        self.sensor = None
        self.led = None
        self.ha_discovery = None
        
        # State
        self.start_time = time.time()
        self.last_sensor_read = None
        self.last_sensor_publish = None
        self.sensor_data = {'temperature': None, 'humidity': None}
        self.mqtt_reconnect_backoff = ExponentialBackoff()
        
        # Scheduler
        self.scheduler = Scheduler()
        
        # Watchdog
        self.wdt = None
        if config.WDT_ENABLED:
            try:
                self.wdt = machine.WDT(timeout=config.WDT_TIMEOUT)
                print("[MAIN] Watchdog enabled")
            except Exception as e:
                print(f"[MAIN] Watchdog init failed: {e}")
    
    def initialize(self):
        """Initialize all components."""
        print("\n[MAIN] Initializing components...")
        
        # Initialize LED ring first (for status indication)
        led_config = self.config.get('led', {})
        self.led = create_led_ring(
            pin=config.LED_PIN,
            num_leds=config.LED_COUNT,
            color_order=config.LED_COLOR_ORDER
        )
        
        if self.led:
            # Show blue blinking during initialization
            self.led.set_effect('blink', config.LED_STATUS_DISCONNECTED, speed=500)
        
        # Initialize sensor
        self.sensor = create_shtc3(
            sda_pin=config.I2C_SDA_PIN,
            scl_pin=config.I2C_SCL_PIN,
            freq=config.I2C_FREQ
        )
        
        if not self.sensor:
            print("[MAIN] Warning: Sensor not available")
        
        # Setup Wi-Fi
        self.wifi = create_wifi_manager()
        
        # Try to connect to Wi-Fi
        if not self.wifi.connect(retry=True):
            print("[MAIN] Wi-Fi connection failed, starting captive portal...")
            
            if self.led:
                self.led.set_effect('solid', (255, 165, 0))  # Orange for portal
            
            # Start captive portal
            portal_config = start_captive_portal(timeout=config.CAPTIVE_PORTAL_TIMEOUT)
            
            if portal_config:
                # Save configuration
                print("[MAIN] Saving portal configuration...")
                self.config = {**self.config, **portal_config}
                save_config(self.config)
                
                # Reboot to apply
                print("[MAIN] Configuration saved, rebooting...")
                time.sleep(2)
                machine.reset()
            else:
                print("[MAIN] Portal timeout, continuing without Wi-Fi...")
        
        # Setup MQTT
        if self.wifi.is_connected():
            mqtt_config = self.config.get('mqtt', {})
            
            # Try mDNS discovery if no broker configured
            if not mqtt_config.get('broker'):
                print("[MAIN] No MQTT broker configured, trying discovery...")
                from mdns_discovery import discover_mqtt_broker
                broker_info = discover_mqtt_broker(timeout=5)
                if broker_info:
                    mqtt_config['broker'] = broker_info['ip']
                    mqtt_config['port'] = broker_info['port']
                    update_config({'mqtt': mqtt_config})
            
            if mqtt_config.get('broker'):
                # Update base topic with location
                location = self.config.get('device', {}).get('location', 'living_room')
                mqtt_config['base_topic'] = config.get_base_topic(location)
                mqtt_config['client_id'] = config.DEVICE_ID
                
                self.mqtt = create_mqtt_client(mqtt_config)
                
                if self.mqtt.connect():
                    print("[MAIN] MQTT connected")
                    
                    # Setup message handlers
                    self._setup_mqtt_handlers()
                    
                    # Publish Home Assistant discovery
                    if mqtt_config.get('discovery_enabled', True):
                        self.ha_discovery = create_ha_discovery(self.config)
                        self.ha_discovery.publish_all_discoveries(self.mqtt)
                else:
                    print("[MAIN] MQTT connection failed")
        
        # Update LED to idle state
        if self.led:
            if self.mqtt and self.mqtt.is_connected():
                led_cfg = self.config.get('led', {})
                self.led.set_state(
                    'ON' if led_cfg.get('enabled', True) else 'OFF',
                    brightness=led_cfg.get('brightness', 128),
                    color=tuple(led_cfg.get('color', [255, 255, 255])),
                    effect=led_cfg.get('effect', 'solid')
                )
            else:
                self.led.set_effect('blink', config.LED_STATUS_DISCONNECTED, speed=1000)
        
        print("[MAIN] Initialization complete\n")
    
    def _setup_mqtt_handlers(self):
        """Setup MQTT message handlers."""
        base_topic = self.mqtt.base_topic
        
        # Subscribe to command topics
        self.mqtt.subscribe(f"{base_topic}/command", self._handle_command)
        self.mqtt.subscribe(f"{base_topic}/config", self._handle_config)
        self.mqtt.subscribe(f"{base_topic}/led/command", self._handle_led_command)
        self.mqtt.subscribe(f"{base_topic}/ota", self._handle_ota_command)
    
    def _handle_command(self, topic, message):
        """Handle general commands."""
        print(f"[MQTT] Command: {message}")
        
        try:
            cmd = json.loads(message)
            
            if cmd.get('action') == 'restart':
                print("[MAIN] Restart requested")
                time.sleep(1)
                machine.reset()
            
            elif cmd.get('action') == 'scan_wifi':
                networks = self.wifi.scan()
                self.mqtt.publish_json(f"{topic}/response", {'networks': networks})
            
        except Exception as e:
            print(f"[MQTT] Command error: {e}")
    
    def _handle_config(self, topic, message):
        """Handle configuration updates."""
        print(f"[MQTT] Config update: {message}")
        
        try:
            config_update = json.loads(message)
            update_config(config_update)
            self.config = load_config()
            print("[MQTT] Configuration updated")
        except Exception as e:
            print(f"[MQTT] Config error: {e}")
    
    def _handle_led_command(self, topic, message):
        """Handle LED commands."""
        if not self.led:
            return
        
        try:
            cmd = json.loads(message)
            
            state = cmd.get('state', 'ON')
            brightness = cmd.get('brightness', 255)
            color = cmd.get('color', {})
            effect = cmd.get('effect', 'solid')
            
            # Extract RGB
            r = color.get('r', 255)
            g = color.get('g', 255)
            b = color.get('b', 255)
            
            self.led.set_state(state, brightness, (r, g, b), effect)
            
            # Publish state
            self._publish_led_state()
            
            print(f"[LED] Command executed: {state}, RGB({r},{g},{b}), {effect}")
            
        except Exception as e:
            print(f"[MQTT] LED command error: {e}")
    
    def _handle_ota_command(self, topic, message):
        """Handle OTA update commands."""
        try:
            cmd = json.loads(message)
            
            url = cmd.get('url')
            sha256 = cmd.get('sha256')
            
            if not url:
                print("[OTA] No URL provided")
                return
            
            print(f"[OTA] Update requested: {url}")
            
            # Publish status
            self.mqtt.publish_json(f"{topic}/status", {'status': 'downloading'})
            
            # Perform update
            success = perform_ota_update(url, sha256)
            
            if success:
                self.mqtt.publish_json(f"{topic}/status", {'status': 'success'})
            else:
                self.mqtt.publish_json(f"{topic}/status", {'status': 'failed'})
            
        except Exception as e:
            print(f"[OTA] Error: {e}")
            self.mqtt.publish_json(f"{topic}/status", {'status': 'error', 'message': str(e)})
    
    def _setup_tasks(self):
        """Setup scheduled tasks."""
        sensor_cfg = self.config.get('sensor', {})
        
        # Sensor reading task
        self.scheduler.add_task(
            'read_sensor',
            self._task_read_sensor,
            sensor_cfg.get('read_interval', 10) * 1000
        )
        
        # Sensor publish task
        self.scheduler.add_task(
            'publish_sensor',
            self._task_publish_sensor,
            sensor_cfg.get('publish_interval', 30) * 1000
        )
        
        # MQTT check messages task
        self.scheduler.add_task(
            'mqtt_check',
            self._task_mqtt_check,
            100  # Check every 100ms
        )
        
        # LED update task
        self.scheduler.add_task(
            'led_update',
            self._task_led_update,
            50  # Update every 50ms for smooth animations
        )
        
        # Memory management task
        self.scheduler.add_task(
            'memory_gc',
            self._task_memory_gc,
            60 * 1000  # Every 60 seconds
        )
        
        # Connection monitor task
        self.scheduler.add_task(
            'connection_monitor',
            self._task_connection_monitor,
            5 * 1000  # Every 5 seconds
        )
    
    def _task_read_sensor(self):
        """Task: Read sensor data."""
        if not self.sensor:
            return
        
        temp, hum = self.sensor.read()
        
        if temp is not None and hum is not None:
            # Apply calibration offsets
            sensor_cfg = self.config.get('sensor', {})
            temp += sensor_cfg.get('temp_offset', 0.0)
            hum += sensor_cfg.get('humidity_offset', 0.0)
            
            # Check for significant change
            significant_change = False
            if self.sensor_data['temperature'] is not None:
                temp_delta = abs(temp - self.sensor_data['temperature'])
                hum_delta = abs(hum - self.sensor_data['humidity'])
                
                if (temp_delta >= config.TEMP_CHANGE_THRESHOLD or 
                    hum_delta >= config.HUMIDITY_CHANGE_THRESHOLD):
                    significant_change = True
            
            self.sensor_data['temperature'] = temp
            self.sensor_data['humidity'] = hum
            self.last_sensor_read = time.time()
            
            # Update LED gauge if active
            if self.led:
                self.led.set_gauge_data(temperature=temp, humidity=hum)
            
            # Publish immediately on significant change
            if significant_change:
                print(f"[SENSOR] Significant change detected")
                self._task_publish_sensor()
    
    def _task_publish_sensor(self):
        """Task: Publish sensor data to MQTT."""
        if not self.mqtt or not self.mqtt.is_connected():
            return
        
        if self.sensor_data['temperature'] is None:
            return
        
        # Build state payload
        state = {
            'temperature': round(self.sensor_data['temperature'], 2),
            'humidity': round(self.sensor_data['humidity'], 2),
            'rssi': self.wifi.get_connection_info().get('rssi') if self.wifi.is_connected() else None,
            'uptime': int(time.time() - self.start_time),
            'timestamp': time.time()
        }
        
        # Publish
        self.mqtt.publish_state(state)
        self.last_sensor_publish = time.time()
        
        print(f"[SENSOR] Published: T={state['temperature']}°C, H={state['humidity']}%")
    
    def _task_mqtt_check(self):
        """Task: Check for MQTT messages."""
        if self.mqtt and self.mqtt.is_connected():
            self.mqtt.check_msg()
    
    def _task_led_update(self):
        """Task: Update LED animations."""
        if self.led:
            self.led.update()
    
    def _task_memory_gc(self):
        """Task: Memory management."""
        check_memory(threshold=config.GC_THRESHOLD, force_gc=True)
    
    def _task_connection_monitor(self):
        """Task: Monitor and maintain connections."""
        # Check Wi-Fi
        if not self.wifi.is_connected():
            print("[MAIN] Wi-Fi disconnected, reconnecting...")
            if self.led:
                self.led.set_effect('blink', config.LED_STATUS_DISCONNECTED, speed=500)
            self.wifi.connect(retry=False)
        
        # Check MQTT
        if self.wifi.is_connected() and self.mqtt:
            if not self.mqtt.is_connected():
                print("[MAIN] MQTT disconnected, reconnecting...")
                self.mqtt.reconnect()
    
    def _publish_led_state(self):
        """Publish LED state to MQTT."""
        if self.mqtt and self.mqtt.is_connected() and self.led:
            state = self.led.get_state()
            self.mqtt.publish_json(f"{self.mqtt.base_topic}/led/state", state)
    
    def run(self):
        """Run main loop."""
        # Setup tasks
        self._setup_tasks()
        
        # Initial sensor read and publish
        self._task_read_sensor()
        time.sleep(0.5)
        self._task_publish_sensor()
        
        print("[MAIN] Starting main loop...\n")
        
        # Main loop
        try:
            while True:
                # Feed watchdog
                if self.wdt:
                    self.wdt.feed()
                
                # Run scheduler
                self.scheduler.run_once()
                
                # Small delay
                time.sleep_ms(10)
                
        except KeyboardInterrupt:
            print("\n[MAIN] Interrupted by user")
            self.shutdown()
        except Exception as e:
            print(f"\n[MAIN] Fatal error: {e}")
            import sys
            sys.print_exception(e)
            self.shutdown()
            raise
    
    def shutdown(self):
        """Graceful shutdown."""
        print("\n[MAIN] Shutting down...")
        
        # Disconnect MQTT
        if self.mqtt:
            self.mqtt.disconnect()
        
        # Disconnect Wi-Fi
        if self.wifi:
            self.wifi.disconnect()
        
        # Turn off LED
        if self.led:
            self.led.clear()
        
        print("[MAIN] Shutdown complete")

def main():
    """Main entry point."""
    try:
        # Check for failsafe mode
        if check_failsafe():
            print("[MAIN] Failsafe mode detected")
            start_failsafe()
            return
        
        # Create and run controller
        controller = DeviceController()
        controller.initialize()
        controller.run()
        
    except Exception as e:
        print(f"[MAIN] Fatal error: {e}")
        import sys
        sys.print_exception(e)
        
        # Log error to failsafe log
        try:
            import io
            log_stream = io.StringIO()
            sys.print_exception(e, log_stream)
            
            with open('failsafe.log', 'a') as f:
                f.write(f"\n\n=== Error at {time.time()} ===\n")
                f.write(log_stream.getvalue())
        except:
            pass
        
        # Reboot after delay
        print("[MAIN] Rebooting in 5 seconds...")
        time.sleep(5)
        machine.reset()

if __name__ == '__main__':
    main()
