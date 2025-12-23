#!/usr/bin/env python3
"""
Rawji - Fujifilm RAW Conversion Tool

Convert Fujifilm RAF files using in-camera processing via USB.
Full control over film simulations, exposure, tone curve, and more.

Usage:
    rawji input.RAF output.jpg [OPTIONS]

Author: Based on petabyt/fudge, libgphoto2, and protocol research
License: GPL (due to library dependencies)
"""

import sys
import argparse
from pathlib import Path

from .fuji_usb import FujiCamera
from .fuji_profile import create_profile_from_camera, validate_params
from .fuji_enums import FilmSimulation, WhiteBalance, DynamicRange


def main():
    parser = argparse.ArgumentParser(
        description='Fujifilm RAW Conversion Tool - Convert RAF files using in-camera processing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic conversion (uses camera defaults)
  %(prog)s input.RAF output.jpg

  # With film simulation
  %(prog)s input.RAF output.jpg --film-sim=velvia

  # Full control
  %(prog)s input.RAF output.jpg \\
      --film-sim=classic-chrome \\
      --exposure=+0.7 \\
      --highlights=+1 \\
      --shadows=-2 \\
      --sharpness=+2 \\
      --color=-1 \\
      --white-balance=shade \\
      --dynamic-range=200

Film Simulations:
  provia, velvia, astia, pronegh, pronegstd, monochrome,
  monochrome-ye, monochrome-r, monochrome-g, sepia,
  classic-chrome, acros, acros-ye, acros-r, acros-g,
  eterna, eterna-bleach

Requirements:
  - Camera in "USB RAW CONVERSION" mode (SET UP menu)
  - Camera connected via USB
  - Python 3.7+ with pyusb
        """
    )

    # Required arguments
    parser.add_argument('input', type=Path, help='Input RAF file')
    parser.add_argument('output', type=Path, help='Output JPEG file')

    # Film simulation
    parser.add_argument(
        '--film-sim',
        type=str,
        choices=FilmSimulation.names(),
        help='Film simulation mode'
    )

    # Exposure
    parser.add_argument(
        '--exposure',
        type=float,
        metavar='EV',
        help='Exposure bias in EV (-5.0 to +5.0)'
    )

    # Tone curve
    parser.add_argument(
        '--highlights',
        type=int,
        metavar='N',
        help='Highlight tone (-4 to +4)'
    )
    parser.add_argument(
        '--shadows',
        type=int,
        metavar='N',
        help='Shadow tone (-4 to +4)'
    )

    # Color and sharpness
    parser.add_argument(
        '--color',
        type=int,
        metavar='N',
        help='Color saturation (-4 to +4)'
    )
    parser.add_argument(
        '--sharpness',
        type=int,
        metavar='N',
        help='Sharpness (-4 to +4)'
    )
    parser.add_argument(
        '--nr',
        type=int,
        metavar='N',
        help='Noise reduction (-4 to +4)'
    )
    parser.add_argument(
        '--clarity',
        type=int,
        metavar='N',
        help='Clarity (-5 to +5)'
    )

    # White balance
    parser.add_argument(
        '--white-balance',
        type=str,
        choices=WhiteBalance.names(),
        help='White balance mode'
    )
    parser.add_argument(
        '--wb-shift-r',
        type=int,
        metavar='N',
        help='WB red shift (-9 to +9)'
    )
    parser.add_argument(
        '--wb-shift-b',
        type=int,
        metavar='N',
        help='WB blue shift (-9 to +9)'
    )
    parser.add_argument(
        '--wb-temp',
        type=int,
        metavar='K',
        help='Color temperature in Kelvin (2500-10000, requires --white-balance=temperature)'
    )

    # Dynamic range
    parser.add_argument(
        '--dynamic-range',
        type=int,
        choices=[100, 200, 400],
        help='Dynamic range (100, 200, or 400)'
    )

    # Removed grain/chrome/quality/size options for now - focus on core parameters

    # Debug options
    parser.add_argument(
        '--dump-profile',
        action='store_true',
        help='Dump camera profile and exit (no conversion)'
    )

    args = parser.parse_args()

    # Validate input file exists
    if not args.input.exists():
        print(f"[-] Input file not found: {args.input}")
        return 1

    if not args.input.suffix.upper() == '.RAF':
        print(f"[!] Warning: Input file doesn't have .RAF extension: {args.input}")

    # Print header
    print("=" * 70)
    print("Rawji - Fujifilm RAW Conversion Tool")
    print("=" * 70)
    print(f"Input:  {args.input}")
    if not args.dump_profile:
        print(f"Output: {args.output}")
    print("=" * 70)

    # Connect to camera
    camera = FujiCamera()
    if not camera.connect():
        return 1

    try:
        # Send RAF file FIRST
        # The camera needs a RAF loaded before it can return a valid profile
        print("[*] Sending RAF file to camera...")
        camera.send_raf(str(args.input))

        # Get current profile from camera (we won't use it, just for verification)
        original_profile = camera.get_profile()
        print(f"[+] Camera returned {len(original_profile)}-byte profile")

        # Build parameter changes dictionary
        changes = {}

        # Film simulation
        if args.film_sim:
            film_sim = FilmSimulation.from_name(args.film_sim)
            changes['FilmSimulation'] = int(film_sim)
            print(f"Film Simulation: {args.film_sim} (0x{film_sim:02X})")

        # Exposure
        if args.exposure is not None:
            changes['ExposureBias'] = int(args.exposure * 1000)  # Convert to millistops
            print(f"Exposure Bias: {args.exposure:+.2f} EV")

        # Tone curve (user provides simple values, encoding handled in create_profile)
        if args.highlights is not None:
            changes['HighlightTone'] = args.highlights
            print(f"Highlight Tone: {args.highlights:+d}")

        if args.shadows is not None:
            changes['ShadowTone'] = args.shadows
            print(f"Shadow Tone: {args.shadows:+d}")

        # Color/sharpness
        if args.color is not None:
            changes['Color'] = args.color
            print(f"Color: {args.color:+d}")

        if args.sharpness is not None:
            changes['Sharpness'] = args.sharpness
            print(f"Sharpness: {args.sharpness:+d}")

        if args.nr is not None:
            changes['NoiseReduction'] = args.nr
            print(f"Noise Reduction: {args.nr:+d}")

        # White balance
        if args.white_balance:
            wb = WhiteBalance.from_name(args.white_balance)
            changes['WhiteBalance'] = int(wb)
            print(f"White Balance: {args.white_balance}")

        # Dynamic range
        if args.dynamic_range:
            dr = DynamicRange.from_percent(args.dynamic_range)
            changes['DynamicRange'] = int(dr)
            print(f"Dynamic Range: DR{args.dynamic_range}")

        print("=" * 70)

        # Validate parameters
        try:
            validate_params(
                film_sim=changes.get('FilmSimulation'),
                exposure=args.exposure,
                highlights=changes.get('HighlightTone'),
                shadows=changes.get('ShadowTone'),
                color=changes.get('Color'),
                sharpness=changes.get('Sharpness'),
            )
        except ValueError as e:
            print(f"[-] Parameter validation failed: {e}")
            return 1

        # Create 628-byte standard format profile
        # This works for ALL cameras including X-T30!
        print("\n[*] Creating 628-byte standard format profile...")
        modified_profile = create_profile_from_camera(original_profile, changes)
        print(f"[+] Profile created: {len(modified_profile)} bytes")

        # Send profile
        print("[*] Sending profile to camera...")
        camera.set_profile(modified_profile)

        # Trigger conversion
        camera.trigger_conversion()

        # Wait for result
        jpeg_data = camera.wait_for_result(timeout=30)

        # Verify it's actually a JPEG
        if not jpeg_data.startswith(b'\xFF\xD8\xFF'):
            print("[!] Warning: Downloaded data doesn't appear to be a JPEG")

        # Save JPEG
        print(f"[*] Saving to {args.output}...")
        args.output.write_bytes(jpeg_data)

        # Success!
        print("\n" + "=" * 70)
        print(f"SUCCESS! Converted {args.input.name} -> {args.output.name}")
        print(f"Output size: {len(jpeg_data)} bytes ({len(jpeg_data) / 1024 / 1024:.2f} MB)")
        print("=" * 70)

        return 0

    except KeyboardInterrupt:
        print("\n\n[!] Interrupted by user")
        return 1

    except Exception as e:
        print(f"\n[-] Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        camera.disconnect()


if __name__ == '__main__':
    sys.exit(main())
