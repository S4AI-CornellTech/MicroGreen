#!/usr/bin/env python3
"""
BLE Connection Monitor - Monitor device connection and track data transfer.
"""
# /// script
# dependencies = [
#     "bleak",
# ]
# ///
#!/usr/bin/env python3

import asyncio
import time
from collections import deque
from bleak import BleakClient, BleakScanner

# Nordic UART Service UUIDs
UART_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"

# Target devices
TARGET_DEVICES = ["PicoNUS", "Pico2NUS", "NanoBLE", "ESP32-NUS", "BTstack"]

class Monitor:
    def __init__(self):
        self.bytes_received = 0
        self.message_count = 0
        self.last_stats_time = time.time()
        self.last_stats_bytes = 0
        self.last_stats_messages = 0
        self.session_start_time = 0
        
        
        self.recent_messages = deque(maxlen=100)
        
    def notification_handler(self, sender, data):
        """Optimized notification handler"""
        self.bytes_received += len(data)
        self.message_count += 1
        
        
        if self.message_count % 50 == 0:
            current_time = time.time()
            elapsed = current_time - self.last_stats_time
            
            if elapsed >= 2.0: 
                bytes_delta = self.bytes_received - self.last_stats_bytes
                msg_delta = self.message_count - self.last_stats_messages
                
                data_rate = bytes_delta / elapsed if elapsed > 0 else 0
                msg_rate = msg_delta / elapsed if elapsed > 0 else 0
                
                print(f"[{time.strftime('%H:%M:%S')}] "
                      f"Rate: {data_rate:.0f} B/s, {msg_rate:.1f} msg/s, "
                      f"Total: {self.message_count} msgs, {self.bytes_received} bytes")
                
                self.last_stats_time = current_time
                self.last_stats_bytes = self.bytes_received
                self.last_stats_messages = self.message_count

async def scan_for_target_device():
    """Scan for target device"""
    devices = await BleakScanner.discover(timeout=5)
    
    for device in devices:
        if device.name in TARGET_DEVICES:
            print(f"Found device: {device.name} at {device.address}")
            return device
    
    return None

async def monitor_device_connection(device):
    """Monitor device connection"""
    monitor = Monitor()
    monitor.session_start_time = time.time()
    
    print(f"Connecting to {device.name}")
    
    try:
        async with BleakClient(device.address, timeout=20.0) as client:
            connect_time = time.time() - monitor.session_start_time
            print(f"Connected in {connect_time:.2f} seconds")
            
            services = client.services
            uart_service = None
            for service in services:
                if service.uuid.lower() == UART_SERVICE_UUID.lower():
                    uart_service = service
                    break
            
            if not uart_service:
                print("Nordic UART Service not found")
                return
            
            await client.start_notify(UART_TX_CHAR_UUID, monitor.notification_handler)
            print("Monitoring data transfer...")
           
            # Monitor connection
            start_monitor = time.time()
            while client.is_connected:
                await asyncio.sleep(0.1) 
                
                if time.time() - start_monitor > 30:  
                    print(f"Still connected after {time.time() - monitor.session_start_time:.0f}s")
                    start_monitor = time.time()
            
            print("Connection lost")
            
    except Exception as e:
        print(f"Connection failed: {e}")
    
    finally:
        session_duration = time.time() - monitor.session_start_time
        
        print(f"\n=== SESSION SUMMARY ===")
        print(f"Device: {device.name}")
        print(f"Duration: {session_duration:.2f} seconds")
        print(f"Messages received: {monitor.message_count}")
        print(f"Total bytes received: {monitor.bytes_received}")
        
        if session_duration > 0 and monitor.bytes_received > 0:
            avg_rate = monitor.bytes_received / session_duration
            print(f"Average data rate: {avg_rate:.2f} bytes/second ({avg_rate*8/1000:.1f} kbps)")
            
            if monitor.message_count > 0:
                avg_message_size = monitor.bytes_received / monitor.message_count
                message_rate = monitor.message_count / session_duration
                print(f"Average message size: {avg_message_size:.1f} bytes")
                print(f"Message rate: {message_rate:.2f} messages/second")

async def main():
    print("BLE Connection Monitor")
    print(f"Target devices: {', '.join(TARGET_DEVICES)}")
    
    while True:
        try:
            print("\nScanning for target devices...")
            device = await scan_for_target_device()
            
            if device:
                await monitor_device_connection(device)
                break
            else:
                print("No target devices found, retrying in 5 seconds")
                await asyncio.sleep(5)
                
        except KeyboardInterrupt:
            print("\nMonitoring stopped")
            break
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())