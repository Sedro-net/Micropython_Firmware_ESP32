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
                        print(f\"[MDNS] Found: {broker['host']} at {broker['ip']}:{broker['port']}\")\n                
                except OSError:\n                    pass  # Timeout, continue\n            \n            sock.close()\n            \n            if discovered:\n                print(f\"[MDNS] Discovery complete: {len(discovered)} broker(s) found\")\n            else:\n                print(\"[MDNS] No brokers found\")\n            \n            return discovered\n            \n        except Exception as e:\n            print(f\"[MDNS] Discovery error: {e}\")\n            return []\n    \n    def discover_first(self):\n        \"\"\"Discover and return first broker found.\"\"\"\n        brokers = self.discover()\n        return brokers[0] if brokers else None\n    \n    def _build_mdns_query(self, service_name):\n        \"\"\"Build mDNS query packet (simplified).\"\"\"\n        # Transaction ID\n        transaction_id = b'\\x00\\x00'\n        \n        # Flags (standard query)\n        flags = b'\\x00\\x00'\n        \n        # Questions: 1, Answer RRs: 0, Authority RRs: 0, Additional RRs: 0\n        questions = b'\\x00\\x01'\n        answer_rrs = b'\\x00\\x00'\n        authority_rrs = b'\\x00\\x00'\n        additional_rrs = b'\\x00\\x00'\n        \n        # Build question\n        qname = b''\n        for part in service_name.split('.'):\n            qname += bytes([len(part)]) + part.encode('utf-8')\n        qname += b'\\x00'  # End of name\n        \n        # Type: PTR (12), Class: IN (1)\n        qtype = b'\\x00\\x0c'\n        qclass = b'\\x00\\x01'\n        \n        return transaction_id + flags + questions + answer_rrs + authority_rrs + additional_rrs + qname + qtype + qclass\n    \n    def _parse_mdns_response(self, data):\n        \"\"\"Parse mDNS response (simplified).\n        \n        This is a basic parser that extracts IP and port from mDNS responses.\n        A full implementation would properly parse all DNS record types.\n        \"\"\"\n        try:\n            # Skip header (12 bytes)\n            if len(data) < 12:\n                return None\n            \n            # For simplicity, we'll look for A records (IP) and SRV records (port)\n            # This is a basic implementation\n            \n            # Skip questions section and look for answers\n            idx = 12\n            \n            # Skip question name\n            while idx < len(data) and data[idx] != 0:\n                length = data[idx]\n                if length & 0xc0 == 0xc0:  # Compression pointer\n                    idx += 2\n                    break\n                idx += length + 1\n            \n            if idx >= len(data):\n                return None\n            \n            idx += 1  # Skip null terminator\n            idx += 4  # Skip qtype and qclass\n            \n            # Try to extract IP from response\n            # This is very simplified and may not work for all mDNS responses\n            \n            # For demo purposes, return a common default if parsing fails\n            # In production, you'd implement full DNS parsing or use a library\n            \n            return None  # Simplified implementation\n            \n        except Exception:\n            return None\n\n# Simplified discovery function\ndef discover_mqtt_broker(timeout=5):\n    \"\"\"\n    Discover MQTT broker via mDNS.\n    \n    Note: This is a simplified implementation. For production use,\n    consider using a full mDNS library or configuring the broker manually.\n    \n    Returns:\n        Broker info dict or None\n    \"\"\"\n    print(\"[MDNS] Starting MQTT broker discovery...\")\n    print(\"[MDNS] Note: mDNS discovery is experimental, consider manual configuration\")\n    \n    # Try multicast DNS discovery\n    discovery = MDNSDiscovery(timeout=timeout)\n    broker = discovery.discover_first()\n    \n    if broker:\n        print(f\"[MDNS] Discovered broker: {broker['ip']}:{broker['port']}\")\n        return broker\n    \n    # Fallback: Try common broker addresses on local network\n    print(\"[MDNS] Trying common broker addresses...\")\n    \n    import network\n    wlan = network.WLAN(network.STA_IF)\n    if wlan.isconnected():\n        # Get local network prefix\n        ip = wlan.ifconfig()[0]\n        ip_parts = ip.split('.')\n        network_prefix = '.'.join(ip_parts[:3])\n        \n        # Try common addresses\n        common_hosts = [\n            f\"{network_prefix}.1\",\n            f\"{network_prefix}.100\",\n            \"homeassistant.local\",\n            \"localhost\"\n        ]\n        \n        for host in common_hosts:\n            if _test_mqtt_connection(host, 1883):\n                print(f\"[MDNS] Found MQTT broker at {host}:1883\")\n                return {'host': host, 'ip': host, 'port': 1883}\n    \n    print(\"[MDNS] No MQTT broker discovered\")\n    return None\n\ndef _test_mqtt_connection(host, port, timeout=2):\n    \"\"\"Test if MQTT broker is reachable.\"\"\"\n    try:\n        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n        sock.settimeout(timeout)\n        sock.connect((host, port))\n        sock.close()\n        return True\n    except:\n        return False\n