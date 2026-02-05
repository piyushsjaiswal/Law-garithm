import os
import time
import requests
from dotenv import load_dotenv

from PIL import Image
import pytesseract
import pypdf

# Load environment variables
load_dotenv()
# Try loading specific env file if it exists, otherwise ignore
load_dotenv("sih.env")

API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"

API_KEY = os.getenv("API_KEY")

TESSERACT_CMD = os.getenv("TESSERACT_PATH", r"D:\OCR\tesseract.exe")
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

PROMPT_TEMPLATES = {
    "simple_summarization": {
        "prompt": "Summarize the following legal document into 3-5 key points. Use simple, clear language that a non-lawyer can understand.\n\nDOCUMENT:\n{document_text}",
        "system_instruction": "You are a helpful assistant for legal document analysis."
    },
    "structured_extraction": {
        "prompt": "Extract and summarize the following information from the document provided:\n\nDocument Type: (e.g., FIR, Court Order, Legal Notice)\n\nParties Involved: (List all names and their roles, like 'Complainant,' 'Accused,' or 'Plaintiff')\n\nCore Issue: (What is the main problem or subject of the document?)\n\nDate of Event: (The date the incident or event occurred)\n\nOutcome/Action: (What is the result or what action is being requested?)\n\nDOCUMENT:\n{document_text}",
        "system_instruction": "You are a legal data extraction tool. Your task is to provide structured information from legal texts."
    },
    "fir_summary": {
        "prompt": "You are a police clerk writing a public summary of an FIR. Summarize the following FIR, focusing on:\n\nFIR Number and Date:\n\nPolice Station and District:\n\nComplainant: (Name, age, and a one-sentence summary of their complaint)\n\nIncident Details: (What happened, when, and where? Be brief and factual)\n\nStolen/Lost Items: (List any items mentioned as lost or stolen)\n\nFIR TEXT:\n{document_text}",
        "system_instruction": "You are an expert in summarizing police reports for public consumption."
    },
    "court_order_summary": {
        "prompt": "Act as a legal paralegal providing a summary of a court order for a client. Summarize the following order by answering these questions:\n\nCase Name/Parties: (e.g., State vs. Accused)\n\nType of Order: (e.g., Bail Order, Divorce Decree, etc.)\n\nCourt and Judge: (The name of the court and the judge)\n\nThe Court's Decision: (What was the final ruling? Use simple terms like 'bail granted' or 'case dismissed')\n\nKey Conditions or Requirements: (What does the order require the parties to do?)\n\nCOURT ORDER TEXT:\n{document_text}",
        "system_instruction": "You are a legal paralegal who translates complex court orders into simple, clear summaries for clients."
    },
    "legal_notice_summary": {
        "prompt": "You are a legal advisor explaining a legal notice to your client. Summarize the content below, explaining:\n\nWho sent the notice:\n\nWho the notice is for:\n\nReason for the notice: (Why was it sent?)\n\nThe Demand: (What is being requested or demanded?)\n\nThe Deadline: (When must the action be taken by?)\n\nLEGAL NOTICE TEXT:\n{document_text}",
        "system_instruction": "You are an experienced legal advisor who simplifies legal documents for clients."
    },
    "chat_with_document": {
        "prompt": "You are a helpful assistant answering questions about a legal document. Use ONLY the information from the document provided below to answer the user's question. If the answer cannot be found in the document, state that clearly. Do not make up information.\n\nDOCUMENT TEXT:\n---\n{document_text}\n---\n\nCONVERSATION HISTORY:\n{chat_history}\n\nUSER QUESTION: {user_question}",
        "system_instruction": "You are an AI assistant that answers questions based strictly on the provided document text. Do not use any external knowledge."
    }
}

def extract_text_from_file(file_path):
    file_extension = os.path.splitext(file_path)[1].lower()
    text = ""

    if file_extension == '.pdf':
        try:
            reader = pypdf.PdfReader(file_path)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        except Exception as e:
            raise ValueError(f"Error processing PDF: {e}")
    elif file_extension in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']:
        text = pytesseract.image_to_string(Image.open(file_path))
    else:
        raise ValueError(f"Unsupported file type '{file_extension}'. Only PDF, PNG, and JPG are supported.")

    return text


def get_llm_response_for_task(task_name, document_text):
    template = PROMPT_TEMPLATES.get(task_name)
    formatted_prompt = template["prompt"].format(document_text=document_text)
    system_instruction = template["system_instruction"]

    return call_llm(formatted_prompt, system_instruction)

def chat_with_document(document_text, user_question, chat_history):
    template = PROMPT_TEMPLATES.get("chat_with_document")
    formatted_prompt = template["prompt"].format(
        document_text=document_text,
        chat_history=chat_history,
        user_question=user_question
    )
    system_instruction = template["system_instruction"]

    return call_llm(formatted_prompt, system_instruction)

def determine_document_task(document_text):
    # Exclude 'chat_with_document' as it is not a document type for summarization
    valid_tasks = [key for key in PROMPT_TEMPLATES.keys() if key != "chat_with_document"]

    classification_prompt = (
        "Analyze the following legal document text and identify its type. "
        f"Respond with ONLY one of the following keywords: {', '.join(valid_tasks)}. "
        "Do not add any other text, explanation, or punctuation.\n\n"
        "DOCUMENT TEXT:\n"
        f"{document_text}"
    )

    system_instruction = (
        "You are a document classification expert. Your task is to identify the type of a legal document "
        "and respond with a single, specific keyword from the provided list."
    )

    determined_task = call_llm(classification_prompt, system_instruction).strip().replace("'", "").replace('"', '')
    print(f"Document identified as: '{determined_task}'")
    return determined_task

def call_llm(prompt, system_instruction="You are a helpful assistant."):
   
    headers = {
        'Content-Type': 'application/json'
    }

    params = {
        'key': API_KEY
    }

    payload = {
        "contents": [{"parts": [{"text": prompt}]}] ,
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        }
    }

    for attempt in range(3):
        response = requests.post(API_URL, json=payload, headers=headers, params=params)
        if response.status_code == 429 and attempt < 2:
            time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s
            continue
        response.raise_for_status()
        break

    result = response.json()        
    
    candidates = result.get('candidates')
    generated_text = "No response generated."
    if candidates:
        generated_text = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', "No text found.")

    return generated_text

def translate_text(text, target_language):
    translation_prompt = (
    f"Translate the following text into {target_language}. "
    "Do not add any other text, explanation, or punctuation. "
    "Only provide the translated text.\n\n"
    "TEXT TO TRANSLATE:\n"
    f"{text}"
    )

    system_instruction = (
        "You are a translation expert. Your task is to translate the given text "
        f"into {target_language} accurately."
    )

    translated_text = call_llm(translation_prompt, system_instruction)
    return translated_text


if __name__ == "__main__":
    file_to_process = r"C:\Users\Piyush\OneDrive\Desktop\SIH\424021461RC0042023A0009.pdf"
    document_text = extract_text_from_file(file_to_process)

    if document_text and document_text.strip():
        task_to_perform = determine_document_task(document_text)
        llm_response = get_llm_response_for_task(task_to_perform, document_text)
        print(llm_response)

        target_language = "Hindi" 
        translated_summary = translate_text(llm_response, target_language)
        print(translated_summary)
        print("You can now ask questions about the document. Type 'quit' to exit.")
        chat_history = ""
        while True:
            user_question = input("\nYour Question: ")
            if user_question.lower().strip() == 'quit':
                print("Exiting chat.")
                break
        
            answer = chat_with_document(document_text, user_question, chat_history)
            print(f"\n{answer}")

            chat_history += f"User: {user_question}\nAssistant: {answer}\n"