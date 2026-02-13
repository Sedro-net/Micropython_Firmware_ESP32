# led_ring.py - NeoPixel RGB LED ring control with non-blocking effects

from machine import Pin
from neopixel import NeoPixel
import time
from util import Timer, hsv_to_rgb, wheel

class LEDRing:
    """Non-blocking LED ring controller with effects."""
    
    def __init__(self, pin, num_leds, color_order="RGB"):
        """
        Initialize LED ring.
        
        Args:
            pin: GPIO pin number
            num_leds: Number of LEDs
            color_order: Color order ("RGB" or "GRB")
        """
        self.pin = Pin(pin, Pin.OUT)
        self.num_leds = num_leds
        self.color_order = color_order.upper()
        self.np = NeoPixel(self.pin, num_leds)
        
        # State
        self.enabled = True
        self.brightness = 128  # 0-255
        self.current_effect = "solid"
        self.effect_color = (255, 255, 255)
        self.effect_speed = 50  # ms per frame
        self.effect_data = {}  # Effect-specific data
        
        # Animation state
        self.last_update = Timer()
        self.frame = 0
        
        # Clear LEDs
        self.clear()
    
    def _remap_color(self, r, g, b):
        """Remap RGB to configured color order."""
        if self.color_order == "GRB":
            return (g, r, b)
        elif self.color_order == "BGR":
            return (b, g, r)
        else:  # RGB
            return (r, g, b)
    
    def _apply_brightness(self, r, g, b):
        """Apply brightness to color."""
        factor = self.brightness / 255.0
        return (int(r * factor), int(g * factor), int(b * factor))
    
    def _set_pixel(self, i, r, g, b):
        """Set pixel color with brightness and color order correction."""
        r, g, b = self._apply_brightness(r, g, b)
        r, g, b = self._remap_color(r, g, b)
        self.np[i] = (r, g, b)
    
    def set_brightness(self, brightness):
        """Set brightness (0-255)."""
        self.brightness = max(0, min(255, brightness))
    
    def set_effect(self, effect, color=(255, 255, 255), speed=50):
        """Set LED effect.
        
        Args:
            effect: Effect name (solid, rainbow, breathing, humidity_gauge, temperature_gauge)
            color: RGB tuple for effects that use a base color
            speed: Animation speed in ms per frame
        """
        self.current_effect = effect
        self.effect_color = color
        self.effect_speed = speed
        self.frame = 0
        self.effect_data = {}
        self.last_update.reset()
        print(f"[LED] Effect: {effect}, Color: {color}, Speed: {speed}ms")
    
    def set_state(self, state, brightness=None, color=None, effect=None):
        """Set LED state (for Home Assistant control).
        
        Args:
            state: "ON" or "OFF"
            brightness: 0-255
            color: RGB tuple
            effect: Effect name
        """
        if state.upper() == "ON":
            self.enabled = True
            if brightness is not None:
                self.set_brightness(brightness)
            if color is not None:
                self.effect_color = color
            if effect is not None:
                self.set_effect(effect, self.effect_color, self.effect_speed)
        else:
            self.enabled = False
            self.clear()
    
    def update(self):
        """Update LED animation (call regularly in main loop)."""
        if not self.enabled:
            return
        
        # Check if it's time to update
        if not self.last_update.has_elapsed(self.effect_speed):
            return
        
        self.last_update.reset()
        
        # Run current effect
        if self.current_effect == "solid":
            self._effect_solid()
        elif self.current_effect == "rainbow":
            self._effect_rainbow()
        elif self.current_effect == "breathing":
            self._effect_breathing()
        elif self.current_effect == "humidity_gauge":
            self._effect_humidity_gauge()
        elif self.current_effect == "temperature_gauge":
            self._effect_temperature_gauge()
        elif self.current_effect == "blink":
            self._effect_blink()
        else:
            self._effect_solid()
        
        self.show()
        self.frame += 1
    
    def _effect_solid(self):
        """Solid color effect."""
        r, g, b = self.effect_color
        for i in range(self.num_leds):
            self._set_pixel(i, r, g, b)
    
    def _effect_rainbow(self):
        """Rainbow cycle effect."""
        for i in range(self.num_leds):
            pixel_index = (i * 256 // self.num_leds) + self.frame
            r, g, b = wheel(pixel_index & 255)
            self._set_pixel(i, r, g, b)
    
    def _effect_breathing(self):
        """Breathing effect (fade in/out)."""
        # Calculate breathing brightness (0-255)
        import math
        brightness = int((math.sin(self.frame * 0.05) + 1) * 127.5)
        
        r, g, b = self.effect_color
        factor = brightness / 255.0
        
        for i in range(self.num_leds):
            self._set_pixel(i, int(r * factor), int(g * factor), int(b * factor))
    
    def _effect_humidity_gauge(self):
        """Humidity gauge effect (blue gradient).
        
        Expects self.effect_data['humidity'] to be set (0-100).
        """
        humidity = self.effect_data.get('humidity', 50)
        
        # Calculate number of LEDs to light up
        num_lit = int((humidity / 100.0) * self.num_leds)
        
        for i in range(self.num_leds):
            if i < num_lit:
                # Blue gradient from dark to bright
                intensity = int(((i + 1) / num_lit) * 255)
                self._set_pixel(i, 0, 0, intensity)
            else:
                self._set_pixel(i, 0, 0, 0)
    
    def _effect_temperature_gauge(self):
        """Temperature gauge effect (blue to red gradient).
        
        Expects self.effect_data['temperature'] to be set (0-40°C range).
        """
        temperature = self.effect_data.get('temperature', 20)
        
        # Map temperature to 0-1 range (assuming 0-40°C)
        temp_normalized = max(0, min(1, temperature / 40.0))
        
        # Calculate number of LEDs to light up
        num_lit = int(temp_normalized * self.num_leds)
        
        for i in range(self.num_leds):
            if i < num_lit:
                # Color gradient from blue (cold) to red (hot)
                ratio = (i + 1) / self.num_leds
                hue = (1 - ratio) * 240  # 240 = blue, 0 = red
                r, g, b = hsv_to_rgb(hue, 1.0, 1.0)
                self._set_pixel(i, r, g, b)
            else:
                self._set_pixel(i, 0, 0, 0)
    
    def _effect_blink(self):
        """Blinking effect."""
        if self.frame % 10 < 5:  # On for 5 frames, off for 5 frames
            r, g, b = self.effect_color
            for i in range(self.num_leds):
                self._set_pixel(i, r, g, b)
        else:
            self.clear()
    
    def set_gauge_data(self, temperature=None, humidity=None):
        """Set data for gauge effects."""
        if temperature is not None:
            self.effect_data['temperature'] = temperature
        if humidity is not None:
            self.effect_data['humidity'] = humidity
    
    def show(self):
        """Write buffer to LEDs."""
        self.np.write()
    
    def clear(self):
        """Turn off all LEDs."""
        for i in range(self.num_leds):
            self.np[i] = (0, 0, 0)
        self.show()
    
    def fill(self, r, g, b):
        """Fill all LEDs with color."""
        for i in range(self.num_leds):
            self._set_pixel(i, r, g, b)
        self.show()
    
    def get_state(self):
        """Get current LED state (for MQTT reporting)."""
        return {
            "state": "ON" if self.enabled else "OFF",
            "brightness": self.brightness,
            "color": {
                "r": self.effect_color[0],
                "g": self.effect_color[1],
                "b": self.effect_color[2]
            },
            "effect": self.current_effect
        }

def create_led_ring(pin=15, num_leds=12, color_order="RGB"):
    """Create LED ring instance.
    
    Args:
        pin: GPIO pin number
        num_leds: Number of LEDs
        color_order: Color order ("RGB" or "GRB")
        
    Returns:
        LEDRing instance
    """
    try:
        ring = LEDRing(pin, num_leds, color_order)
        print(f"[LED] Initialized {num_leds} LEDs on pin {pin}")
        return ring
    except Exception as e:
        print(f"[LED] Initialization error: {e}")
        return None
