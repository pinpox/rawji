#!/usr/bin/env bash
# Convert example.RAF with all film simulations

set -e

INPUT="example.RAF"
OUTPUT_DIR="output"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# List of all film simulations (matching argparse choices format)
SIMS=(
    "provia"
    "velvia"
    "astia"
    "proneghi"
    "pronegstd"
    "monochrome"
    "monochromeye"
    "monochromer"
    "monochromeg"
    "sepia"
    "classicchrome"
    "acros"
    "acrosye"
    "acrosr"
    "acrosg"
    "eterna"
    "eternableach"
)

echo "======================================================================="
echo "Converting $INPUT with all film simulations"
echo "======================================================================="
echo ""

# Convert with each simulation
for sim in "${SIMS[@]}"; do
    output_file="$OUTPUT_DIR/${sim}.jpg"
    echo "Converting with $sim..."
    nix run . -- "$INPUT" "$output_file" --film-sim="$sim"
    echo ""
done

echo "======================================================================="
echo "All conversions complete! Files saved in $OUTPUT_DIR/"
echo "======================================================================="
ls -lh "$OUTPUT_DIR"
