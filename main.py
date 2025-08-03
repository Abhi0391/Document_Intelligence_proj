from dotenv import load_dotenv
import os
from openai import OpenAI
import shutil
from PyPDF2 import PdfReader
from docx import Document

#load variables from .env file
load_dotenv()

#Use the API key
client=OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

#Defn destination folders for each category
TEAM_FOLDERS = {
    "Loan Document": "./teams/loan",
    "Credit Card Document": "./teams/credit_card/",
    "Unknown": "./teams/others/"
}

def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def extract_text_from_docx(file_path):
    doc=Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

def classify_document(text):
    prompt = f"""
    Classify the following document into one of the following categories:
    -Loan Document
    -Credit Card Document
    -Unknown (If it doesn't match any of the above)
    Document:
    \"\"\"
    {text[:200]} 
    \"\"\"
    """
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

def route_file(file_path, classification):
    destination_folder = TEAM_FOLDERS.get(classification, TEAM_FOLDERS["Unknown"])
    os.makedirs(destination_folder, exist_ok=True)
    shutil.move(file_path, os.path.join(destination_folder, os.path.basename(file_path)))
    print(f"Moved '{file_path}' to '{destination_folder}'")

def process_file(file_path):
    if file_path.endswith(".pdf"):
        text = extract_text_from_pdf(file_path)
    elif file_path.endswith(".docx"):
        text = extract_text_from_docx(file_path)
    else:
        print(f"Unsupported file format: {file_path}")
        return

    classification = classify_document(text)
    print(f"Classified as {classification}")
    route_file(file_path, classification)

def main():
    input_folder = "./incoming_docs/"
    for file_name in os.listdir(input_folder):
        file_path = os.path.join(input_folder, file_name)
        if os.path.isfile(file_path):
            print(f"processing: {file_path}")
            process_file(file_path)

if __name__=="__main__":
    main()



