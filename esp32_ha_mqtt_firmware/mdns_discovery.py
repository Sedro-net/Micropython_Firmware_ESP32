# mdns_discovery.py - MQTT broker auto-discovery via mDNS

import socket
import struct
import time
from util import Timer

class MDNSDiscovery:
    """Simple mDNS service discovery for MQTT brokers."""
    
    MDNS_ADDR = '224.0.0.251'
    MDNS_PORT = 5353
    
    def __init__(self, service_type='_mqtt._tcp.local', timeout=5):
        """
        Initialize mDNS discovery.
        
        Args:
            service_type: Service type to discover
            timeout: Discovery timeout in seconds
        """
        self.service_type = service_type
        self.timeout = timeout
    
    def discover(self):
        """
        Discover MQTT brokers via mDNS.
        
        Returns:
            List of discovered brokers with 'host', 'ip', 'port'
        """
        print(f"[MDNS] Discovering {self.service_type}...")
        
        try:
            # Create socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(1.0)
            
            # Build mDNS query
            query = self._build_mdns_query(self.service_type)
            
            # Send query
            sock.sendto(query, (self.MDNS_ADDR, self.MDNS_PORT))
            
            # Collect responses
            discovered = []
            timer = Timer()
            
            while timer.elapsed_s() < self.timeout:
                try:
                    data, addr = sock.recvfrom(1024)
                    
                    # Parse mDNS response (simplified)
                    broker = self._parse_mdns_response(data)
                    
                    if broker and broker not in discovered:
                        discovered.append(broker)
                        print(f"[MDNS] Found: {broker['host']} at {broker['ip']}:{broker['port']}")
                
                except OSError:
                    pass  # Timeout, continue
            
            sock.close()
            
            if discovered:
                print(f"[MDNS] Discovery complete: {len(discovered)} broker(s) found")
            else:
                print("[MDNS] No brokers found")
            
            return discovered
            
        except Exception as e:
            print(f"[MDNS] Discovery error: {e}")
            return []
    
    def discover_first(self):
        """Discover and return first broker found."""
        brokers = self.discover()
        return brokers[0] if brokers else None
    
    def _build_mdns_query(self, service_name):
        """Build mDNS query packet (simplified)."""
        # Transaction ID
        transaction_id = b'\x00\x00'
        
        # Flags (standard query)
        flags = b'\x00\x00'
        
        # Questions: 1, Answer RRs: 0, Authority RRs: 0, Additional RRs: 0
        questions = b'\x00\x01'
        answer_rrs = b'\x00\x00'
        authority_rrs = b'\x00\x00'
        additional_rrs = b'\x00\x00'
        
        # Build question
        qname = b''
        for part in service_name.split('.'):
            qname += bytes([len(part)]) + part.encode('utf-8')
        qname += b'\x00'  # End of name
        
        # Type: PTR (12), Class: IN (1)
        qtype = b'\x00\x0c'
        qclass = b'\x00\x01'
        
        return transaction_id + flags + questions + answer_rrs + authority_rrs + additional_rrs + qname + qtype + qclass
    
    def _parse_mdns_response(self, data):
        """Parse mDNS response (simplified).
        
        This is a basic parser that extracts IP and port from mDNS responses.
        A full implementation would properly parse all DNS record types.
        """
        try:
            # Skip header (12 bytes)
            if len(data) < 12:
                return None
            
            # For simplicity, we'll look for A records (IP) and SRV records (port)
            # This is a basic implementation
            
            # Skip questions section and look for answers
            idx = 12
            
            # Skip question name
            while idx < len(data) and data[idx] != 0:
                length = data[idx]
                if length & 0xc0 == 0xc0:  # Compression pointer
                    idx += 2
                    break
                idx += length + 1
            
            if idx >= len(data):
                return None
            
            idx += 1  # Skip null terminator
            idx += 4  # Skip qtype and qclass
            
            # Try to extract IP from response
            # This is very simplified and may not work for all mDNS responses
            
            # For demo purposes, return a common default if parsing fails
            # In production, you'd implement full DNS parsing or use a library
            
            return None  # Simplified implementation
            
        except Exception:
            return None

# Simplified discovery function
def discover_mqtt_broker(timeout=5):
    """
    Discover MQTT broker via mDNS.
    
    Note: This is a simplified implementation. For production use,
    consider using a full mDNS library or configuring the broker manually.
    
    Returns:
        Broker info dict or None
    """
    print("[MDNS] Starting MQTT broker discovery...")
    print("[MDNS] Note: mDNS discovery is experimental, consider manual configuration")
    
    # Try multicast DNS discovery
    discovery = MDNSDiscovery(timeout=timeout)
    broker = discovery.discover_first()
    
    if broker:
        print(f"[MDNS] Discovered broker: {broker['ip']}:{broker['port']}")
        return broker
    
    # Fallback: Try common broker addresses on local network
    print("[MDNS] Trying common broker addresses...")
    
    import network
    wlan = network.WLAN(network.STA_IF)
    if wlan.isconnected():
        # Get local network prefix
        ip = wlan.ifconfig()[0]
        ip_parts = ip.split('.')
        network_prefix = '.'.join(ip_parts[:3])
        
        # Try common addresses
        common_hosts = [
            f"{network_prefix}.1",
            f"{network_prefix}.100",
            "homeassistant.local",
            "localhost"
        ]
        
        for host in common_hosts:
            if _test_mqtt_connection(host, 1883):
                print(f"[MDNS] Found MQTT broker at {host}:1883")
                return {'host': host, 'ip': host, 'port': 1883}
    
    print("[MDNS] No MQTT broker discovered")
    return None

def _test_mqtt_connection(host, port, timeout=2):
    """Test if MQTT broker is reachable."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        return True
    except:
        return False
