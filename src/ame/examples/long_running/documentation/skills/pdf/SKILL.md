# PDF Text Extraction Skill

This skill allows you to extract text from PDF files.

## Description
The skill uses available system tools to extract text from a given PDF file and save it to a text file.

## Requirements
- `pdftotext` (from poppler-utils) OR `gs` (Ghostscript)

## Usage
Run the `extract_text.sh` script with the following arguments:
1. Path to the input PDF file.
2. Path to the output text file.

Example:
```bash
./skills/pdf/extract_text.sh input.pdf output.txt
```
