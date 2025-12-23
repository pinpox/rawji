#!/usr/bin/env python3
"""
Fujifilm RAW Conversion - USB PTP Transport Layer

Implements USB PTP protocol for communication with Fujifilm cameras.
Based on:
- docs/libgphoto2/camlibs/ptp2/usb.c (USB PTP implementation)
- docs/fudge/lib/libusb.c (Fujifilm-specific USB)
- docs/fudge/lib/fuji_usb.c (RAW conversion workflow)
"""

import struct
import time
import usb.core
import usb.util
from typing import Optional, Tuple
from .fuji_enums import (
    PTPOperation,
    PTPResponseCode,
    PTP_DPC_FUJI_RawConvProfile,
    PTP_DPC_FUJI_StartRawConversion,
    FUJIFILM_USB_VENDOR_ID,
    FUJIFILM_CAMERA_PIDS,
)


# ==============================================================================
# PTP Container Structure (USB variant)
# ==============================================================================

class PTPContainer:
    """PTP container for USB bulk transfer (different from PTP/IP)"""

    # Container types
    COMMAND = 0x0001
    DATA = 0x0002
    RESPONSE = 0x0003
    EVENT = 0x0004

    def __init__(self, container_type: int, code: int, transaction_id: int, params: list = None, data: bytes = None):
        self.type = container_type
        self.code = code
        self.transaction_id = transaction_id
        self.params = params or []
        self.data = data or b''

    def pack(self) -> bytes:
        """Pack container into bytes for USB transmission"""
        # Header: length(4) + type(2) + code(2) + trans_id(4) = 12 bytes
        # Followed by up to 5 parameters (4 bytes each)
        # Followed by data (if any)

        params_bytes = b''
        for param in self.params[:5]:  # Max 5 parameters
            params_bytes += struct.pack('<I', param)

        total_length = 12 + len(params_bytes) + len(self.data)

        header = struct.pack('<I', total_length)  # Length
        header += struct.pack('<H', self.type)  # Type
        header += struct.pack('<H', self.code)  # Code
        header += struct.pack('<I', self.transaction_id)  # Transaction ID

        return header + params_bytes + self.data

    @classmethod
    def unpack(cls, data: bytes):
        """Unpack container from USB response"""
        if len(data) < 12:
            raise ValueError(f"Container too short: {len(data)} bytes")

        length, container_type, code, trans_id = struct.unpack('<IHHI', data[:12])

        # Parse parameters and payload
        params_data = data[12:]
        params = []
        payload = b''

        if container_type == cls.DATA:
            # DATA containers have NO parameters, everything after header is payload
            payload = params_data
        elif container_type == cls.RESPONSE:
            # RESPONSE containers can have up to 5 parameters, NO payload
            while len(params_data) >= 4 and len(params) < 5:
                param = struct.unpack('<I', params_data[:4])[0]
                params.append(param)
                params_data = params_data[4:]
        # COMMAND containers are only sent, never received, so we don't handle them here

        return cls(container_type, code, trans_id, params, payload)


# ==============================================================================
# USB PTP Transport
# ==============================================================================

class FujiCamera:
    """USB PTP communication with Fujifilm camera"""

    def __init__(self):
        self.dev = None
        self.ep_in = None  # Bulk IN endpoint
        self.ep_out = None  # Bulk OUT endpoint
        self.ep_int = None  # Interrupt endpoint (events)
        self.session_id = 0x00000001
        self.transaction_id = 0
        self.timeout = 5000  # 5 seconds default

    def find_camera(self) -> Optional[usb.core.Device]:
        """Find Fujifilm camera on USB"""
        print("[*] Searching for Fujifilm camera...")

        # Try known PIDs first
        for pid in FUJIFILM_CAMERA_PIDS:
            dev = usb.core.find(idVendor=FUJIFILM_USB_VENDOR_ID, idProduct=pid)
            if dev:
                print(f"[+] Found Fujifilm camera: VID=0x{FUJIFILM_USB_VENDOR_ID:04X}, PID=0x{pid:04X}")
                return dev

        # Try any Fujifilm device
        dev = usb.core.find(idVendor=FUJIFILM_USB_VENDOR_ID)
        if dev:
            print(f"[+] Found Fujifilm device: VID=0x{FUJIFILM_USB_VENDOR_ID:04X}, PID=0x{dev.idProduct:04X}")
            return dev

        return None

    def connect(self) -> bool:
        """Connect to camera and initialize USB endpoints"""
        self.dev = self.find_camera()
        if not self.dev:
            print("[-] No Fujifilm camera found")
            print("    Check:")
            print("    1. Camera is powered on")
            print("    2. USB cable is connected")
            print("    3. Camera is in 'USB RAW CONVERSION' mode")
            return False

        # Detach kernel driver if active
        try:
            if self.dev.is_kernel_driver_active(0):
                print("[*] Detaching kernel driver...")
                self.dev.detach_kernel_driver(0)
        except Exception as e:
            print(f"[!] Could not detach kernel driver: {e}")
            # Continue anyway - might work

        # Set configuration and claim interface
        try:
            self.dev.set_configuration()
            usb.util.claim_interface(self.dev, 0)
            print("[+] USB interface claimed")
        except Exception as e:
            print(f"[-] Failed to claim interface: {e}")
            return False

        # Find endpoints
        cfg = self.dev.get_active_configuration()
        intf = cfg[(0, 0)]

        # Find bulk endpoints
        for ep in intf:
            if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN:
                if usb.util.endpoint_type(ep.bmAttributes) == usb.util.ENDPOINT_TYPE_BULK:
                    self.ep_in = ep
                elif usb.util.endpoint_type(ep.bmAttributes) == usb.util.ENDPOINT_TYPE_INTR:
                    self.ep_int = ep
            else:
                if usb.util.endpoint_type(ep.bmAttributes) == usb.util.ENDPOINT_TYPE_BULK:
                    self.ep_out = ep

        if not self.ep_in or not self.ep_out:
            print("[-] Could not find bulk endpoints")
            return False

        print(f"[+] Endpoints: OUT=0x{self.ep_out.bEndpointAddress:02X}, IN=0x{self.ep_in.bEndpointAddress:02X}")

        # Open PTP session
        return self.open_session()

    def disconnect(self):
        """Close session and release USB resources"""
        if self.dev:
            try:
                self.close_session()
            except:
                pass

            try:
                usb.util.release_interface(self.dev, 0)
            except:
                pass

            self.dev = None

        print("[+] Disconnected from camera")

    def _next_transaction_id(self) -> int:
        """Generate next transaction ID"""
        self.transaction_id += 1
        return self.transaction_id

    def _send_container(self, container: PTPContainer):
        """Send PTP container via USB bulk OUT with chunking for large transfers"""
        data = container.pack()

        # Chunk large transfers to avoid USB memory issues
        # Based on libpict transport.c ptp_send_packet()
        max_chunk_size = 512 * 1024  # 512KB chunks
        offset = 0
        total = len(data)

        try:
            while offset < total:
                chunk_size = min(max_chunk_size, total - offset)
                chunk = data[offset:offset + chunk_size]
                self.ep_out.write(chunk, timeout=self.timeout)
                offset += chunk_size
        except Exception as e:
            raise IOError(f"USB write failed: {e}")

    def _recv_container(self) -> PTPContainer:
        """Receive PTP container via USB bulk IN, handling multi-packet transfers"""
        try:
            # Read first chunk to get container length
            first_chunk = self.ep_in.read(512 * 1024, timeout=self.timeout)
            data = bytearray(first_chunk)

            # Parse container header to get total length
            if len(data) < 12:
                raise IOError(f"Container too short: {len(data)} bytes")

            total_length = struct.unpack('<I', data[:4])[0]

            # Read remaining packets if needed
            while len(data) < total_length:
                chunk = self.ep_in.read(512 * 1024, timeout=self.timeout)
                data.extend(chunk)

                # Safety check to avoid infinite loops
                if len(data) > 100 * 1024 * 1024:  # 100MB limit
                    raise IOError(f"Container too large: {len(data)} bytes")

            return PTPContainer.unpack(bytes(data))
        except Exception as e:
            raise IOError(f"USB read failed: {e}")

    def send_command(self, opcode: int, params: list = None) -> Tuple[int, list, bytes]:
        """
        Send PTP command and receive response

        Returns: (response_code, response_params, data)
        """
        if params is None:
            params = []

        trans_id = self._next_transaction_id()

        # Send command container
        cmd = PTPContainer(PTPContainer.COMMAND, opcode, trans_id, params)
        self._send_container(cmd)

        # Receive response (might be DATA or RESPONSE)
        resp = self._recv_container()

        data = b''
        if resp.type == PTPContainer.DATA:
            # Data phase - extract data then wait for response
            data = resp.data
            resp = self._recv_container()

        if resp.type != PTPContainer.RESPONSE:
            raise IOError(f"Expected RESPONSE, got container type 0x{resp.type:04X}")

        return (resp.code, resp.params, data)

    def send_data_command(self, opcode: int, params: list, data: bytes) -> Tuple[int, list]:
        """
        Send PTP command with data phase

        Returns: (response_code, response_params)
        """
        trans_id = self._next_transaction_id()

        # Send command container
        cmd = PTPContainer(PTPContainer.COMMAND, opcode, trans_id, params)
        self._send_container(cmd)

        # Send data container
        data_cont = PTPContainer(PTPContainer.DATA, opcode, trans_id, data=data)
        self._send_container(data_cont)

        # Receive response
        resp = self._recv_container()

        if resp.type != PTPContainer.RESPONSE:
            raise IOError(f"Expected RESPONSE, got container type 0x{resp.type:04X}")

        return (resp.code, resp.params)

    # ==========================================================================
    # PTP Session Management
    # ==========================================================================

    def open_session(self) -> bool:
        """Open PTP session"""
        print(f"[*] Opening session (ID=0x{self.session_id:08X})...")

        code, params, _ = self.send_command(PTPOperation.OpenSession, [self.session_id])

        if code == PTPResponseCode.OK:
            print("[+] Session opened")
            return True
        elif code == 0x201E:  # SessionAlreadyOpen
            print("[!] Session already open, closing and reopening...")
            # Close the existing session
            try:
                self.send_command(PTPOperation.CloseSession)
            except:
                pass  # Ignore errors
            # Try opening again
            code, params, _ = self.send_command(PTPOperation.OpenSession, [self.session_id])
            if code == PTPResponseCode.OK:
                print("[+] Session opened")
                return True
            else:
                print(f"[-] OpenSession failed after close: 0x{code:04X}")
                return False
        else:
            print(f"[-] OpenSession failed: 0x{code:04X}")
            return False

    def close_session(self):
        """Close PTP session"""
        print("[*] Closing session...")

        try:
            code, _, _ = self.send_command(PTPOperation.CloseSession)
            if code == PTPResponseCode.OK:
                print("[+] Session closed")
        except:
            pass  # Ignore errors on close

    # ==========================================================================
    # RAW Conversion Operations
    # ==========================================================================

    def send_raf(self, filepath: str):
        """
        Upload RAF file to camera using Fujifilm vendor-specific commands

        Uses operations 0x900C (SendObjectInfo) and 0x900D (SendObject2)
        Based on fudge library: fuji_send_raf() in fuji_usb.c
        """
        print(f"[*] Sending RAF file: {filepath}")

        with open(filepath, 'rb') as f:
            raf_data = f.read()

        print(f"[*] RAF file size: {len(raf_data)} bytes ({len(raf_data) / 1024 / 1024:.1f} MB)")

        # Build ObjectInfo structure - use proper PTP ObjectInfo format!
        # Based on actual C code: fuji_send_raf() in fuji_usb.c line 307-310
        object_info = bytearray()

        # StorageID (uint32) = 0
        object_info += struct.pack('<I', 0)

        # ObjectFormat (uint16) = 0xf802 (NOT 0x5000!)
        object_info += struct.pack('<H', 0xf802)

        # ProtectionStatus (uint16) = 0
        object_info += struct.pack('<H', 0)

        # CompressedSize (uint32) = file_size
        object_info += struct.pack('<I', len(raf_data))

        # ThumbFormat (uint16) = 0
        object_info += struct.pack('<H', 0)

        # ThumbCompressedSize (uint32) = 0
        object_info += struct.pack('<I', 0)

        # ThumbPixWidth (uint32) = 0
        object_info += struct.pack('<I', 0)

        # ThumbPixHeight (uint32) = 0
        object_info += struct.pack('<I', 0)

        # ImagePixWidth (uint32) = 0
        object_info += struct.pack('<I', 0)

        # ImagePixHeight (uint32) = 0
        object_info += struct.pack('<I', 0)

        # ImageBitDepth (uint32) = 0
        object_info += struct.pack('<I', 0)

        # ParentObject (uint32) = 0
        object_info += struct.pack('<I', 0)

        # AssociationType (uint16) = 0
        object_info += struct.pack('<H', 0)

        # AssociationDesc (uint32) = 0
        object_info += struct.pack('<I', 0)

        # SequenceNumber (uint32) = 0
        object_info += struct.pack('<I', 0)

        # Filename (PTP string) - "FUP_FILE.dat"
        filename = "FUP_FILE.dat"
        filename_len = len(filename) + 1  # Include null terminator
        object_info += struct.pack('B', filename_len)
        for char in filename:
            object_info += struct.pack('<H', ord(char))
        object_info += struct.pack('<H', 0)  # Null terminator

        # CaptureDate (empty PTP string)
        object_info += struct.pack('B', 0)

        # ModificationDate (empty PTP string)
        object_info += struct.pack('B', 0)

        # Keywords (empty PTP string)
        object_info += struct.pack('B', 0)

        print(f"[*] ObjectInfo size: {len(object_info)} bytes")

        # Step 1: Send ObjectInfo using Fuji vendor command 0x900C
        # The C code calls fuji_send_object_info_ex() which uses PTP_OC_FUJI_SendObjectInfo
        print("[*] Sending object info (Fuji SendObjectInfo, 0x900C)...")
        code, params = self.send_data_command(
            0x900C,  # PTP_OC_FUJI_SendObjectInfo
            [0, 0, 0],  # storage_id, handle, 0 (3 params for Fuji variant!)
            bytes(object_info)
        )

        if code != PTPResponseCode.OK:
            raise IOError(f"SendObjectInfo failed: 0x{code:04X}")

        print("[+] Object info sent")

        # Step 2: Send RAF data using Fuji vendor command 0x900D
        # The C code calls fuji_send_object_ex() which uses PTP_OC_FUJI_SendObject2
        print("[*] Sending RAF data (Fuji SendObject2, 0x900D)...")
        code, params = self.send_data_command(
            0x900D,  # PTP_OC_FUJI_SendObject2
            [],  # No parameters
            raf_data
        )

        if code != PTPResponseCode.OK:
            raise IOError(f"SendObject failed: 0x{code:04X}")

        print("[+] RAF file sent successfully")

    def get_profile(self) -> bytes:
        """Get RAW conversion profile from camera (property 0xD185)"""
        print("[*] Getting RAW profile from camera...")

        code, params, data = self.send_command(
            PTPOperation.GetDevicePropValue,
            [PTP_DPC_FUJI_RawConvProfile]
        )

        if code != PTPResponseCode.OK:
            raise IOError(f"GetDevicePropValue(0xD185) failed: 0x{code:04X}")

        print(f"[+] Received profile: {len(data)} bytes")

        if len(data) == 0:
            raise IOError("Profile data is empty")

        return data

    def set_profile(self, profile: bytes):
        """Send modified RAW profile to camera (property 0xD185)"""
        print(f"[*] Sending modified profile ({len(profile)} bytes)...")

        # Debug: Check FilmSimulation value in profile being sent
        if len(profile) >= 500:  # 468 + 7*4 + 4
            offset = 468 + 7 * 4
            film_sim = struct.unpack('<I', profile[offset:offset+4])[0]
            print(f"    DEBUG: FilmSimulation in profile = 0x{film_sim:02X}")

        code, params = self.send_data_command(
            PTPOperation.SetDevicePropValue,
            [PTP_DPC_FUJI_RawConvProfile],
            profile
        )

        if code != PTPResponseCode.OK:
            raise IOError(f"SetDevicePropValue(0xD185) failed: 0x{code:04X}")

        print("[+] Profile sent successfully")

    def trigger_conversion(self):
        """Trigger RAW conversion (set property 0xD183 to 0)"""
        print("[*] Triggering RAW conversion...")

        # Value is just uint16 = 0
        data = struct.pack('<H', 0)

        code, params = self.send_data_command(
            PTPOperation.SetDevicePropValue,
            [PTP_DPC_FUJI_StartRawConversion],
            data
        )

        if code != PTPResponseCode.OK:
            raise IOError(f"StartRawConversion failed: 0x{code:04X}")

        print("[+] Conversion started")

    def wait_for_result(self, timeout: int = 30) -> bytes:
        """
        Poll for converted JPEG and download it

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            JPEG data as bytes
        """
        print("[*] Waiting for conversion result", end='', flush=True)

        start_time = time.time()

        while time.time() - start_time < timeout:
            # GetObjectHandles (storage_id=-1, format=0, parent=0)
            code, params, data = self.send_command(
                PTPOperation.GetObjectHandles,
                [0xFFFFFFFF, 0x0000, 0x00000000]
            )

            if code != PTPResponseCode.OK:
                raise IOError(f"GetObjectHandles failed: 0x{code:04X}")

            # Parse object handles from data
            if len(data) >= 4:
                num_handles = struct.unpack('<I', data[:4])[0]

                if num_handles > 0:
                    # Extract first handle
                    handle = struct.unpack('<I', data[4:8])[0]

                    print(f"\n[+] Conversion complete! (handle=0x{handle:08X})")

                    # Download object
                    print("[*] Downloading JPEG...")
                    code, params, jpeg_data = self.send_command(
                        PTPOperation.GetObject,
                        [handle]
                    )

                    if code != PTPResponseCode.OK:
                        raise IOError(f"GetObject failed: 0x{code:04X}")

                    print(f"[+] Downloaded {len(jpeg_data)} bytes ({len(jpeg_data) / 1024 / 1024:.1f} MB)")

                    # Delete temp object
                    print("[*] Cleaning up temporary object...")
                    code, _, _ = self.send_command(
                        PTPOperation.DeleteObject,
                        [handle]
                    )

                    return jpeg_data

            print(".", end='', flush=True)
            time.sleep(1)

        raise TimeoutError(f"Conversion timeout after {timeout} seconds")
