# ota.py - Over-The-Air firmware update with SHA-256 verification

import urequests
import uhashlib
import os
import machine
import gc

class OTAUpdater:
    """OTA firmware updater with verification and rollback protection."""
    
    def __init__(self, url=None, verify_sha256=True):
        """
        Initialize OTA updater.
        
        Args:
            url: Firmware URL
            verify_sha256: Enable SHA-256 verification
        """
        self.url = url
        self.verify_sha256 = verify_sha256
        self.temp_file = "firmware.tmp"
        self.backup_dir = "backup"
    
    def check_update(self, manifest_url=None):
        """Check if update is available.
        
        Args:
            manifest_url: URL to manifest JSON file
            
        Returns:
            Dict with update info or None
        """
        if not manifest_url:
            return None
        
        try:
            print(f"[OTA] Checking for updates: {manifest_url}")
            
            response = urequests.get(manifest_url, timeout=10)
            
            if response.status_code != 200:
                print(f"[OTA] Manifest not found: {response.status_code}")
                response.close()
                return None
            
            import ujson
            manifest = ujson.loads(response.text)
            response.close()
            
            # Check version
            import config
            current_version = config.FIRMWARE_VERSION
            available_version = manifest.get('version', '0.0.0')
            
            print(f"[OTA] Current: {current_version}, Available: {available_version}")
            
            if available_version > current_version:
                print("[OTA] Update available")
                return manifest
            else:
                print("[OTA] No update needed")
                return None
                
        except Exception as e:
            print(f"[OTA] Check update error: {e}")
            return None
    
    def download_firmware(self, url, expected_sha256=None):
        """Download firmware file.
        
        Args:
            url: Firmware URL
            expected_sha256: Expected SHA-256 hash (hex string)
            
        Returns:
            True if successful
        """
        try:
            print(f"[OTA] Downloading firmware from {url}")
            
            # Free memory
            gc.collect()
            
            response = urequests.get(url, timeout=60)
            
            if response.status_code != 200:
                print(f"[OTA] Download failed: {response.status_code}")
                response.close()
                return False
            
            # Get content length
            content_length = int(response.headers.get('Content-Length', 0))
            print(f"[OTA] Firmware size: {content_length} bytes")
            
            # Download in chunks
            sha256 = uhashlib.sha256() if self.verify_sha256 else None
            bytes_downloaded = 0
            chunk_size = 4096
            
            with open(self.temp_file, 'wb') as f:
                while True:
                    chunk = response.raw.read(chunk_size)
                    if not chunk:
                        break
                    
                    f.write(chunk)
                    bytes_downloaded += len(chunk)
                    
                    if sha256:
                        sha256.update(chunk)
                    
                    # Progress
                    if content_length > 0:
                        progress = (bytes_downloaded / content_length) * 100
                        print(f"[OTA] Progress: {progress:.1f}%")
                    
                    # Free memory
                    gc.collect()
            
            response.close()
            
            print(f"[OTA] Downloaded {bytes_downloaded} bytes")
            
            # Verify SHA-256
            if self.verify_sha256 and expected_sha256:
                actual_sha256 = sha256.digest().hex()
                print(f"[OTA] Expected SHA-256: {expected_sha256}")
                print(f"[OTA] Actual SHA-256:   {actual_sha256}")
                
                if actual_sha256 != expected_sha256:
                    print("[OTA] SHA-256 verification failed!")
                    self._cleanup()
                    return False
                
                print("[OTA] SHA-256 verified")
            
            return True
            
        except Exception as e:
            print(f"[OTA] Download error: {e}")
            self._cleanup()
            return False
    
    def apply_update(self):
        """Apply downloaded update.
        
        This creates a backup and replaces the main.py file.
        After applying, device should be reset.
        
        Returns:
            True if successful
        """
        try:
            print("[OTA] Applying update...")
            
            # Verify temp file exists
            if not self._file_exists(self.temp_file):
                print("[OTA] Temporary file not found")
                return False
            
            # Create backup directory
            self._mkdir(self.backup_dir)
            
            # List of files to backup/update
            files_to_update = [
                'main.py',
                'boot.py',
                'config.py'
            ]
            
            # For this implementation, we assume the downloaded file is a tar or
            # we update main.py only. Adjust based on your needs.
            
            # Backup current main.py
            if self._file_exists('main.py'):
                print("[OTA] Backing up main.py")
                self._copy_file('main.py', f'{self.backup_dir}/main.py.bak')
            
            # Replace main.py with downloaded firmware
            print("[OTA] Installing new firmware")
            self._copy_file(self.temp_file, 'main.py')
            
            # Cleanup temp file
            self._cleanup()
            
            print("[OTA] Update applied successfully")
            print("[OTA] Device will reboot in 3 seconds...")
            
            import time
            time.sleep(3)
            
            # Reset device
            machine.reset()
            
            return True
            
        except Exception as e:
            print(f"[OTA] Apply update error: {e}")
            return False
    
    def rollback(self):
        """Rollback to backup firmware."""
        try:
            backup_file = f'{self.backup_dir}/main.py.bak'
            
            if not self._file_exists(backup_file):
                print("[OTA] No backup found")
                return False
            
            print("[OTA] Rolling back to backup...")
            self._copy_file(backup_file, 'main.py')
            
            print("[OTA] Rollback complete, rebooting...")
            
            import time
            time.sleep(2)
            machine.reset()
            
            return True
            
        except Exception as e:
            print(f"[OTA] Rollback error: {e}")
            return False
    
    def update(self, url, sha256=None):
        """Complete update process: download, verify, and apply.
        
        Args:
            url: Firmware URL
            sha256: Expected SHA-256 hash
            
        Returns:
            True if successful
        """
        print("[OTA] Starting OTA update...")
        
        # Download
        if not self.download_firmware(url, sha256):
            print("[OTA] Update failed: download error")
            return False
        
        # Apply
        return self.apply_update()
    
    def _cleanup(self):
        """Clean up temporary files."""
        try:
            if self._file_exists(self.temp_file):
                os.remove(self.temp_file)
                print("[OTA] Cleaned up temporary files")
        except:
            pass
    
    def _file_exists(self, path):
        """Check if file exists."""
        try:
            os.stat(path)
            return True
        except OSError:
            return False
    
    def _copy_file(self, src, dst):
        """Copy file."""
        with open(src, 'rb') as f_src:
            with open(dst, 'wb') as f_dst:
                while True:
                    chunk = f_src.read(4096)
                    if not chunk:
                        break
                    f_dst.write(chunk)
    
    def _mkdir(self, path):
        """Create directory if not exists."""
        try:
            os.mkdir(path)
        except OSError:
            pass  # Already exists

def perform_ota_update(url, sha256=None):
    """Perform OTA update.
    
    Args:
        url: Firmware URL
        sha256: Expected SHA-256 hash
        
    Returns:
        True if successful
    """
    updater = OTAUpdater(url=url, verify_sha256=(sha256 is not None))
    return updater.update(url, sha256)
