# failsafe.py - Failsafe mode with error diagnostics

import os
import ujson as json
import time
import network
import socket
import sys
import io

class FailsafeMode:
    """Failsafe mode for recovery and diagnostics."""
    
    def __init__(self):
        self.ap = network.WLAN(network.AP_IF)
        self.server_socket = None
        self.logs = []
        self.error_info = None
    
    def load_failsafe_info(self):
        """Load failsafe flag information."""
        try:
            with open('failsafe.flag', 'r') as f:
                return json.load(f)
        except:
            return {'reason': 'unknown', 'timestamp': time.time()}
    
    def load_logs(self):
        """Load system logs."""
        try:
            with open('failsafe.log', 'r') as f:
                return f.read()
        except:
            return "No logs available"
    
    def start(self):
        """Start failsafe mode with diagnostic web interface."""
        print("\n" + "="*50)
        print("FAILSAFE MODE ACTIVATED")
        print("="*50)
        
        self.error_info = self.load_failsafe_info()
        
        print(f"Reason: {self.error_info.get('reason', 'unknown')}")
        print(f"Time: {self.error_info.get('timestamp', 0)}")
        
        # Start AP
        import config
        ap_ssid = f"{config.AP_SSID}-FAILSAFE"
        print(f"\nStarting failsafe AP: {ap_ssid}")
        
        self.ap.active(True)
        self.ap.config(essid=ap_ssid, password="failsafe123", authmode=3)
        self.ap.ifconfig(('192.168.4.1', '255.255.255.0', '192.168.4.1', '192.168.4.1'))
        
        print(f"AP IP: {self.ap.ifconfig()[0]}")
        print(f"Connect to '{ap_ssid}' (password: failsafe123)")
        print(f"Visit: http://192.168.4.1")
        print("\nFailsafe options:")
        print("  - View diagnostics")
        print("  - Clear configuration")
        print("  - Reset boot counter")
        print("  - Reboot device")
        print("="*50 + "\n")
        
        # Start web server
        self._start_server()
        
        # Run server
        while True:
            try:
                self._handle_client()
                time.sleep(0.1)
            except KeyboardInterrupt:
                print("\n[FAILSAFE] Interrupted")
                break
            except Exception as e:
                print(f"[FAILSAFE] Error: {e}")
    
    def _start_server(self):
        """Start HTTP server."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', 80))
        self.server_socket.listen(1)
        self.server_socket.settimeout(1.0)
    
    def _handle_client(self):
        """Handle HTTP client."""
        try:
            client, addr = self.server_socket.accept()
            client.settimeout(3.0)
            
            request = client.recv(2048).decode('utf-8')
            
            lines = request.split('\r\n')
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
            
            if method == 'GET':
                if path == '/' or path.startswith('/index'):
                    self._send_diagnostics_page(client)
                elif path == '/clear_config':
                    self._handle_clear_config(client)
                elif path == '/reset_boot':
                    self._handle_reset_boot(client)
                elif path == '/reboot':
                    self._handle_reboot(client)
                elif path == '/logs':
                    self._send_logs(client)
                else:
                    self._send_error(client, 404)
            else:
                self._send_error(client, 405)
            
            client.close()
            
        except OSError as e:
            if e.args[0] not in [11, 110]:  # Not EAGAIN or ETIMEDOUT
                pass
    
    def _send_diagnostics_page(self, client):
        """Send diagnostics page."""
        import config
        import gc
        
        # System info
        gc.collect()
        mem_free = gc.mem_free()
        mem_alloc = gc.mem_alloc()
        
        reset_cause = config.get_reset_cause()
        
        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Failsafe Mode - {config.DEVICE_NAME}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Arial,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px}}
.container{{max-width:800px;margin:0 auto}}
.header{{background:#58181c;border:2px solid #da3633;border-radius:12px;padding:30px;margin-bottom:20px;text-align:center}}
.header h1{{color:#ff7b72;font-size:28px;margin-bottom:10px}}
.header p{{color:#f0f6fc;font-size:14px}}
.card{{background:#161b22;border-radius:12px;padding:25px;margin-bottom:20px;border:1px solid #30363d}}
.card h2{{color:#58a6ff;font-size:20px;margin-bottom:20px;padding-bottom:10px;border-bottom:2px solid#21262d}}
.info-row{{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #21262d}}
.info-row:last-child{{border-bottom:none}}
.info-label{{color:#8b949e;font-size:14px}}
.info-value{{color:#c9d1d9;font-weight:600;font-size:14px}}
.btn{{background:#238636;color:#fff;padding:12px 24px;border:none;border-radius:6px;font-size:14px;font-weight:600;cursor:pointer;text-decoration:none;display:inline-block;margin:5px}}
.btn:hover{{background:#2ea043}}
.btn-danger{{background:#da3633}}
.btn-danger:hover{{background:#e5534b}}
.btn-warning{{background:#9e6a03}}
.btn-warning:hover{{background:#bb8009}}
.log-box{{background:#0d1117;padding:15px;border-radius:6px;font-family:monospace;font-size:12px;overflow-x:auto;max-height:300px;overflow-y:auto}}
.alert{{background:#1f6feb1a;border-left:3px solid #1f6feb;padding:12px;border-radius:4px;margin:15px 0;font-size:13px}}
.alert-error{{background:#da36331a;border-left-color:#da3633;color:#ff7b72}}
</style>
</head><body>
<div class="container">
<div class="header">
<h1>⚠️ FAILSAFE MODE</h1>
<p>Device Recovery & Diagnostics</p>
</div>

<div class="card">
<h2>❌ Error Information</h2>
<div class="alert alert-error">
<strong>Reason:</strong> {self.error_info.get('reason', 'Unknown')}<br>
<strong>Timestamp:</strong> {self.error_info.get('timestamp', 'Unknown')}
</div>
<p style="color:#8b949e;margin-top:15px">The device entered failsafe mode due to repeated boot failures or critical errors.</p>
</div>

<div class="card">
<h2>📊 System Information</h2>
<div class="info-row"><span class="info-label">Device ID:</span><span class="info-value">{config.DEVICE_ID}</span></div>
<div class="info-row"><span class="info-label">Firmware Version:</span><span class="info-value">{config.FIRMWARE_VERSION}</span></div>
<div class="info-row"><span class="info-label">Reset Cause:</span><span class="info-value">{reset_cause}</span></div>
<div class="info-row"><span class="info-label">Free Memory:</span><span class="info-value">{mem_free} bytes</span></div>
<div class="info-row"><span class="info-label">Used Memory:</span><span class="info-value">{mem_alloc} bytes</span></div>
</div>

<div class="card">
<h2>🔧 Recovery Actions</h2>
<p style="color:#8b949e;margin-bottom:20px">Choose a recovery action:</p>
<a href="/reset_boot" class="btn btn-warning">Reset Boot Counter</a>
<a href="/clear_config" class="btn btn-danger">Clear Configuration</a>
<a href="/reboot" class="btn">Reboot Device</a>
<a href="/logs" class="btn">View Logs</a>
</div>

<div class="card">
<h2>📝 Instructions</h2>
<div class="alert">
<strong>Reset Boot Counter:</strong> Clears the boot loop counter and removes failsafe flag.<br><br>
<strong>Clear Configuration:</strong> Removes all saved configuration and Wi-Fi credentials. Device will start in AP mode for reconfiguration.<br><br>
<strong>Reboot Device:</strong> Restarts the device. It may enter failsafe mode again if the issue persists.
</div>
</div>

</div>
</body></html>"""
        
        response = f"""HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Connection: close

{html}"""
        
        client.sendall(response.encode('utf-8'))
    
    def _send_logs(self, client):
        """Send logs page."""
        logs = self.load_logs()
        
        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>System Logs</title>
<style>
body{{font-family:Arial,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px}}
.container{{max-width:900px;margin:0 auto}}
h1{{color:#58a6ff;margin-bottom:20px}}
.log-box{{background:#161b22;padding:15px;border-radius:6px;font-family:monospace;font-size:12px;white-space:pre-wrap;word-wrap:break-word;border:1px solid #30363d}}
.btn{{background:#238636;color:#fff;padding:10px 20px;border:none;border-radius:6px;text-decoration:none;display:inline-block;margin-top:20px}}
</style>
</head><body>
<div class="container">
<h1>📋 System Logs</h1>
<div class="log-box">{logs}</div>
<a href="/" class="btn">← Back to Diagnostics</a>
</div>
</body></html>"""
        
        response = f"""HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Connection: close

{html}"""
        
        client.sendall(response.encode('utf-8'))
    
    def _handle_clear_config(self, client):
        """Handle clear configuration request."""
        try:
            # Remove config file
            try:
                os.remove('config.json')
            except:
                pass
            
            # Remove boot count
            try:
                os.remove('boot_count.json')
            except:
                pass
            
            # Remove failsafe flag
            try:
                os.remove('failsafe.flag')
            except:
                pass
            
            html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Configuration Cleared</title>
<style>body{font-family:Arial,sans-serif;background:#0d1117;color:#c9d1d9;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;text-align:center}
h1{color:#58a6ff;margin-bottom:20px}</style>
</head><body>
<div><h1>✓ Configuration Cleared</h1><p>Device will reboot in 3 seconds...</p></div>
<script>setTimeout(function(){window.location.href='/reboot'},3000)</script>
</body></html>"""
            
            response = f"""HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Connection: close

{html}"""
            
            client.sendall(response.encode('utf-8'))
            
        except Exception as e:
            self._send_error(client, 500, str(e))
    
    def _handle_reset_boot(self, client):
        """Handle reset boot counter request."""
        try:
            # Remove boot count
            try:
                os.remove('boot_count.json')
            except:
                pass
            
            # Remove failsafe flag
            try:
                os.remove('failsafe.flag')
            except:
                pass
            
            html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Boot Counter Reset</title>
<style>body{font-family:Arial,sans-serif;background:#0d1117;color:#c9d1d9;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;text-align:center}
h1{color:#58a6ff;margin-bottom:20px}</style>
</head><body>
<div><h1>✓ Boot Counter Reset</h1><p>Device will reboot in 3 seconds...</p></div>
<script>setTimeout(function(){window.location.href='/reboot'},3000)</script>
</body></html>"""
            
            response = f"""HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Connection: close

{html}"""
            
            client.sendall(response.encode('utf-8'))
            
        except Exception as e:
            self._send_error(client, 500, str(e))
    
    def _handle_reboot(self, client):
        """Handle reboot request."""
        html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rebooting</title>
<style>body{font-family:Arial,sans-serif;background:#0d1117;color:#c9d1d9;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;text-align:center}
h1{color:#58a6ff;margin-bottom:20px}</style>
</head><body>
<div><h1>🔄 Rebooting...</h1><p>Device is restarting now.</p></div>
</body></html>"""
        
        response = f"""HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Connection: close

{html}"""
        
        client.sendall(response.encode('utf-8'))
        
        time.sleep(1)
        import machine
        machine.reset()
    
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

def check_failsafe():
    """Check if device should enter failsafe mode."""
    try:
        os.stat('failsafe.flag')
        return True
    except OSError:
        return False

def start_failsafe():
    """Start failsafe mode."""
    failsafe = FailsafeMode()
    failsafe.start()
