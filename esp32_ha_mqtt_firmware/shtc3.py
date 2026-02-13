# shtc3.py - SHTC3 temperature/humidity sensor driver

from machine import I2C, Pin
import time

class SHTC3:
    """Driver for SHTC3 temperature and humidity sensor."""
    
    # I2C address
    ADDRESS = 0x70
    
    # Commands
    CMD_SLEEP = b'\xB0\x98'
    CMD_WAKEUP = b'\x35\x17'
    CMD_SOFT_RESET = b'\x80\x5D'
    CMD_READ_ID = b'\xEF\xC8'
    
    # Measurement commands (Normal mode, Clock stretching disabled)
    CMD_MEASURE_T_FIRST = b'\x78\x66'  # Temperature first, normal mode
    CMD_MEASURE_RH_FIRST = b'\x58\xE0'  # Humidity first, normal mode
    
    def __init__(self, i2c, address=ADDRESS):
        """
        Initialize SHTC3 sensor.
        
        Args:
            i2c: I2C bus instance
            address: I2C address (default 0x70)
        """
        self.i2c = i2c
        self.address = address
        self.last_temp = None
        self.last_humidity = None
        self.error_count = 0
        
        # Wake up sensor
        self._wakeup()
        
        # Verify sensor ID
        if not self._verify_id():
            print("[SHTC3] Warning: Could not verify sensor ID")
    
    def _wakeup(self):
        """Wake up sensor from sleep mode."""
        try:
            self.i2c.writeto(self.address, self.CMD_WAKEUP)
            time.sleep_ms(1)  # Wait for wake up
        except OSError as e:
            print(f"[SHTC3] Wake up failed: {e}")
    
    def _sleep(self):
        """Put sensor to sleep mode."""
        try:
            self.i2c.writeto(self.address, self.CMD_SLEEP)
        except OSError as e:
            print(f"[SHTC3] Sleep failed: {e}")
    
    def _verify_id(self):
        """Verify sensor ID."""
        try:
            self.i2c.writeto(self.address, self.CMD_READ_ID)
            time.sleep_ms(1)
            data = self.i2c.readfrom(self.address, 3)
            
            # ID should be 0x0807
            sensor_id = (data[0] << 8) | data[1]
            
            if sensor_id == 0x0807:
                print(f"[SHTC3] Sensor ID verified: 0x{sensor_id:04X}")
                return True
            else:
                print(f"[SHTC3] Unexpected sensor ID: 0x{sensor_id:04X}")
                return False
                
        except Exception as e:
            print(f"[SHTC3] ID verification failed: {e}")
            return False
    
    def soft_reset(self):
        """Perform soft reset of sensor."""
        try:
            self._wakeup()
            self.i2c.writeto(self.address, self.CMD_SOFT_RESET)
            time.sleep_ms(1)
            print("[SHTC3] Soft reset performed")
            return True
        except Exception as e:
            print(f"[SHTC3] Soft reset failed: {e}")
            return False
    
    def read(self, retries=3):
        """Read temperature and humidity.
        
        Args:
            retries: Number of retry attempts
            
        Returns:
            Tuple of (temperature_C, humidity_percent) or (None, None) on error
        """
        for attempt in range(retries):
            try:
                # Wake up sensor
                self._wakeup()
                
                # Start measurement (temperature first)
                self.i2c.writeto(self.address, self.CMD_MEASURE_T_FIRST)
                
                # Wait for measurement (typical 12.1ms)
                time.sleep_ms(15)
                
                # Read 6 bytes: temp_msb, temp_lsb, temp_crc, hum_msb, hum_lsb, hum_crc
                data = self.i2c.readfrom(self.address, 6)
                
                # Put sensor to sleep
                self._sleep()
                
                # Parse temperature
                temp_raw = (data[0] << 8) | data[1]
                temp_c = -45 + 175 * (temp_raw / 65535.0)
                
                # Parse humidity
                hum_raw = (data[3] << 8) | data[4]
                hum_percent = 100 * (hum_raw / 65535.0)
                
                # Validate ranges
                if -40 <= temp_c <= 125 and 0 <= hum_percent <= 100:
                    self.last_temp = temp_c
                    self.last_humidity = hum_percent
                    self.error_count = 0
                    return temp_c, hum_percent
                else:
                    print(f"[SHTC3] Invalid reading: T={temp_c:.1f}C, H={hum_percent:.1f}%")
                    
            except Exception as e:
                print(f"[SHTC3] Read error (attempt {attempt + 1}/{retries}): {e}")
                time.sleep_ms(100)
        
        # All retries failed
        self.error_count += 1
        print(f"[SHTC3] Read failed after {retries} attempts")
        return None, None
    
    def read_temperature(self, retries=3):
        """Read only temperature."""
        temp, _ = self.read(retries)
        return temp
    
    def read_humidity(self, retries=3):
        """Read only humidity."""
        _, hum = self.read(retries)
        return hum
    
    def get_last_reading(self):
        """Get last successful reading."""
        return self.last_temp, self.last_humidity
    
    def is_available(self):
        """Check if sensor is available."""
        try:
            devices = self.i2c.scan()
            return self.address in devices
        except:
            return False

def create_shtc3(sda_pin=21, scl_pin=22, freq=400000):
    """Create SHTC3 sensor instance.
    
    Args:
        sda_pin: SDA pin number
        scl_pin: SCL pin number
        freq: I2C frequency in Hz
        
    Returns:
        SHTC3 instance or None on error
    """
    try:
        i2c = I2C(0, scl=Pin(scl_pin), sda=Pin(sda_pin), freq=freq)
        
        # Scan for devices
        devices = i2c.scan()
        print(f"[I2C] Found devices: {[hex(d) for d in devices]}")
        
        if SHTC3.ADDRESS not in devices:
            print(f"[SHTC3] Sensor not found at address 0x{SHTC3.ADDRESS:02X}")
            return None
        
        sensor = SHTC3(i2c)
        print("[SHTC3] Sensor initialized")
        return sensor
        
    except Exception as e:
        print(f"[SHTC3] Initialization error: {e}")
        return None
