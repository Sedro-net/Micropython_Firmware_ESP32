# ha_discovery.py - Home Assistant MQTT discovery payloads

import ujson as json

class HADiscovery:
    """Generate Home Assistant MQTT discovery payloads."""
    
    def __init__(self, base_topic, device_info):
        """
        Initialize HA discovery.
        
        Args:
            base_topic: Base MQTT topic (e.g., home/living_room/abc123)
            device_info: Device information dict
        """
        self.base_topic = base_topic
        self.device_info = device_info
        self.discovery_prefix = "homeassistant"
    
    def get_device_payload(self):
        """Get device information payload."""
        return {
            "identifiers": [self.device_info.get('device_id')],
            "name": self.device_info.get('name'),
            "model": self.device_info.get('model', 'ESP32-SHTC3'),
            "manufacturer": self.device_info.get('manufacturer', 'Custom'),
            "sw_version": self.device_info.get('sw_version', '1.0.0')
        }
    
    def create_sensor_discovery(self, sensor_type, name, unit, icon, device_class=None, state_class=None):
        """Create sensor discovery payload.
        
        Args:
            sensor_type: Type identifier (e.g., 'temperature', 'humidity')
            name: Human-readable name
            unit: Unit of measurement
            icon: MDI icon
            device_class: Home Assistant device class
            state_class: Home Assistant state class
        """
        unique_id = f"{self.device_info['device_id']}_{sensor_type}"
        
        payload = {
            "name": name,
            "unique_id": unique_id,
            "object_id": unique_id,
            "state_topic": f"{self.base_topic}/state",
            "value_template": f"{{{{ value_json.{sensor_type} }}}}",
            "unit_of_measurement": unit,
            "icon": icon,
            "device": self.get_device_payload(),
            "availability_topic": f"{self.base_topic}/status",
            "payload_available": "online",
            "payload_not_available": "offline"
        }
        
        if device_class:
            payload["device_class"] = device_class
        
        if state_class:
            payload["state_class"] = state_class
        
        discovery_topic = f"{self.discovery_prefix}/sensor/{unique_id}/config"
        
        return discovery_topic, payload
    
    def create_light_discovery(self):
        """Create LED light discovery payload."""
        unique_id = f"{self.device_info['device_id']}_led"
        
        payload = {
            "name": f"{self.device_info['name']} LED",
            "unique_id": unique_id,
            "object_id": unique_id,
            "command_topic": f"{self.base_topic}/led/command",
            "state_topic": f"{self.base_topic}/led/state",
            "schema": "json",
            "brightness": True,
            "rgb": True,
            "effect": True,
            "effect_list": ["solid", "rainbow", "breathing", "humidity_gauge", "temperature_gauge"],
            "device": self.get_device_payload(),
            "availability_topic": f"{self.base_topic}/status",
            "payload_available": "online",
            "payload_not_available": "offline"
        }
        
        discovery_topic = f"{self.discovery_prefix}/light/{unique_id}/config"
        
        return discovery_topic, payload
    
    def publish_all_discoveries(self, mqtt_client):
        """Publish all discovery messages.
        
        Args:
            mqtt_client: MQTT client instance
            
        Returns:
            True if all published successfully
        """
        discoveries = []
        
        # Temperature sensor
        discoveries.append(
            self.create_sensor_discovery(
                'temperature',
                f"{self.device_info['name']} Temperature",
                '°C',
                'mdi:thermometer',
                device_class='temperature',
                state_class='measurement'
            )
        )
        
        # Humidity sensor
        discoveries.append(
            self.create_sensor_discovery(
                'humidity',
                f"{self.device_info['name']} Humidity",
                '%',
                'mdi:water-percent',
                device_class='humidity',
                state_class='measurement'
            )
        )
        
        # RSSI sensor
        discoveries.append(
            self.create_sensor_discovery(
                'rssi',
                f"{self.device_info['name']} RSSI",
                'dBm',
                'mdi:wifi',
                device_class='signal_strength',
                state_class='measurement'
            )
        )
        
        # Uptime sensor
        discoveries.append(
            self.create_sensor_discovery(
                'uptime',
                f"{self.device_info['name']} Uptime",
                's',
                'mdi:clock-outline',
                state_class='total_increasing'
            )
        )
        
        # LED light
        discoveries.append(self.create_light_discovery())
        
        # Publish all
        success = True
        for topic, payload in discoveries:
            print(f"[HA] Publishing discovery: {topic}")
            if not mqtt_client.publish_json(topic, payload, retain=True):
                success = False
                print(f"[HA] Failed to publish {topic}")
        
        if success:
            print(f"[HA] Published {len(discoveries)} discovery messages")
        
        return success
    
    def remove_all_discoveries(self, mqtt_client):
        """Remove all discovery messages (publish empty payload).
        
        Args:
            mqtt_client: MQTT client instance
        """
        device_id = self.device_info['device_id']
        
        topics = [
            f"{self.discovery_prefix}/sensor/{device_id}_temperature/config",
            f"{self.discovery_prefix}/sensor/{device_id}_humidity/config",
            f"{self.discovery_prefix}/sensor/{device_id}_rssi/config",
            f"{self.discovery_prefix}/sensor/{device_id}_uptime/config",
            f"{self.discovery_prefix}/light/{device_id}_led/config"
        ]
        
        for topic in topics:
            mqtt_client.publish(topic, '', retain=True)
        
        print("[HA] Removed all discovery messages")

def create_ha_discovery(config):
    """Create HA discovery instance from configuration."""
    device_info = {
        'device_id': config.get('device', {}).get('name', 'esp32').replace('-', '_').lower(),
        'name': config.get('device', {}).get('name', 'ESP32 SHTC3'),
        'model': 'ESP32-SHTC3',
        'manufacturer': 'Custom',
        'sw_version': config.get('device', {}).get('firmware_version', '1.0.0')
    }
    
    base_topic = config.get('mqtt', {}).get('base_topic', 'home/esp32')
    
    return HADiscovery(base_topic, device_info)
