#!/bin/bash
# This script extracts text from a PDF file.
# Usage: ./extract_text.sh <input_pdf_file> <output_text_file>

if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Usage: ./extract_text.sh <input_pdf_file> <output_text_file>"
  exit 1
fi

INPUT_PDF="$1"
OUTPUT_TEXT="$2"

if command -v pdftotext &> /dev/null; then
    pdftotext "$INPUT_PDF" "$OUTPUT_TEXT"
elif command -v gs &> /dev/null; then
    gs -sDEVICE=txtwrite -o "$OUTPUT_TEXT" "$INPUT_PDF"
else
    echo "Error: Neither pdftotext nor gs found."
    exit 1
fi
