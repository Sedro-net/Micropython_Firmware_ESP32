# captive_portal.py - AP mode + HTTP server with responsive UI

import network
import socket
import time
import ujson as json
from util import Timer

class CaptivePortal:
    """Captive portal for Wi-Fi and MQTT configuration."""
    
    def __init__(self, ssid, password="configure123", port=80):
        """
        Initialize captive portal.
        
        Args:
            ssid: AP SSID
            password: AP password
            port: HTTP server port
        """
        self.ssid = ssid
        self.password = password
        self.port = port
        self.ap = network.WLAN(network.AP_IF)
        self.server_socket = None
        self.running = False
        self.config_received = False
        self.received_config = {}
    
    def start(self, timeout=300):
        """
        Start captive portal.
        
        Args:
            timeout: Timeout in seconds (0 = no timeout)
            
        Returns:
            Received configuration dict or None if timeout
        """
        print(f"[PORTAL] Starting captive portal...")
        print(f"[PORTAL] SSID: {self.ssid}")
        print(f"[PORTAL] Password: {self.password}")
        
        # Start AP
        self.ap.active(True)
        self.ap.config(essid=self.ssid, password=self.password, authmode=3)
        
        # Configure IP
        self.ap.ifconfig(('192.168.4.1', '255.255.255.0', '192.168.4.1', '192.168.4.1'))
        
        print(f"[PORTAL] AP started: {self.ap.ifconfig()[0]}")
        print(f"[PORTAL] Connect to '{self.ssid}' and visit http://192.168.4.1")
        
        # Start HTTP server
        self._start_server()
        
        # Run until configured or timeout
        start_time = Timer()
        self.running = True
        
        while self.running:
            if timeout > 0 and start_time.elapsed_s() > timeout:
                print(f"[PORTAL] Timeout after {timeout}s")
                break
            
            if self.config_received:
                print("[PORTAL] Configuration received")
                break
            
            try:
                self._handle_client()
            except Exception as e:
                print(f"[PORTAL] Error: {e}")
            
            time.sleep(0.1)
        
        self.stop()
        
        return self.received_config if self.config_received else None
    
    def _start_server(self):
        """Start HTTP server."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', self.port))
        self.server_socket.listen(1)
        self.server_socket.settimeout(1.0)  # Non-blocking with timeout
        print(f"[PORTAL] HTTP server listening on port {self.port}")
    
    def _handle_client(self):
        """Handle HTTP client request."""
        try:
            client, addr = self.server_socket.accept()
            client.settimeout(3.0)
            
            request = client.recv(2048).decode('utf-8')
            
            # Parse request
            lines = request.split('\\r\\n')
            if not lines:
                client.close()
                return
            
            request_line = lines[0]
            parts = request_line.split(' ')
            
            if len(parts) < 2:
                client.close()
                return
            
            method = parts[0]
            path = parts[1]
            
            # Handle different endpoints
            if method == 'GET':
                if path == '/' or path.startswith('/index'):
                    print("[PORTAL] Send configuration page")
                    self._send_config_page(client)
                elif path == '/scan':
                    self._send_scan_results(client)
                elif path == '/status':
                    self._send_status(client)
                else:
                    # Redirect all other paths to root (captive portal behavior)
                    self._send_redirect(client, '/')
            elif method == 'POST':
                if path == '/configure':
                    self._handle_configure(client, request)
                else:
                    self._send_error(client, 404)
            else:
                self._send_error(client, 405)
            
            client.close()
            
        except OSError as e:
            if e.args[0] != 11 and e.args[0] != 110:  # EAGAIN and ETIMEDOUT
                pass  # Ignore timeout errors
    
    def _send_config_page(self, client):
        """Send configuration page."""
        # Scan for networks
        from wifi_manager import WiFiManager
        wifi = WiFiManager()
        networks = wifi.scan()
        
        # Generate network options
        network_options = ''
        seen_ssids = set()
        for net in networks:
            if net['ssid'] not in seen_ssids and net['ssid']:
                seen_ssids.add(net['ssid'])
                network_options += f'<option value=\"{net["ssid"]}\">{net["ssid"]} (RSSI: {net["rssi"]})</option>\n'
                print(f'[PORTAL] added following ssid to options: {net['ssid']}')
        
        html = self._get_html_template(network_options)
        
        response = f"""HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Connection: close

{html}"""
        
        # Stream response in chunks to save memory
        print('[PORTAL] Send response')
        client.sendall(response.encode('utf-8'))
    
    def _send_scan_results(self, client):
        """Send Wi-Fi scan results as JSON."""
        from wifi_manager import WiFiManager
        wifi = WiFiManager()
        networks = wifi.scan()
        
        response = f"""HTTP/1.1 200 OK
Content-Type: application/json
Connection: close

{json.dumps(networks)}"""
        
        client.sendall(response.encode('utf-8'))
    
    def _send_status(self, client):
        """Send status as JSON."""
        import config
        
        status = {
            'device_id': config.DEVICE_ID,
            'device_name': config.DEVICE_NAME,
            'firmware_version': config.FIRMWARE_VERSION,
            'ap_ip': self.ap.ifconfig()[0]
        }
        
        response = f"""HTTP/1.1 200 OK
Content-Type: application/json
Connection: close

{json.dumps(status)}"""
        
        client.sendall(response.encode('utf-8'))
    
    def _handle_configure(self, client, request):
        """Handle configuration POST request."""
        try:
            # Extract body from request
            body_start = request.find('\\r\\n\\r\\n')
            if body_start == -1:
                self._send_error(client, 400)
                return
            
            body = request[body_start + 4:]
            
            # Parse form data
            config_data = self._parse_form_data(body)
            
            # Validate required fields
            if 'wifi_ssid_1' not in config_data or not config_data['wifi_ssid_1']:
                self._send_error(client, 400, "Wi-Fi SSID is required")
                return
            
            # Build configuration
            self.received_config = {
                'wifi': {
                    'profiles': []
                },
                'mqtt': {},
                'device': {}
            }
            
            # Wi-Fi profiles
            if config_data.get('wifi_ssid_1'):
                self.received_config['wifi']['profiles'].append({
                    'ssid': config_data['wifi_ssid_1'],
                    'password': config_data.get('wifi_password_1', ''),
                    'priority': 1
                })
            
            if config_data.get('wifi_ssid_2'):
                self.received_config['wifi']['profiles'].append({
                    'ssid': config_data['wifi_ssid_2'],
                    'password': config_data.get('wifi_password_2', ''),
                    'priority': 2
                })
            
            # MQTT config
            if config_data.get('mqtt_broker'):
                self.received_config['mqtt'] = {
                    'broker': config_data.get('mqtt_broker', ''),
                    'port': int(config_data.get('mqtt_port', 1883)),
                    'username': config_data.get('mqtt_username', ''),
                    'password': config_data.get('mqtt_password', '')
                }
            
            # Device config
            if config_data.get('device_location'):
                self.received_config['device'] = {
                    'location': config_data.get('device_location', 'living_room')
                }
            
            self.config_received = True
            
            # Send success page
            success_html = """<!DOCTYPE html>
<html><head><meta charset=\"UTF-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>Configuration Saved</title>
<style>body{font-family:Arial,sans-serif;background:#0d1117;color:#c9d1d9;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}
.card{background:#161b22;border-radius:12px;padding:40px;text-align:center;box-shadow:0 8px 24px rgba(0,0,0,0.4);max-width:400px}
h1{color:#58a6ff;margin-bottom:20px}.icon{font-size:64px;margin-bottom:20px}p{font-size:16px;line-height:1.6;margin-bottom:20px}
</style></head><body>
<div class=\"card\"><div class=\"icon\">✓</div><h1>Configuration Saved</h1>
<p>Your device will now restart and connect to the configured Wi-Fi network.</p>
<p>You can close this page.</p></div></body></html>"""
            
            response = f"""HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Connection: close

{success_html}"""
            
            client.sendall(response.encode('utf-8'))
            
        except Exception as e:
            print(f"[PORTAL] Configure error: {e}")
            self._send_error(client, 500, str(e))
    
    def _parse_form_data(self, body):
        """Parse URL-encoded form data."""
        data = {}
        pairs = body.split('&')
        for pair in pairs:
            if '=' in pair:
                key, value = pair.split('=', 1)
                # URL decode
                value = value.replace('+', ' ')
                value = self._url_decode(value)
                data[key] = value
        return data
    
    def _url_decode(self, s):
        """Simple URL decoder."""
        result = ''
        i = 0
        while i < len(s):
            if s[i] == '%' and i + 2 < len(s):
                try:
                    result += chr(int(s[i+1:i+3], 16))
                    i += 3
                except:
                    result += s[i]
                    i += 1
            else:
                result += s[i]
                i += 1
        return result
    
    def _send_redirect(self, client, location):
        """Send HTTP redirect."""
        response = f"""HTTP/1.1 302 Found
Location: {location}
Connection: close

"""
        client.sendall(response.encode('utf-8'))
    
    def _send_error(self, client, code, message=""):
        """Send HTTP error."""
        messages = {
            400: "Bad Request",
            404: "Not Found",
            405: "Method Not Allowed",
            500: "Internal Server Error"
        }
        msg = message or messages.get(code, "Error")
        
        response = f"""HTTP/1.1 {code} {messages.get(code, 'Error')}
Content-Type: text/plain
Connection: close

{msg}"""
        
        client.sendall(response.encode('utf-8'))
    
    def _get_html_template(self, network_options):
        """Get HTML template with inline CSS."""
        import config
        
        return f"""<!DOCTYPE html>
<html><head><meta charset=\"UTF-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>{config.DEVICE_NAME} Configuration</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;padding:20px;color:#c9d1d9}}
.container{{max-width:800px;margin:0 auto}}
.header{{background:#161b22;border-radius:12px;padding:30px;margin-bottom:20px;text-align:center;box-shadow:0 8px 24px rgba(0,0,0,0.4)}}
.header h1{{color:#58a6ff;font-size:28px;margin-bottom:10px}}
.header p{{color:#8b949e;font-size:14px}}
.card{{background:#161b22;border-radius:12px;padding:25px;margin-bottom:20px;box-shadow:0 8px 24px rgba(0,0,0,0.4)}}
.card h2{{color:#58a6ff;font-size:20px;margin-bottom:20px;padding-bottom:10px;border-bottom:2px solid #21262d}}
.form-group{{margin-bottom:20px}}
.form-group label{{display:block;margin-bottom:8px;color:#c9d1d9;font-weight:500;font-size:14px}}
.form-group input,.form-group select{{width:100%;padding:12px;background:#0d1117;border:1px solid #30363d;border-radius:6px;color:#c9d1d9;font-size:14px}}
.form-group input:focus,.form-group select:focus{{outline:none;border-color:#58a6ff}}
.form-group small{{display:block;margin-top:5px;color:#8b949e;font-size:12px}}
.profile-group{{background:#0d1117;padding:20px;border-radius:8px;margin-bottom:15px}}
.profile-title{{color:#58a6ff;font-size:16px;margin-bottom:15px;font-weight:600}}
.btn{{background:#238636;color:#fff;padding:14px 32px;border:none;border-radius:6px;font-size:16px;font-weight:600;cursor:pointer;width:100%;transition:background 0.2s}}
.btn:hover{{background:#2ea043}}
.btn:active{{background:#2c974b}}
.scan-btn{{background:#1f6feb;margin-bottom:20px}}
.scan-btn:hover{{background:#388bfd}}
.device-info{{background:#0d1117;padding:15px;border-radius:6px;margin-bottom:15px}}
.device-info div{{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #21262d}}
.device-info div:last-child{{border-bottom:none}}
.device-info .label{{color:#8b949e;font-size:13px}}
.device-info .value{{color:#58a6ff;font-size:13px;font-weight:600}}
.note{{background:#1f6feb1a;border-left:3px solid #1f6feb;padding:12px;border-radius:4px;margin-top:20px;font-size:13px;line-height:1.6}}
@media(max-width:600px){{body{{padding:10px}}.card{{padding:20px}}.header{{padding:20px}}}}
</style>
</head><body>
<div class=\"container\">
<div class=\"header\">
<h1>📡 {config.DEVICE_NAME}</h1>
<p>ESP32 SHTC3 Sensor Configuration Portal</p>
</div>

<div class=\"card\">
<h2>📊 Device Information</h2>
<div class=\"device-info\">
<div><span class=\"label\">Device ID:</span><span class=\"value\">{config.DEVICE_ID}</span></div>
<div><span class=\"label\">Firmware Version:</span><span class=\"value\">{config.FIRMWARE_VERSION}</span></div>
<div><span class=\"label\">AP IP Address:</span><span class=\"value\">192.168.4.1</span></div>
</div>
</div>

<form method=\"POST\" action=\"/configure\">
<div class=\"card\">
<h2>📶 Wi-Fi Configuration</h2>
<p style=\"color:#8b949e;margin-bottom:20px;font-size:14px\">Configure up to 2 Wi-Fi networks. The device will try them in priority order.</p>

<div class=\"profile-group\">
<div class=\"profile-title\">Primary Wi-Fi (Priority 1)</div>
<div class=\"form-group\">
<label for=\"wifi_ssid_1\">Network Name (SSID) *</label>
<select id=\"wifi_ssid_1\" name=\"wifi_ssid_1\" required>
<option value=\"\">-- Select or type below --</option>
{network_options}</select>
<small>Or type manually if not listed</small>
</div>
<div class=\"form-group\">
<label for=\"wifi_password_1\">Password *</label>
<input type=\"password\" id=\"wifi_password_1\" name=\"wifi_password_1\" required>
</div>
</div>

<div class=\"profile-group\">
<div class=\"profile-title\">Backup Wi-Fi (Priority 2) - Optional</div>
<div class=\"form-group\">
<label for=\"wifi_ssid_2\">Network Name (SSID)</label>
<select id=\"wifi_ssid_2\" name=\"wifi_ssid_2\">
<option value=\"\">-- Select or type below --</option>
{network_options}</select>
</div>
<div class=\"form-group\">
<label for=\"wifi_password_2\">Password</label>
<input type=\"password\" id=\"wifi_password_2\" name=\"wifi_password_2\">
</div>
</div>
</div>

<div class=\"card\">
<h2>🔌 MQTT Configuration</h2>
<p style=\"color:#8b949e;margin-bottom:20px;font-size:14px\">Configure MQTT broker. Leave empty to use mDNS auto-discovery.</p>

<div class=\"form-group\">
<label for=\"mqtt_broker\">MQTT Broker</label>
<input type=\"text\" id=\"mqtt_broker\" name=\"mqtt_broker\" placeholder=\"192.168.1.100 or mqtt.example.com\">
<small>Leave empty for auto-discovery via mDNS</small>
</div>
<div class=\"form-group\">
<label for=\"mqtt_port\">MQTT Port</label>
<input type=\"number\" id=\"mqtt_port\" name=\"mqtt_port\" value=\"1883\">
</div>
<div class=\"form-group\">
<label for=\"mqtt_username\">MQTT Username</label>
<input type=\"text\" id=\"mqtt_username\" name=\"mqtt_username\" placeholder=\"Optional\">
</div>
<div class=\"form-group\">
<label for=\"mqtt_password\">MQTT Password</label>
<input type=\"password\" id=\"mqtt_password\" name=\"mqtt_password\" placeholder=\"Optional\">
</div>
</div>

<div class=\"card\">
<h2>⚙️ Device Settings</h2>
<div class=\"form-group\">
<label for=\"device_location\">Device Location</label>
<input type=\"text\" id=\"device_location\" name=\"device_location\" value=\"living_room\" placeholder=\"living_room\">
<small>Used in MQTT topic: home/&lt;location&gt;/&lt;device_id&gt;</small>
</div>
</div>

<div class=\"card\">
<button type=\"submit\" class=\"btn\">💾 Save Configuration</button>
<div class=\"note\">
<strong>Note:</strong> After saving, the device will restart and attempt to connect to the configured Wi-Fi network. 
If connection fails, it will return to AP mode after 3 failed boot attempts.
</div>
</div>
</form>

</div>

<script>
// Allow typing custom SSID
document.getElementById('wifi_ssid_1').addEventListener('change', function() {{
    if (this.value === '') {{
        let custom = prompt('Enter custom SSID:');
        if (custom) {{
            let opt = document.createElement('option');
            opt.value = custom;
            opt.text = custom + ' (custom)';
            opt.selected = true;
            this.add(opt);
        }}
    }}
}});
document.getElementById('wifi_ssid_2').addEventListener('change', function() {{
    if (this.value === '') {{
        let custom = prompt('Enter custom SSID:');
        if (custom) {{
            let opt = document.createElement('option');
            opt.value = custom;
            opt.text = custom + ' (custom)';
            opt.selected = true;
            this.add(opt);
        }}
    }}
}});
</script>

</body></html>"""
    
    def stop(self):
        """Stop captive portal."""
        self.running = False
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        if self.ap.active():
            self.ap.active(False)
        
        print("[PORTAL] Stopped")

def start_captive_portal(timeout=300):
    """Start captive portal and return configuration."""
    import config
    portal = CaptivePortal(config.AP_SSID, config.AP_PASSWORD)
    return portal.start(timeout)
