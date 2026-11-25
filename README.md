# Rawji

Alternative to **Fujifim X-Raw Studio** for Linux users.

<div align="center">
  <img src="https://github.com/user-attachments/assets/c16513c0-7061-46bb-bfc2-a1fbb453349e" alt="Film Simulation Comparison" width="800">
</div>

Convert Fujifilm RAF files to JPEG using your camera's built-in processor via
USB. Apply complete Fujifilm recipes with full control over film simulations,
exposure, tone curve, and more!

- **All Film Simulations** - Provia, Velvia, Acros, Classic Chrome, Eterna, and more
- **Complete Tone Control** - Sharpness, Highlights, Shadows, Color/Saturation
- **Exposure Adjustment** - -2.0 to +3.0 EV in 1/3 stops (honored range)
- **Dynamic Range** - DR100, DR200, DR400
- **White Balance** - Full control including temperature and RGB shift

## GUI

[grawji](https://github.com/p5k369/grawji) is a GTK4 frontend for rawji with
live recipe previews rendered by the camera engine.

## Requirements

- **Camera**: Fujifilm X-series camera with USB RAW conversion support (X-T20, X-T30, X-T3, X-T4, X-H1, X-Pro3, etc.)
- **Python**: 3.7 or newer
- **PyUSB**: USB library for Python
- **Operating System**: Linux (tested), macOS (should work), Windows (untested)

## Camera Setup

1. Turn on your Fujifilm camera
2. Navigate to: **MENU → SET UP → CONNECTION SETTING → USB MODE**
3. Select: **USB RAW CONV./BACKUP RESTORE**
4. Connect camera to computer via USB

> **Note:** the camera only converts RAF files that were **shot by that same camera body**. Feeding a RAF from a different body (or model) is rejected with PTP error `0x2002`.

## Usage

Basic Conversion, uses the camera's default settings from when the photo was
taken:

```bash
rawji input.RAF output.jpg
```

Apply a complete Fujifilm Recipe (Reggie's Portra):

```bash
rawji photo.RAF converted.jpg \
    --film-sim=classicchrome \
    --highlights=-1 \
    --shadows=-1 \
    --color=+2 \
    --sharpness=-2 \
    --nr=-4 \
    --grain=weak \
    --color-chrome=strong \
    --wb-shift-r=+2 \
    --wb-shift-b=-4 \
    --exposure=+0.7
```

### Film Simulation Options

- `provia` - Standard (balanced, neutral)
- `velvia` - Vivid (saturated colors, high contrast)
- `astia` - Soft (gentle colors)
- `classic-chrome` - Muted, vintage look
- `classic-neg` - Classic Negative (film-print look)
- `nostalgic-neg` - Nostalgic Negative (warm, amber look)
- `reala-ace` - Reala Ace (faithful color, hard tonality)
- `pronegh` / `pronegstd` - PRO Neg (for portraits)
- `acros` / `acros-ye` / `acros-r` / `acros-g` - B&W variations
- `monochrome` / `sepia` - Standard B&W and sepia
- `eterna` / `eterna-bleach` - Cinema-like colors

A film simulation must exist on the camera doing the conversion. The
engine renders unknown codes as Provia.

### Batch Conversion

Apply one recipe to many RAFs by passing several inputs and a directory
as output:

```bash
rawji *.RAF converted/ --film-sim=velvia --grain=weak
```

### White Balance Options

- `asshot` - Keep the RAF's own white balance (default when unset)
- `auto` - Automatic white balance
- `daylight` - Daylight
- `shade` - Shade
- `incandescent` - Incandescent / tungsten
- `fluorescent1` / `fluorescent2` / `fluorescent3` - Fluorescent
- `underwater` - Underwater
- `temperature` - Manual color temperature, set the value with `--wb-temp`
- `custom1` / `custom2` / `custom3` - Custom presets measured on the camera

Any preset can be fine-tuned with `--wb-shift-r` and `--wb-shift-b`. The
manual `temperature` mode honors only the camera's Kelvin presets on
older bodies, but any value from 2500 to 10000 K on XProcessor5 bodies.

### Parameter Reference

| Parameter         | Range             | Description                   |
|-------------------|-------------------|-------------------------------|
| `--film-sim`      | See above         | Film simulation mode          |
| `--exposure`      | -2.0 to +3.0      | Exposure bias in EV (1/3 stops) |
| `--highlights`    | -2 to +4          | Highlight tone adjustment     |
| `--shadows`       | -2 to +4          | Shadow tone (X-T30: -2 to +4) |
| `--sharpness`     | -4 to +4          | Sharpness (-4=soft, +4=hard)  |
| `--color`         | -4 to +4          | Color saturation/intensity    |
| `--nr`            | -4 to +4          | Noise reduction               |
| `--clarity`       | -5 to +5          | Clarity (newer bodies only)   |
| `--grain`         | off/weak/strong   | Film grain effect             |
| `--grain-size`    | small/large       | Grain size                    |
| `--color-chrome`  | off/weak/strong   | Color chrome effect           |
| `--color-chrome-blue` | off/weak/strong | Color chrome FX blue        |
| `--smooth-skin`   | off/weak/strong   | Smooth skin effect            |
| `--dynamic-range` | 100/200/400       | Dynamic range setting         |
| `--d-range-priority` | off/weak/strong | D-Range Priority             |
| `--lens-modulation` | on/off           | Lens Modulation Optimizer    |
| `--white-balance` | See above         | White balance mode            |
| `--wb-shift-r`    | -9 to +9          | WB shift, red-cyan axis       |
| `--wb-shift-b`    | -9 to +9          | WB shift, blue-yellow axis    |
| `--wb-temp`       | 2500 to 10000 K   | Kelvin (needs `temperature`)  |
| `--mono-wc`       | ±9 gen4 / ±18 XProc5 | Mono warm-cool (B&W sims)  |
| `--mono-mg`       | ±18 XProc5   | Mono magenta-green (B&W sims)      |
| `--thumbnail`     | flag              | Small fast preview (~40 KB)   |
| `--file-type`     | jpeg/tiff-8bit/tiff-16bit/heif | Output format    |

## Examples

### Kodak Tri-X 400 Recipe
```bash
rawji input.RAF output.jpg \
    --film-sim=acros-ye \
    --exposure=+0.33 \
    --highlights=0 \
    --shadows=+3 \
    --sharpness=+1
```

### Fuji Velvia 50 Recipe
```bash
rawji input.RAF output.jpg \
    --film-sim=velvia \
    --highlights=+1 \
    --shadows=+1 \
    --color=+2 \
    --sharpness=+2
```

### Classic Chrome Portrait
```bash
rawji input.RAF output.jpg \
    --film-sim=classic-chrome \
    --highlights=+1 \
    --shadows=-1 \
    --color=-2 \
    --sharpness=-1
```

### Vintage Film Look with Grain
```bash
rawji input.RAF output.jpg \
    --film-sim=classic-chrome \
    --grain=strong \
    --color-chrome=weak \
    --highlights=+2 \
    --shadows=-1
```

The entire process takes ~2-5 seconds per image.

## Cameras tested

- Fujifilm X-T30
- Fujifilm X100F
- Fujifilm X-T3
- Fujifilm X-E5

## Credits & Acknowledgments

Based on reverse-engineering:
- [petabyt/fudge](https://github.com/petabyt/fudge) - X RAW STUDIO clone
- [libgphoto2](https://github.com/gphoto/libgphoto2) - PTP protocol
- **d185 binary profile format** - 628-byte standard format works across all cameras
- **Tone values use ×10 encoding** - discovered through analysis
- The original X-Raw studio MacOS executable

Special thanks to:
- **petabyt** - For fudge and extensive PTP research
- **gphoto2 team** - For PTP protocol implementation
- **Fujifilm community** - For film simulation recipes
