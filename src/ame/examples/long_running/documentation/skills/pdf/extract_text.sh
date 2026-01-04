#!/bin/bash
# This script extracts text from a PDF file.
# Usage: ./extract_text.sh <input_pdf_file> <output_text_file>

if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Usage: ./extract_text.sh <input_pdf_file> <output_text_file>"
  exit 1
fi

INPUT_PDF="$1"
OUTPUT_TEXT="$2"

# This command assumes pdftotext is installed.
# If pdftotext is not available, this script will fail.
pdftotext "$INPUT_PDF" "$OUTPUT_TEXT"
