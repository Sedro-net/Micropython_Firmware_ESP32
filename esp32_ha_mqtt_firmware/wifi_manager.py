# wifi_manager.py - 2-profile Wi-Fi manager with rotation logic

import network
import time
from util import Timer

class WiFiManager:
    """Manages Wi-Fi connections with multiple profile support."""
    
    def __init__(self, profiles=None, timeout=10):
        """
        Initialize WiFi manager.
        
        Args:
            profiles: List of profile dicts with 'ssid', 'password', 'priority'
            timeout: Timeout in seconds per profile connection attempt
        """
        self.profiles = profiles or []
        self.timeout = timeout
        self.wlan = network.WLAN(network.STA_IF)
        self.connected_profile = None
        self.last_connect_attempt = 0
        self.connect_retry_delay = 5  # seconds
        
        # Sort profiles by priority (lower number = higher priority)
        self.profiles.sort(key=lambda p: p.get('priority', 999))
        
        # Limit to 2 profiles
        if len(self.profiles) > 2:
            print("[WIFI] Warning: More than 2 profiles, using top 2 by priority")
            self.profiles = self.profiles[:2]
    
    def add_profile(self, ssid, password, priority=999):
        """Add a Wi-Fi profile."""
        # Check if profile already exists
        for i, p in enumerate(self.profiles):
            if p['ssid'] == ssid:
                # Update existing profile
                self.profiles[i] = {'ssid': ssid, 'password': password, 'priority': priority}
                self.profiles.sort(key=lambda p: p.get('priority', 999))
                return True
        
        # Add new profile
        if len(self.profiles) < 2:
            self.profiles.append({'ssid': ssid, 'password': password, 'priority': priority})
            self.profiles.sort(key=lambda p: p.get('priority', 999))
            return True
        else:
            print("[WIFI] Max profiles (2) reached, cannot add more")
            return False
    
    def remove_profile(self, ssid):
        """Remove a Wi-Fi profile."""
        self.profiles = [p for p in self.profiles if p['ssid'] != ssid]
        if self.connected_profile and self.connected_profile['ssid'] == ssid:
            self.connected_profile = None
    
    def get_profiles(self):
        """Get list of profiles (without passwords)."""
        return [{'ssid': p['ssid'], 'priority': p.get('priority', 999)} for p in self.profiles]
    
    def connect(self, retry=True):
        """
        Connect to Wi-Fi using available profiles.
        
        Args:
            retry: If True, retry all profiles in rotation
            
        Returns:
            True if connected, False otherwise
        """
        if not self.profiles:
            print("[WIFI] No profiles configured")
            return False
        
        # Activate station interface
        if not self.wlan.active():
            self.wlan.active(True)
        
        # Check if already connected
        if self.is_connected():
            return True
        
        attempts = 0
        max_attempts = 3 if retry else 1
        
        while attempts < max_attempts:
            # Try each profile in order
            for profile in self.profiles:
                print(f"[WIFI] Attempting to connect to '{profile['ssid']}' (attempt {attempts + 1}/{max_attempts})...")
                
                if self._try_connect_profile(profile):
                    self.connected_profile = profile
                    self._print_connection_info()
                    return True
                
                print(f"[WIFI] Failed to connect to '{profile['ssid']}'")
            
            attempts += 1
            if attempts < max_attempts:
                print(f"[WIFI] Retrying all profiles in {self.connect_retry_delay}s...")
                time.sleep(self.connect_retry_delay)
        
        print("[WIFI] Failed to connect to any profile")
        return False
    
    def _try_connect_profile(self, profile):
        """Try to connect to a specific profile."""
        try:
            # Disconnect if connected
            if self.wlan.isconnected():
                self.wlan.disconnect()
                time.sleep(0.5)
            
            # Start connection
            self.wlan.connect(profile['ssid'], profile['password'])
            
            # Wait for connection with timeout
            timer = Timer()
            while not self.wlan.isconnected() and timer.elapsed_s() < self.timeout:
                time.sleep(0.1)
            
            return self.wlan.isconnected()
            
        except Exception as e:
            print(f"[WIFI] Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Wi-Fi."""
        if self.wlan.isconnected():
            self.wlan.disconnect()
            print("[WIFI] Disconnected")
        self.connected_profile = None
    
    def is_connected(self):
        """Check if connected to Wi-Fi."""
        return self.wlan.active() and self.wlan.isconnected()
    
    def get_connection_info(self):
        """Get current connection information."""
        if not self.is_connected():
            return None
        
        ifconfig = self.wlan.ifconfig()
        
        info = {
            'ssid': self.connected_profile['ssid'] if self.connected_profile else 'Unknown',
            'ip': ifconfig[0],
            'subnet': ifconfig[1],
            'gateway': ifconfig[2],
            'dns': ifconfig[3]
        }
        
        # Try to get RSSI if available
        try:
            info['rssi'] = self.wlan.status('rssi')
        except:
            info['rssi'] = None
        
        return info
    
    def _print_connection_info(self):
        """Print connection information."""
        info = self.get_connection_info()
        if info:
            print(f"[WIFI] Connected to '{info['ssid']}'")
            print(f"[WIFI] IP: {info['ip']}")
            print(f"[WIFI] Gateway: {info['gateway']}")
            if info['rssi'] is not None:
                print(f"[WIFI] RSSI: {info['rssi']} dBm")
    
    def scan(self):
        """Scan for available Wi-Fi networks."""
        print("[WIFI] Scanning for networks...")
        
        if not self.wlan.active():
            self.wlan.active(True)
        
        try:
            networks = self.wlan.scan()
            
            # Sort by signal strength
            networks = sorted(networks, key=lambda x: x[3], reverse=True)
            
            print(f"[WIFI] Found {len(networks)} networks:")
            
            result = []
            for ssid, bssid, channel, rssi, authmode, hidden in networks:
                ssid_str = ssid.decode('utf-8') if isinstance(ssid, bytes) else ssid
                auth_modes = {
                    0: 'Open',
                    1: 'WEP',
                    2: 'WPA-PSK',
                    3: 'WPA2-PSK',
                    4: 'WPA/WPA2-PSK'
                }
                auth_str = auth_modes.get(authmode, f'Unknown ({authmode})')
                
                print(f"  {ssid_str:32s} | Ch:{channel:2d} | RSSI:{rssi:3d} | {auth_str}")
                
                result.append({
                    'ssid': ssid_str,
                    'rssi': rssi,
                    'channel': channel,
                    'authmode': authmode,
                    'hidden': hidden
                })
            
            return result
            
        except Exception as e:
            print(f"[WIFI] Scan error: {e}")
            return []
    
    def get_status_text(self):
        """Get human-readable status text."""
        if not self.wlan.active():
            return "Inactive"
        
        if self.is_connected():
            return f"Connected to {self.connected_profile['ssid']}"
        
        status = self.wlan.status()
        status_map = {
            network.STAT_IDLE: "Idle",
            network.STAT_CONNECTING: "Connecting",
            network.STAT_WRONG_PASSWORD: "Wrong password",
            network.STAT_NO_AP_FOUND: "No AP found",
            network.STAT_CONNECT_FAIL: "Connection failed",
            1000: "Got IP",  # network.STAT_GOT_IP
        }
        
        return status_map.get(status, f"Unknown ({status})")
    
    def deinit(self):
        """Deinitialize Wi-Fi."""
        self.disconnect()
        self.wlan.active(False)
        print("[WIFI] Deinitialized")

# Convenience functions

def load_profiles_from_config():
    """Load Wi-Fi profiles from configuration."""
    from storage import load_config
    config = load_config()
    return config.get('wifi', {}).get('profiles', [])

def load_profiles_from_secrets():
    """Load Wi-Fi profiles from secrets file."""
    try:
        import secrets
        return secrets.WIFI_PROFILES
    except (ImportError, AttributeError):
        return []

def create_wifi_manager():
    """Create WiFi manager with profiles from config and secrets."""
    profiles = []
    
    # Try secrets file first
    secrets_profiles = load_profiles_from_secrets()
    if secrets_profiles:
        print(f"[WIFI] Loaded {len(secrets_profiles)} profiles from secrets")
        profiles = secrets_profiles
    
    # Then try config file
    if not profiles:
        config_profiles = load_profiles_from_config()
        if config_profiles:
            print(f"[WIFI] Loaded {len(config_profiles)} profiles from config")
            profiles = config_profiles
    
    return WiFiManager(profiles)
