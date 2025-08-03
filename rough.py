import os
import pdfplumber
import re

data = {}
filepath = "./incoming_docs/test.pdf"
with pdfplumber.open(filepath) as pdf:
    page = pdf.pages[0]
    text = page.extract_text()
print(text)

# Extract invoice Number
match = re.search(r"INVOICE\s+#\s*(\d+)", text)
if match:
    data["Invoice Number"] = match.group(1)
# Extract Date
match = re.search(r"Date:\s*(\w+\s\d+\,?\s*\d+)", text)
if match:
    data["date"] = match.group(1)
#Extract Balance Due
match = re.search(r"Balance Due:\s*\$(\d+\.\d+)",text)
if match:
    data["Balance Due"] = match.group(1)


#Extract ship mode
print(data)

tables = page.extract_tables()
for row in tables:
    print(row)
