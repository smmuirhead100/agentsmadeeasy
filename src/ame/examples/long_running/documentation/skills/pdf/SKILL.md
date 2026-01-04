This is the main skill file for the PDF skill.

# Overview
This skill is used to extract text from PDF files.

# Usage
To use this skill, you need to provide a PDF file.

# Example
```python
from ame.examples.long_running.documentation.skills.pdf import PDFSkill
pdf_skill = PDFSkill()
pdf_skill.extract_text("example.pdf")
```