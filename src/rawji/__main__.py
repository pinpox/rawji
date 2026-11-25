#!/usr/bin/env python3
"""
Rawji - Fujifilm RAW Conversion Tool

Convert Fujifilm RAF files using in-camera processing via USB.
Full control over film simulations, exposure, tone curve, and more.

Usage:
    rawji input.RAF output.jpg [OPTIONS]
    rawji *.RAF output-dir/ [OPTIONS]

Author: Based on petabyt/fudge, libgphoto2, and protocol research
License: GPL (due to library dependencies)
"""

import sys
import argparse
from pathlib import Path

from .fuji_usb import FujiCamera
from .fuji_profile import create_profile_from_camera, validate_params
from .fuji_enums import (
    FilmSimulation, WhiteBalance, DynamicRange,
    GrainEffect, GrainEffectSize, ChromeEffect, ColorChromeBlue,
    LensModulationOpt, DRangePriority,
    FileType, CONTAINER_SUFFIX, detect_container, grain_effect_code,
)


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

  # Batch: apply one recipe to many RAFs (output is a directory)
  %(prog)s *.RAF converted/ --film-sim=velvia

Film Simulations:
  provia, velvia, astia, pronegh, pronegstd, monochrome,
  monochrome-ye, monochrome-r, monochrome-g, sepia,
  classic-chrome, acros, acros-ye, acros-r, acros-g,
  eterna, classic-neg, eterna-bleach, nostalgic-neg, reala-ace

Requirements:
  - Camera in "USB RAW CONVERSION" mode (SET UP menu)
  - Camera connected via USB
  - Python 3.7+ with pyusb
        """
    )

    # Required arguments
    parser.add_argument('input', type=Path, nargs='+', help='Input RAF file(s)')
    parser.add_argument('output', type=Path,
                        help='Output JPEG file, or a directory with several inputs')

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
        help='Exposure bias in EV (-2.0 to +3.0, 1/3 stops)'
    )

    # Tone curve
    parser.add_argument(
        '--highlights',
        type=int,
        metavar='N',
        help='Highlight tone (-2 to +4)'
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
    parser.add_argument(
        '--mono-wc',
        type=int,
        metavar='N',
        help='Mono warm-cool, B&W sims (+-9 gen4, +-18 XProcessor5)'
    )
    parser.add_argument(
        '--mono-mg',
        type=int,
        metavar='N',
        help='Mono magenta-green, B&W sims, XProcessor5 only (+-18)'
    )

    # White balance
    parser.add_argument(
        '--white-balance',
        type=str,
        choices=WhiteBalance.names(),
        help='White balance mode'
    )
    parser.add_argument(
        '--thumbnail',
        action='store_true',
        help='Render a preview and download only its thumbnail'
    )
    parser.add_argument(
        '--file-type',
        type=str,
        choices=FileType.names(),
        help='Output format (jpeg, tiff-8bit, tiff-16bit, heif)'
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

    # Film effects
    parser.add_argument(
        '--grain',
        type=str,
        choices=GrainEffect.names(),
        help='Film grain effect (off, weak, strong)'
    )
    parser.add_argument(
        '--grain-size',
        type=str,
        choices=GrainEffectSize.names(),
        help='Film grain size effect (small, large)'
    )    
    parser.add_argument(
        '--color-chrome',
        type=str,
        choices=ChromeEffect.names(),
        help='Color chrome effect (off, weak, strong)'
    )
    parser.add_argument(
        '--color-chrome-blue',
        type=str,
        choices=ColorChromeBlue.names(),
        help='Color chrome FX blue (off, weak, strong)'
    )
    parser.add_argument(
        '--smooth-skin',
        type=str,
        choices=ChromeEffect.names(),
        help='Smooth skin effect (off, weak, strong)'
    )
    parser.add_argument(
        '--d-range-priority',
        type=str,
        choices=DRangePriority.names(),
        help='D-Range Priority (off, weak, strong). Weak and strong '
             'override highlights, shadows and dynamic range'
    )
    parser.add_argument(
        '--lens-modulation',
        type=str,
        choices=LensModulationOpt.names(),
        help='Lens Modulation Optimizer (on, off)'
    )

    # Debug options
    parser.add_argument(
        '--dump-profile',
        action='store_true',
        help='Dump camera profile and exit (no conversion)'
    )

    args = parser.parse_args()

    # Validate input files exist
    for input_path in args.input:
        if not input_path.exists():
            print(f"[-] Input file not found: {input_path}")
            return 1

        if not input_path.suffix.upper() == '.RAF':
            print(f"[!] Warning: Input file doesn't have .RAF extension: {input_path}")

    file_type = FileType.from_name(args.file_type) if args.file_type else None
    if file_type is not None and args.thumbnail:
        print("[!] --file-type is ignored with --thumbnail")
        file_type = None

    if file_type is FileType.HEIF:
        suffix = CONTAINER_SUFFIX['heif']
    elif file_type in (FileType.TIFF_8BIT, FileType.TIFF_16BIT):
        suffix = CONTAINER_SUFFIX['tiff']
    else:
        suffix = CONTAINER_SUFFIX['jpeg']

    batch = len(args.input) > 1
    name_outputs = batch or args.output.is_dir()
    if name_outputs:
        outputs = [args.output / (p.stem + suffix) for p in args.input]
    else:
        outputs = [args.output]

    # Print header
    print("=" * 70)
    print("Rawji - Fujifilm RAW Conversion Tool")
    print("=" * 70)
    if batch:
        print(f"Input:  {len(args.input)} RAF files")
    else:
        print(f"Input:  {args.input[0]}")
    if not args.dump_profile:
        print(f"Output: {args.output}")
    print("=" * 70)

    # Connect to camera
    camera = FujiCamera()
    if not camera.connect():
        return 1

    try:
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

        if args.clarity is not None:
            changes['Clarity'] = args.clarity
            print(f"Clarity: {args.clarity:+d}")

        # Monochromatic Color
        if args.mono_wc is not None:
            changes['BlackImageTone'] = args.mono_wc
            print(f"Mono WC: {args.mono_wc:+d}")

        if args.mono_mg is not None:
            changes['MonochromaticColorRG'] = args.mono_mg
            print(f"Mono MG: {args.mono_mg:+d}")

        # White balance
        if args.white_balance:
            wb = WhiteBalance.from_name(args.white_balance)
            changes['WhiteBalance'] = int(wb)
            print(f"White Balance: {args.white_balance}")

        # WB shift
        if args.wb_shift_r is not None:
            changes['WBShiftR'] = args.wb_shift_r
            print(f"WB Shift R: {args.wb_shift_r:+d}")

        if args.wb_shift_b is not None:
            changes['WBShiftB'] = args.wb_shift_b
            print(f"WB Shift B: {args.wb_shift_b:+d}")

        # Dynamic range
        if args.dynamic_range:
            dr = DynamicRange.from_percent(args.dynamic_range)
            changes['DynamicRange'] = int(dr)
            print(f"Dynamic Range: DR{args.dynamic_range}")

        # Film effects
        if args.grain:
            grain = GrainEffect.from_name(args.grain)
            size = GrainEffectSize.from_name(args.grain_size or 'small')
            # Effect and size share one profile slot, see grain_effect_code.
            changes['GrainEffect'] = grain_effect_code(grain, size)
            print(f"Grain Effect: {args.grain} ({args.grain_size or 'small'})")

        if args.color_chrome:
            chrome = ChromeEffect.from_name(args.color_chrome)
            changes['ColorChromeEffect'] = int(chrome)
            print(f"Color Chrome Effect: {args.color_chrome}")

        if args.color_chrome_blue:
            chrome_blue = ColorChromeBlue.from_name(args.color_chrome_blue)
            changes['ColorChromeBlue'] = int(chrome_blue)
            print(f"Color Chrome FX Blue: {args.color_chrome_blue}")

        if args.smooth_skin:
            skin = ChromeEffect.from_name(args.smooth_skin)
            changes['SmoothSkinEffect'] = int(skin)
            print(f"Smooth Skin Effect: {args.smooth_skin}")

        if args.d_range_priority:
            priority = DRangePriority.from_name(args.d_range_priority)
            changes['WideDRange'] = int(priority)
            print(f"D-Range Priority: {args.d_range_priority}")

        if args.lens_modulation:
            lens = LensModulationOpt.from_name(args.lens_modulation)
            changes['LensModulationOpt'] = int(lens)
            print(f"Lens Modulation Optimizer: {args.lens_modulation}")

        if file_type is not None:
            changes['FileType'] = int(file_type)
            print(f"File Type: {args.file_type}")

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
                file_type=changes.get('FileType'),
            )
        except ValueError as e:
            print(f"[-] Parameter validation failed: {e}")
            return 1

        if batch:
            args.output.mkdir(parents=True, exist_ok=True)

        total_bytes = 0
        for index, (input_path, output_path) in enumerate(zip(args.input, outputs)):
            if batch:
                print(f"\n--- [{index + 1}/{len(args.input)}] {input_path.name} ---")

            # Send RAF file first, the camera needs a RAF loaded before it can return a valid profile
            print("[*] Sending RAF file to camera...")
            camera.send_raf(str(input_path))

            # Get current profile from camera
            original_profile = camera.get_profile()
            print(f"[+] Camera returned {len(original_profile)}-byte profile")

            # Create 628-byte standard format profile
            # This works for ALL cameras including X-T30!
            print("[*] Creating 628-byte standard format profile...")
            modified_profile = create_profile_from_camera(original_profile, changes)
            print(f"[+] Profile created: {len(modified_profile)} bytes")

            # Send profile
            print("[*] Sending profile to camera...")
            camera.set_profile(modified_profile)

            # Trigger conversion
            camera.trigger_conversion(full_resolution=not args.thumbnail)

            # Wait for result
            jpeg_data = camera.wait_for_result(
                timeout=30, thumbnail=args.thumbnail)
            if not jpeg_data:
                # A timeout usually means the camera has wedged. Retrying
                # only makes it worse. Power-cycle before the next attempt.
                print(f"\n[-] Conversion timed out after {index} file(s); "
                      "power-cycle the camera before retrying")
                return 1

            container = detect_container(jpeg_data)
            if container is None:
                print("[!] Warning: downloaded data matches no known format")
            elif CONTAINER_SUFFIX[container] != suffix:
                print(f"[!] Camera returned {container.upper()}, not the "
                      f"requested {args.file_type}: this body does not "
                      "support that format")
                if name_outputs:
                    output_path = output_path.with_suffix(
                        CONTAINER_SUFFIX[container]
                    )

            # Save the converted image
            print(f"[*] Saving to {output_path}...")
            output_path.write_bytes(jpeg_data)
            total_bytes += len(jpeg_data)

        # Success!
        print("\n" + "=" * 70)
        if batch:
            print(f"SUCCESS! Converted {len(args.input)} RAF files -> {args.output}")
        else:
            print(f"SUCCESS! Converted {args.input[0].name} -> {outputs[0].name}")
        print(f"Output size: {total_bytes} bytes ({total_bytes / 1024 / 1024:.2f} MB)")
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
