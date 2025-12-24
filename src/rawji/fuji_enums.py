#!/usr/bin/env python3
"""
Fujifilm RAW Conversion - Constants and Enumerations

All constants extracted from:
- docs/fudge/lib/fp/src/fp.h
- docs/fudge/lib/fujiptp.h
- docs/libgphoto2/camlibs/ptp2/ptp.h
"""

from enum import IntEnum


# ==============================================================================
# PTP Standard Operation Codes
# ==============================================================================

class PTPOperation(IntEnum):
    """Standard PTP operation codes (ISO 15740)"""
    GetDeviceInfo = 0x1001
    OpenSession = 0x1002
    CloseSession = 0x1003
    GetStorageIDs = 0x1004
    GetStorageInfo = 0x1005
    GetNumObjects = 0x1006
    GetObjectHandles = 0x1007
    GetObjectInfo = 0x1008
    GetObject = 0x1009
    DeleteObject = 0x100B
    SendObjectInfo = 0x100C
    SendObject = 0x100D
    GetDevicePropDesc = 0x1014
    GetDevicePropValue = 0x1015
    SetDevicePropValue = 0x1016


class PTPResponseCode(IntEnum):
    """PTP response codes"""
    OK = 0x2001
    GeneralError = 0x2002
    SessionNotOpen = 0x2003
    InvalidTransactionID = 0x2004
    OperationNotSupported = 0x2005
    ParameterNotSupported = 0x2006
    IncompleteTransfer = 0x2007
    InvalidStorageID = 0x2008
    InvalidObjectHandle = 0x2009
    DevicePropNotSupported = 0x200A


# ==============================================================================
# Fujifilm Device Properties
# ==============================================================================

# Critical properties for RAW conversion
PTP_DPC_FUJI_RawConvProfile = 0xD185  # The 605/628-byte d185 profile
PTP_DPC_FUJI_StartRawConversion = 0xD183  # Trigger conversion (set to 0)


# ==============================================================================
# Film Simulations
# ==============================================================================

class FilmSimulation(IntEnum):
    """Fujifilm film simulation modes"""
    Provia = 0x1  # Standard
    Velvia = 0x2  # Vivid
    Astia = 0x3  # Soft
    ProNegHi = 0x4  # Pro Neg. Hi
    ProNegStd = 0x5  # Pro Neg. Std
    Monochrome = 0x6  # B&W
    MonochromeYe = 0x7  # B&W + Yellow filter
    MonochromeR = 0x8  # B&W + Red filter
    MonochromeG = 0x9  # B&W + Green filter
    Sepia = 0xA
    ClassicChrome = 0xB
    Acros = 0xC  # Acros (modern B&W)
    AcrosYe = 0xD  # Acros + Yellow filter
    AcrosR = 0xE  # Acros + Red filter
    AcrosG = 0xF  # Acros + Green filter
    Eterna = 0x10  # Cinema
    EternaBleach = 0x11  # Eterna Bleach Bypass

    @classmethod
    def names(cls):
        """Return list of film simulation names for argparse choices"""
        return [name.lower().replace('_', '-') for name in cls.__members__.keys()]

    @classmethod
    def from_name(cls, name: str):
        """Convert CLI name to enum value"""
        # Convert 'classic-chrome' -> 'ClassicChrome'
        # Need to handle special cases like 'proneghi' -> 'ProNegHi'
        name_normalized = name.replace('-', '').lower()
        for member_name in cls.__members__.keys():
            if member_name.lower() == name_normalized:
                return cls[member_name]
        raise ValueError(f"Unknown film simulation: {name}")


# ==============================================================================
# White Balance
# ==============================================================================

class WhiteBalance(IntEnum):
    """White balance modes"""
    AsShot = 0x0  # Use camera's original WB
    Auto = 0x2
    Daylight = 0x4
    Incandescent = 0x6
    Underwater = 0x8
    Fluorescent1 = 0x8001  # Warm white fluorescent
    Fluorescent2 = 0x8002  # Cool white fluorescent
    Fluorescent3 = 0x8003  # Daylight fluorescent
    Shade = 0x8006
    Temperature = 0x8007  # Use WBColorTemp instead
    Custom1 = 0x8008
    Custom2 = 0x8009
    Custom3 = 0x800A

    @classmethod
    def names(cls):
        """Return list of WB names for argparse choices"""
        return [name.lower().replace('_', '-') for name in cls.__members__.keys()]

    @classmethod
    def from_name(cls, name: str):
        """Convert CLI name to enum value"""
        enum_name = name.replace('-', ' ').title().replace(' ', '')
        return cls[enum_name]


# ==============================================================================
# Image Quality & Size
# ==============================================================================

class ImageQuality(IntEnum):
    """JPEG quality"""
    Fine = 0x2
    Normal = 0x3


class ImageSize(IntEnum):
    """Output image size (aspect ratio encoded)"""
    S_3x2 = 0x1  # Small 3:2
    S_16x9 = 0x2  # Small 16:9
    S_1x1 = 0x3  # Small 1:1 (square)
    M_3x2 = 0x4  # Medium 3:2
    M_16x9 = 0x5  # Medium 16:9
    M_1x1 = 0x6  # Medium 1:1
    L_3x2 = 0x7  # Large 3:2
    L_16x9 = 0x8  # Large 16:9
    L_1x1 = 0x9  # Large 1:1

    @classmethod
    def names(cls):
        """Return list of size names for argparse choices"""
        return [name.lower().replace('_', '-') for name in cls.__members__.keys()]

    @classmethod
    def from_name(cls, name: str):
        """Convert CLI name to enum value"""
        enum_name = name.upper().replace('-', '_')
        return cls[enum_name]


# ==============================================================================
# Dynamic Range
# ==============================================================================

class DynamicRange(IntEnum):
    """Dynamic range settings"""
    DR100 = 0x1  # Standard (100%)
    DR200 = 0x2  # +1 EV (200%)
    DR400 = 0x3  # +2 EV (400%)

    @classmethod
    def from_percent(cls, value: int):
        """Convert percentage (100, 200, 400) to enum"""
        if value == 100:
            return cls.DR100
        elif value == 200:
            return cls.DR200
        elif value == 400:
            return cls.DR400
        else:
            raise ValueError(f"Invalid dynamic range: {value} (must be 100, 200, or 400)")


# ==============================================================================
# Effects
# ==============================================================================

class GrainEffect(IntEnum):
    """Film grain effect strength"""
    Off = 0x1
    Weak = 0x2
    Strong = 0x3

    @classmethod
    def names(cls):
        """Return list of grain effect names for argparse choices"""
        return [name.lower() for name in cls.__members__.keys()]

    @classmethod
    def from_name(cls, name: str):
        """Convert CLI name to enum value"""
        return cls[name.capitalize()]


class GrainEffectSize(IntEnum):
    """Film grain size"""
    Small = 0x0
    Large = 0x1


class ChromeEffect(IntEnum):
    """Color chrome effect strength"""
    Off = 0x1
    Weak = 0x2
    Strong = 0x3

    @classmethod
    def names(cls):
        """Return list of chrome effect names for argparse choices"""
        return [name.lower() for name in cls.__members__.keys()]

    @classmethod
    def from_name(cls, name: str):
        """Convert CLI name to enum value"""
        return cls[name.capitalize()]


class ColorChromeBlue(IntEnum):
    """Color chrome blue effect"""
    Off = 0x0
    Weak = 0x1
    Strong = 0x2


# ==============================================================================
# Exposure Bias Constants
# ==============================================================================

# Exposure bias is stored as int32 in units of 1/1000 EV
# Range: -5.0 to +5.0 EV in 1/3 stop increments
# Examples:
#   0.0 EV = 0
#  +1.0 EV = 1000
#  -2.33 EV = -2333 (approx -2 1/3 stops)

FP_EV_ZERO = 0
FP_EV_PLUS_5 = 5000
FP_EV_MIN_5 = -5000


def ev_to_int(ev: float) -> int:
    """Convert EV float to int32 for profile (-5.0 to +5.0)"""
    if ev < -5.0 or ev > 5.0:
        raise ValueError(f"Exposure bias out of range: {ev} EV (must be -5.0 to +5.0)")
    return int(ev * 1000)


def int_to_ev(value: int) -> float:
    """Convert int32 from profile to EV float"""
    return value / 1000.0


# ==============================================================================
# Tone/Color Range Constants (-4 to +4)
# ==============================================================================

# These parameters use simple signed int:
# - HighlightTone: -4 to +4
# - ShadowTone: -4 to +4
# - Color: -4 to +4
# - Sharpness: -4 to +4
# - NoiseReduction: -4 to +4
# - Clarity: -5 to +5

FP_TONE_MIN = -4
FP_TONE_MAX = 4
FP_TONE_ZERO = 0

FP_CLARITY_MIN = -5
FP_CLARITY_MAX = 5


def validate_tone(value: int, min_val: int = -4, max_val: int = 4, name: str = "parameter") -> int:
    """Validate tone/color parameter range"""
    if value < min_val or value > max_val:
        raise ValueError(f"{name} out of range: {value} (must be {min_val} to {max_val})")
    return value


# ==============================================================================
# White Balance Shift Constants
# ==============================================================================

# WB shift: -9 to +9 for both R and B channels
FP_WB_SHIFT_MIN = -9
FP_WB_SHIFT_MAX = 9


def validate_wb_shift(value: int) -> int:
    """Validate WB shift parameter (-9 to +9)"""
    if value < -9 or value > 9:
        raise ValueError(f"WB shift out of range: {value} (must be -9 to +9)")
    return value


# ==============================================================================
# Color Temperature Constants
# ==============================================================================

# Color temperature: 2500K to 10000K (when WhiteBalance = Temperature)
FP_COLOR_TEMP_MIN = 2500
FP_COLOR_TEMP_MAX = 10000


def validate_color_temp(value: int) -> int:
    """Validate color temperature (2500K to 10000K)"""
    if value < 2500 or value > 10000:
        raise ValueError(f"Color temperature out of range: {value}K (must be 2500K to 10000K)")
    return value


# ==============================================================================
# D185 Profile Parameter Mapping
# ==============================================================================

# Map parameter names to their index in the 29-parameter array
# Based on: docs/fudge/lib/fp/src/fp.h struct FujiProfile
# NOTE: This is for the STANDARD format (628 bytes, offset 0x201)

PROFILE_PARAM_INDEX = {
    'ShootingCondition': 0,
    'FileType': 1,
    'ImageSize': 2,
    'ImageQuality': 3,
    'ExposureBias': 4,
    'DynamicRange': 5,
    'WideDRange': 6,  # D-Range Priority
    'FilmSimulation': 7,  # *** CRITICAL PARAMETER ***
    'BlackImageTone': 8,
    'MonochromaticColor_RG': 9,
    'GrainEffect': 10,
    'GrainEffectSize': 11,
    'ChromeEffect': 12,
    'ColorChromeBlue': 13,
    'SmoothSkinEffect': 14,
    'WBShootCond': 15,
    'WhiteBalance': 16,
    'WBShiftR': 17,  # Red shift -9 to +9
    'WBShiftB': 18,  # Blue shift -9 to +9
    'WBColorTemp': 19,  # 2500K-10000K
    'HighlightTone': 20,  # -4 to +4
    'ShadowTone': 21,  # -4 to +4
    'Color': 22,  # -4 to +4
    'Sharpness': 23,  # -4 to +4
    'NoiseReduction': 24,  # -4 to +4
    'Clarity': 25,  # -5 to +5
    'LensModulationOpt': 26,
    'ColorSpace': 27,
    'HDR': 28,
}

# X-T30 specific parameter mapping (605 bytes, offset 0x1D4)
# The X-T30 uses a different layout with 24 parameters (indices 0-10 are always zero).
# Values are stored in BYTE 1 of the 32-bit value (not the full 32 bits).
#
# IMPORTANT: The X-T30 profile has LIMITED parameter support!
# Only the parameters below are confirmed to work. Other tone parameters
# (Sharpness, Highlight, Shadow, Color/Saturation, Noise Reduction) are
# READ from the RAF file's EXIF metadata, NOT from the d185 profile.
#
# Discovered through systematic reverse engineering and testing.

PROFILE_PARAM_INDEX_XT30 = {
    # Indices 0-10: Always zero (reserved/unused)
    # Indices 11-17: Unknown/untested
    'unknown_11': 11,          # Byte 1: 0x02 (no visible effect in testing)
    'unknown_12': 12,          # Byte 1: 0x07 (no visible effect in testing)

    # CONFIRMED WORKING PARAMETERS:
    'ImageSize': 13,           # Byte 1: 0x01-0x09 (3:2/16:9/1:1 in S/M/L sizes)
    'unknown_14': 14,          # Byte 1: 0x02 (no visible effect)
    'unknown_15': 15,          # Byte 1: 0x00 (no visible effect)
    'unknown_16': 16,          # Byte 1: 0xC8 (no visible effect)
    'unknown_17': 17,          # Byte 1: 0x00 (no visible effect)
    'FilmSimulation': 18,      # Byte 1: 0x01-0x11 (all film modes) ✓ CONFIRMED
    'GrainEffect': 19,         # Byte 1: 0x00=Off, 0x01-0x03=Weak/Strong ✓ CONFIRMED
    'ColorChromeEffect': 20,   # Byte 1: 0x00=Off, 0x01-0x03=Weak/Strong ✓ CONFIRMED
    'unknown_21': 21,          # Byte 1: 0x01 (affects ColorChromeEffect)
    'unknown_22': 22,          # Byte 1: 0x00 (no visible effect)
    'unknown_23': 23,          # Byte 1: 0x02 (no visible effect)

    # NOT IN PROFILE - These are read from RAF EXIF, cannot be modified:
    # - Sharpness
    # - HighlightTone
    # - ShadowTone
    # - Color/Saturation
    # - NoiseReduction
    # - WhiteBalance (may be in profile but not at tested indices)
    # - DynamicRange (may be in profile but not at tested indices)
    # - Quality (may be in profile but not at tested indices)
}


# ==============================================================================
# USB Device IDs
# ==============================================================================

FUJIFILM_USB_VENDOR_ID = 0x04CB  # Fuji Photo Film Co., Ltd

# Known Fujifilm PTP camera PIDs
FUJIFILM_CAMERA_PIDS = [
    0x02E3,  # X-T30
    0x02E5,  # X-T3
    0x02E7,  # X-T4
    # Add more as discovered
]


# ==============================================================================
# Helper Functions
# ==============================================================================

def get_param_index(name: str) -> int:
    """Get profile parameter index by name"""
    if name not in PROFILE_PARAM_INDEX:
        raise ValueError(f"Unknown parameter: {name}")
    return PROFILE_PARAM_INDEX[name]


def get_param_name(index: int) -> str:
    """Get profile parameter name by index"""
    for name, idx in PROFILE_PARAM_INDEX.items():
        if idx == index:
            return name
    raise ValueError(f"Unknown parameter index: {index}")
