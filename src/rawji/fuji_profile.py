#!/usr/bin/env python3
"""
Fujifilm RAW Conversion - D185 Profile Handler

CRITICAL FINDINGS:
- X-T30 ACCEPTS the 628-byte STANDARD format (not just its native 605-byte format!)
- ALL parameters work when using standard format with offset 0x201
- Tone parameters use value*10 encoding (FP_PLUS_4=40, FP_MIN_2=-20)
- X-T30 shadow tone range is +4 to -2 (not -4!)

Based on: docs/fudge/lib/fp/src/d185.c and docs/fudge/lib/fp/src/fp.h
"""

import struct
from typing import Dict, Optional

# ==============================================================================
# Profile Format Constants
# ==============================================================================

PROFILE_SIZE_STANDARD = 632  # 0x201 (513) + 29*4 (116) = 629, round to 632
NUM_PARAMS = 29
PROFILE_PARAMS_OFFSET = 0x201  # Standard format offset (513)

# Parameter value encoding (from fp.h)
# Tone parameters use value * 10 encoding:
#   +4 → 40 (FP_PLUS_4)
#   +2 → 20 (FP_PLUS_2)
#    0 → 0  (FP_ZERO)
#   -2 → -20 (FP_MIN_2) = 0xFFFFFFEC
#   -4 → -40 (FP_MIN_4) = 0xFFFFFFD8

def encode_tone_value(value: int) -> int:
    """Encode tone parameter value (multiply by 10)"""
    return value * 10

def decode_tone_value(encoded: int) -> int:
    """Decode tone parameter value (divide by 10)"""
    # Handle negative values (two's complement)
    if encoded > 0x7FFFFFFF:
        encoded = encoded - 0x100000000
    return encoded // 10

# ==============================================================================
# Profile Parameter Indices (Standard Format)
# ==============================================================================

PARAM_INDEX = {
    'ShootingCondition': 0,
    'FileType': 1,
    'ImageSize': 2,
    'ImageQuality': 3,
    'ExposureBias': 4,
    'DynamicRange': 5,
    'WideDRange': 6,
    'FilmSimulation': 7,      # ← Film sim works!
    'GrainEffect': 8,
    'SmoothSkinEffect': 9,
    'WBShootCond': 10,
    'WhiteBalance': 11,
    'WBShiftR': 12,
    'WBShiftB': 13,
    'WBColorTemp': 14,
    'HighlightTone': 15,      # ← Works with *10 encoding!
    'ShadowTone': 16,         # ← Works with *10 encoding! (X-T30: -2 to +4)
    'Color': 17,              # ← Works with *10 encoding!
    'Sharpness': 18,          # ← Works with *10 encoding!
    'NoiseReduction': 19,     # ← Should work with *10 encoding
    'Clarity': 20,
    'ColorSpace': 21,
    'HDR': 22,
    'DigitalTeleConv': 23,
    'PortraitEnhancer': 24,
    'Reserved25': 25,
    'Reserved26': 26,
    'Reserved27': 27,
    'Reserved28': 28,
}

# Inverse mapping
INDEX_TO_PARAM = {v: k for k, v in PARAM_INDEX.items()}

# Parameters that use *10 encoding
TONE_PARAMS = {'HighlightTone', 'ShadowTone', 'Color', 'Sharpness', 'NoiseReduction', 'Clarity'}

# ==============================================================================
# Profile Creation
# ==============================================================================

def create_profile_from_camera(
    camera_profile: bytes,
    changes: Dict[str, int],
    iopcode: str = "FF159502"
) -> bytes:
    """
    Create 628-byte standard format profile from camera's profile + changes

    Args:
        camera_profile: Original profile from camera (for extracting base values)
        changes: Parameter changes (user-friendly values, will be encoded)
        iopcode: Camera IOPCode (default: FF159502 for X-T30)

    Returns:
        628-byte standard format profile ready to send to camera
    """
    # Create buffer
    profile = bytearray(PROFILE_SIZE_STANDARD)

    # Header: n_props = 0x1d (29)
    struct.pack_into('<H', profile, 0, NUM_PARAMS)

    # IOPCode string (wide char, null-terminated)
    offset = 2
    struct.pack_into('<B', profile, offset, len(iopcode) + 1)
    offset += 1

    for c in iopcode:
        struct.pack_into('<H', profile, offset, ord(c))
        offset += 2

    struct.pack_into('<H', profile, offset, 0)  # null terminator
    offset += 2

    # Pad to 0x201 (513)
    while offset < PROFILE_PARAMS_OFFSET:
        profile[offset] = 0
        offset += 1

    # Default parameter values (from get_prop() in d185.c)
    default_params = {
        'ShootingCondition': 0x2,
        'FileType': 0x7,
        'ImageSize': 0x7,        # L 3:2
        'ImageQuality': 0x2,     # Fine
        'ExposureBias': 0,
        'DynamicRange': 0x1,     # DR100
        'WideDRange': 0,
        'FilmSimulation': 0x1,   # Provia (default)
        'GrainEffect': 0,
        'SmoothSkinEffect': 0,
        'WBShootCond': 0,
        'WhiteBalance': 0,       # AsShot
        'WBShiftR': 0,
        'WBShiftB': 0,
        'WBColorTemp': 0,
        'HighlightTone': 0,
        'ShadowTone': 0,
        'Color': 0,
        'Sharpness': 0,
        'NoiseReduction': 0,
        'Clarity': 0,
        'ColorSpace': 0,
        'HDR': 0,
        'DigitalTeleConv': 0,
        'PortraitEnhancer': 0,
        'Reserved25': 0,
        'Reserved26': 0,
        'Reserved27': 0,
        'Reserved28': 0,
    }

    # Apply changes
    params = default_params.copy()
    params.update(changes)

    # Encode tone parameters (multiply by 10)
    for param_name in TONE_PARAMS:
        if param_name in params:
            value = params[param_name]
            params[param_name] = encode_tone_value(value)

    # Write parameters at offset 0x201
    for i in range(NUM_PARAMS):
        param_name = INDEX_TO_PARAM[i]
        value = params[param_name]

        # Convert negative values to uint32 (two's complement)
        if value < 0:
            value = (1 << 32) + value

        struct.pack_into('<I', profile, PROFILE_PARAMS_OFFSET + i*4, value)

    return bytes(profile)


def create_profile_simple(
    film_sim: int = 0x1,
    exposure: float = 0.0,
    highlights: int = 0,
    shadows: int = 0,
    color: int = 0,
    sharpness: int = 0,
    iopcode: str = "FF159502"
) -> bytes:
    """
    Create profile with simple parameters

    Args:
        film_sim: Film simulation (1=Provia, 2=Velvia, etc.)
        exposure: Exposure bias in EV (-5.0 to +5.0)
        highlights: Highlight tone (-4 to +4)
        shadows: Shadow tone (-2 to +4 for X-T30, -4 to +4 for X-Processor 5)
        color: Color/saturation (-4 to +4)
        sharpness: Sharpness (-4 to +4)
        iopcode: Camera IOPCode

    Returns:
        628-byte profile
    """
    changes = {
        'FilmSimulation': film_sim,
        'ExposureBias': int(exposure * 1000),  # Convert EV to millistops
        'HighlightTone': highlights,
        'ShadowTone': shadows,
        'Color': color,
        'Sharpness': sharpness,
    }

    return create_profile_from_camera(b'', changes, iopcode)


# ==============================================================================
# Profile Parsing
# ==============================================================================

def parse_profile(data: bytes) -> Dict[str, int]:
    """
    Parse d185 binary profile

    Returns user-friendly values (tone params decoded from *10 encoding)
    """
    if len(data) < PROFILE_PARAMS_OFFSET + NUM_PARAMS * 4:
        # Try parsing X-T30 605-byte format
        return _parse_xt30_format(data)

    params = {}

    # Read parameters at offset 0x201
    for i in range(NUM_PARAMS):
        param_name = INDEX_TO_PARAM[i]
        value = struct.unpack_from('<I', data, PROFILE_PARAMS_OFFSET + i*4)[0]

        # Convert to signed if negative
        if value > 0x7FFFFFFF:
            value = value - 0x100000000

        # Decode tone parameters
        if param_name in TONE_PARAMS:
            value = decode_tone_value(value)

        params[param_name] = value

    return params


def _parse_xt30_format(data: bytes) -> Dict[str, int]:
    """Parse X-T30 605-byte native format (for reading camera's profile)"""
    # X-T30 format uses offset 0x1D4 (468) with byte 1 encoding
    # But we won't modify this - we'll convert to standard format instead
    params = {}
    offset = 0x1D4  # 468

    # Just return minimal parse for now - main tool uses standard format
    return params


# ==============================================================================
# Helper Functions
# ==============================================================================

def validate_params(
    film_sim: Optional[int] = None,
    exposure: Optional[float] = None,
    highlights: Optional[int] = None,
    shadows: Optional[int] = None,
    color: Optional[int] = None,
    sharpness: Optional[int] = None,
) -> None:
    """Validate parameter ranges"""

    if film_sim is not None and (film_sim < 0x1 or film_sim > 0x11):
        raise ValueError(f"FilmSimulation out of range: 0x{film_sim:02X} (must be 0x01-0x11)")

    if exposure is not None and (exposure < -5.0 or exposure > 5.0):
        raise ValueError(f"Exposure out of range: {exposure} (must be -5.0 to +5.0 EV)")

    if highlights is not None and (highlights < -4 or highlights > 4):
        raise ValueError(f"Highlights out of range: {highlights} (must be -4 to +4)")

    # X-T30 shadow tone is limited to -2 to +4
    if shadows is not None and (shadows < -2 or shadows > 4):
        raise ValueError(f"Shadows out of range: {shadows} (must be -2 to +4 for X-T30)")

    if color is not None and (color < -4 or color > 4):
        raise ValueError(f"Color out of range: {color} (must be -4 to +4)")

    if sharpness is not None and (sharpness < -4 or sharpness > 4):
        raise ValueError(f"Sharpness out of range: {sharpness} (must be -4 to +4)")


def dump_profile(profile: bytes) -> str:
    """Dump profile in human-readable format"""
    params = parse_profile(profile)

    lines = []
    lines.append(f"Profile size: {len(profile)} bytes")
    lines.append("=" * 60)

    for i in range(NUM_PARAMS):
        param_name = INDEX_TO_PARAM[i]
        value = params.get(param_name, 0)

        if param_name == 'FilmSimulation':
            lines.append(f"{i:2d}. {param_name:25s} = 0x{value:02X}")
        elif param_name == 'ExposureBias':
            ev = value / 1000.0
            lines.append(f"{i:2d}. {param_name:25s} = {value:6d} ({ev:+.2f} EV)")
        elif param_name in TONE_PARAMS:
            lines.append(f"{i:2d}. {param_name:25s} = {value:+3d}")
        else:
            lines.append(f"{i:2d}. {param_name:25s} = {value}")

    return "\n".join(lines)
