# storage.py - JSON config persistence with atomic writes

import ujson as json
import os

class Storage:
    """Handles persistent configuration storage with atomic writes."""
    
    def __init__(self, filename="config.json"):
        self.filename = filename
        self.temp_filename = filename + ".tmp"
        self.backup_filename = filename + ".bak"
    
    def load(self, default=None):
        """Load configuration from file.
        
        Args:
            default: Default value to return if file doesn't exist
            
        Returns:
            Loaded configuration or default
        """
        # Try main file first
        data = self._load_file(self.filename)
        if data is not None:
            return data
        
        # Try backup file
        print(f"[STORAGE] Main file not found, trying backup...")
        data = self._load_file(self.backup_filename)
        if data is not None:
            # Restore from backup
            print(f"[STORAGE] Restored from backup")
            self._copy_file(self.backup_filename, self.filename)
            return data
        
        # Return default
        print(f"[STORAGE] No configuration found, using default")
        return default if default is not None else {}
    
    def save(self, data):
        """Save configuration to file with atomic write.
        
        Uses a temporary file and rename to ensure atomicity.
        Creates a backup of the previous version.
        
        Args:
            data: Data to save (must be JSON serializable)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create backup of existing file
            if self._file_exists(self.filename):
                self._copy_file(self.filename, self.backup_filename)
            
            # Write to temporary file
            with open(self.temp_filename, 'w') as f:
                json.dump(data, f)
            
            # Atomic rename
            self._rename_file(self.temp_filename, self.filename)
            
            print(f"[STORAGE] Configuration saved")
            return True
            
        except Exception as e:
            print(f"[STORAGE] Error saving configuration: {e}")
            # Clean up temp file if it exists
            self._remove_file(self.temp_filename)
            return False
    
    def update(self, updates):
        """Update specific fields in configuration.
        
        Args:
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        config = self.load()
        config = self._deep_update(config, updates)
        return self.save(config)
    
    def delete(self):
        """Delete configuration file and backup."""
        self._remove_file(self.filename)
        self._remove_file(self.backup_filename)
        self._remove_file(self.temp_filename)
        print(f"[STORAGE] Configuration deleted")
    
    def exists(self):
        """Check if configuration file exists."""
        return self._file_exists(self.filename)
    
    # Helper methods
    
    def _load_file(self, filename):
        """Load JSON from file."""
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except (OSError, ValueError):
            return None
    
    def _file_exists(self, filename):
        """Check if file exists."""
        try:
            os.stat(filename)
            return True
        except OSError:
            return False
    
    def _copy_file(self, src, dst):
        """Copy file from src to dst."""
        try:
            with open(src, 'rb') as f_src:
                with open(dst, 'wb') as f_dst:
                    f_dst.write(f_src.read())
            return True
        except OSError:
            return False
    
    def _rename_file(self, src, dst):
        """Rename file (atomic operation)."""
        try:
            # Remove destination if it exists (needed on some platforms)
            if self._file_exists(dst):
                os.remove(dst)
            os.rename(src, dst)
            return True
        except OSError:
            return False
    
    def _remove_file(self, filename):
        """Remove file if it exists."""
        try:
            if self._file_exists(filename):
                os.remove(filename)
            return True
        except OSError:
            return False
    
    def _deep_update(self, base, updates):
        """Deep update dictionary."""
        for key, value in updates.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                base[key] = self._deep_update(base[key], value)
            else:
                base[key] = value
        return base

# Convenience functions

def load_config(default=None):
    """Load configuration from default location."""
    from config import CONFIG_FILE, DEFAULT_CONFIG
    storage = Storage(CONFIG_FILE)
    config = storage.load(default=DEFAULT_CONFIG if default is None else default)
    return config

def save_config(data):
    """Save configuration to default location."""
    from config import CONFIG_FILE
    storage = Storage(CONFIG_FILE)
    return storage.save(data)

def update_config(updates):
    """Update configuration fields."""
    from config import CONFIG_FILE
    storage = Storage(CONFIG_FILE)
    return storage.update(updates)
