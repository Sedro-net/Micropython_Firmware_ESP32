# mqtt_client.py - MQTT wrapper with LWT and reconnection logic

from umqtt.simple import MQTTClient
import ujson as json
import time
from util import ExponentialBackoff

class MQTTClientWrapper:
    """MQTT client wrapper with automatic reconnection and LWT."""
    
    def __init__(self, config):
        """
        Initialize MQTT client.
        
        Args:
            config: Configuration dict with broker, port, username, password, etc.
        """
        self.config = config
        self.client = None
        self.connected = False
        self.backoff = ExponentialBackoff(initial_delay=5, max_delay=60)
        self.message_callback = None
        self.subscriptions = []
        
        # Extract config
        self.broker = config.get('broker', '')
        self.port = config.get('port', 1883)
        self.username = config.get('username', '')
        self.password = config.get('password', '')
        self.client_id = config.get('client_id', 'esp32')
        self.base_topic = config.get('base_topic', 'home/esp32')
        self.lwt_topic = f"{self.base_topic}/status"
    
    def connect(self):
        """Connect to MQTT broker."""
        if not self.broker:
            print("[MQTT] No broker configured")
            return False
        
        try:
            print(f"[MQTT] Connecting to {self.broker}:{self.port}...")
            
            # Create client
            self.client = MQTTClient(
                client_id=self.client_id,
                server=self.broker,
                port=self.port,
                user=self.username if self.username else None,
                password=self.password if self.password else None,
                keepalive=60
            )
            
            # Set LWT
            self.client.set_last_will(self.lwt_topic, b'offline', retain=True)
            
            # Set message callback
            self.client.set_callback(self._on_message)
            
            # Connect
            self.client.connect()
            
            # Publish online status
            self.publish(self.lwt_topic, 'online', retain=True)
            
            self.connected = True
            self.backoff.reset()
            
            print(f"[MQTT] Connected to {self.broker}")
            
            # Resubscribe to topics
            self._resubscribe()
            
            return True
            
        except Exception as e:
            print(f"[MQTT] Connection failed: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.client and self.connected:
            try:
                # Publish offline status
                self.publish(self.lwt_topic, 'offline', retain=True)
                self.client.disconnect()
                print("[MQTT] Disconnected")
            except Exception as e:
                print(f"[MQTT] Disconnect error: {e}")
        
        self.connected = False
        self.client = None
    
    def reconnect(self):
        """Reconnect to MQTT broker with exponential backoff."""
        if self.connected:
            return True
        
        delay = self.backoff.next()
        print(f"[MQTT] Reconnecting in {delay:.1f}s...")
        time.sleep(delay)
        
        return self.connect()
    
    def publish(self, topic, payload, retain=False, qos=0):
        """Publish message to topic."""
        if not self.connected or not self.client:
            print(f"[MQTT] Not connected, cannot publish to {topic}")
            return False
        
        try:
            # Convert payload to bytes
            if isinstance(payload, dict):
                payload = json.dumps(payload)
            if isinstance(payload, str):
                payload = payload.encode('utf-8')
            
            self.client.publish(topic, payload, retain=retain, qos=qos)
            return True
            
        except Exception as e:
            print(f"[MQTT] Publish error: {e}")
            self.connected = False
            return False
    
    def subscribe(self, topic, callback=None):
        """Subscribe to topic."""
        if not self.connected or not self.client:
            print(f"[MQTT] Not connected, queueing subscription to {topic}")
            # Queue subscription for when we reconnect
            if topic not in [s[0] for s in self.subscriptions]:
                self.subscriptions.append((topic, callback))
            return False
        
        try:
            self.client.subscribe(topic)
            print(f"[MQTT] Subscribed to {topic}")
            
            # Store subscription
            if topic not in [s[0] for s in self.subscriptions]:
                self.subscriptions.append((topic, callback))
            
            return True
            
        except Exception as e:
            print(f"[MQTT] Subscribe error: {e}")
            return False
    
    def _resubscribe(self):
        """Resubscribe to all topics after reconnection."""
        if not self.subscriptions:
            return
        
        print(f"[MQTT] Resubscribing to {len(self.subscriptions)} topics...")
        
        for topic, callback in self.subscriptions:
            try:
                self.client.subscribe(topic)
                print(f"[MQTT] Resubscribed to {topic}")
            except Exception as e:
                print(f"[MQTT] Resubscribe error for {topic}: {e}")
    
    def _on_message(self, topic, msg):
        """Internal message callback."""
        try:
            topic_str = topic.decode('utf-8')
            msg_str = msg.decode('utf-8')
            
            print(f"[MQTT] Received on {topic_str}: {msg_str[:100]}...")
            
            # Find matching subscription callback
            for sub_topic, callback in self.subscriptions:
                if self._topic_matches(topic_str, sub_topic):
                    if callback:
                        try:
                            callback(topic_str, msg_str)
                        except Exception as e:
                            print(f"[MQTT] Callback error: {e}")
            
            # Call global message callback if set
            if self.message_callback:
                try:
                    self.message_callback(topic_str, msg_str)
                except Exception as e:
                    print(f"[MQTT] Global callback error: {e}")
                    
        except Exception as e:
            print(f"[MQTT] Message processing error: {e}")
    
    def _topic_matches(self, topic, pattern):
        """Check if topic matches pattern (supports + and # wildcards)."""
        topic_parts = topic.split('/')
        pattern_parts = pattern.split('/')
        
        if len(pattern_parts) > len(topic_parts):
            # Pattern has more parts than topic (unless last is #)
            if pattern_parts[-1] != '#':
                return False
        
        for i, pattern_part in enumerate(pattern_parts):
            if pattern_part == '#':
                # Multi-level wildcard matches rest
                return True
            elif pattern_part == '+':
                # Single-level wildcard
                if i >= len(topic_parts):
                    return False
                continue
            elif i >= len(topic_parts) or topic_parts[i] != pattern_part:
                return False
        
        # Check if all topic parts matched
        return len(topic_parts) == len(pattern_parts)
    
    def set_message_callback(self, callback):
        """Set global message callback."""
        self.message_callback = callback
    
    def check_msg(self):
        """Check for new messages (non-blocking)."""
        if not self.connected or not self.client:
            return
        
        try:
            self.client.check_msg()
        except Exception as e:
            print(f"[MQTT] Check message error: {e}")
            self.connected = False
    
    def wait_msg(self):
        """Wait for message (blocking)."""
        if not self.connected or not self.client:
            return
        
        try:
            self.client.wait_msg()
        except Exception as e:
            print(f"[MQTT] Wait message error: {e}")
            self.connected = False
    
    def is_connected(self):
        """Check if connected."""
        return self.connected
    
    def publish_json(self, topic, data, retain=False):
        """Publish JSON data."""
        return self.publish(topic, json.dumps(data), retain=retain)
    
    def publish_state(self, state_data):
        """Publish state to state topic."""
        state_topic = f"{self.base_topic}/state"
        return self.publish_json(state_topic, state_data)

# Convenience functions

def create_mqtt_client(config):
    """Create MQTT client from configuration."""
    return MQTTClientWrapper(config)
