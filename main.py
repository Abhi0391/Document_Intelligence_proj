from dotenv import load_dotenv
import os
from openai import OpenAI, azure_endpoint
import shutil
from PyPDF2 import PdfReader
from docx import Document
import pdfplumber
from openai import AzureOpenAI
import re
from datetime import datetime

#from loan_metadata import AZURE_DEPLOYMENT_LLM

#load variables from .env file
load_dotenv()

#Use the API key
client=OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

#Azure OpenAI Configuration
#AZURE_ENDPOINT = "https://kaarthi-poc1.openai.azure.com/"
#AZURE_API_KEY = os.getenv("API_KEY")
#AZURE_DEPLOYMENT_EMBEDDING = "kaarthipoc-text-embedding-ada-002"
#AZURE_DEPLOYMENT_LLM = "Kaarthipocgpt4omini"
#AZURE_API_VERSION = "2024-08-01-preview"

#Create Azure OpenAI Client
#client = AzureOpenAI(
#api_key = AZURE_API_KEY,
#api_version = AZURE_API_VERSION,
#azure_endpoint= AZURE_ENDPOINT
#)

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
    You are a document classifier.
    Task:
    Read the following document text and decide which single category it belongs to.
    Valid categories:
    1. Loan Document
    2. Others
    
    Rules: 
    - Output only the category name exactly as written above.
    - Do not include any explanation or extra text. 
    \"\"\"
    {text[:200]} 
    \"\"\"
    """
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    print(response.choices[0].message.content.strip())
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
    #extract metadata if it's a loan document
    if classification == "Loan Document":
        metadata = extract_loan_metadata(file_path)
        print("Loan Metadata:", metadata)
        if validate_metadata(metadata):
            print("Metadata validated")
        else:
            print("Metadata failed validation")
    route_file(file_path, classification)



def extract_loan_metadata(file_path):
    """Extract loan metadata using regex + Azure OpenAI """
    data = {}
    #Regex patterns for structured loan details
    patterns = {
        "Loan Number": r"Loan\s*Number[:\s]*([A-Za-z0-9\-]+)",
        "Borrower Name": r"Borrower[:\s]*([A-Za-z ,.'-]+)",
        "Loan Amount": r"Loan\s*Amount[:\s]*\$?([\d,]+\.\d{2})",
        "Interest Rate":r"Interest\s*Rate[:\s]*([\d\.]+%)",
        "Loan Date":r"(Loan\s*Date|Start\s*Date)[:\s]*([\w\s,/-]+)",
        "Due Date":r"(Due\s*Date|Maturity\s*Date)[:\s]*([\w\s,/-]+)",
        "Bank":r"(Bank|Issuer)[:\s]*([A-Za-z &]+)"
    }
    with pdfplumber.open(file_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        print(text)

    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data[key] = match.group(1).strip()
        else:
            data[key] = None

    return data

def validate_metadata(data):
    try:
        required = ["Loan Number", "Borrower Name", "Loan Amount", "Interest Rate", "Loan Date","Due Date","Bank"]
        for key in required:
            if key not in data or not data[key].strip():
                print(f"Missing or empty: {key}")
                #return False

        #Loan Amount: numeric
        if not re.fullmatch(r"[\d,]+(\.\d{1,2})?", data["Loan Amount"]):
            print("Invalid loan amount format")
            #return False

        if not re.fullmatch(r"\d{1,2}(\.\d+)?%",data["Interest Rate"]):
            print("Invalid Interest Rate format")
            #return False

        for date_key in ["Loan Date", "Due Date"]:
            if not _is_valid_date(data[date_key]):
                print(f"Invalid date for {date_key}")
                #return False

        return True
    except Exception as e:
        print(f"Validation error: {e}")
        return True



def main():
    input_folder = "./incoming_docs/"
    for file_name in os.listdir(input_folder):
        file_path = os.path.join(input_folder, file_name)
        if os.path.isfile(file_path):
            print(f"processing: {file_path}")
            process_file(file_path)

if __name__=="__main__":
    main()



