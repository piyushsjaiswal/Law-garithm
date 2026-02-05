from flask import Flask, render_template, request, jsonify
import os
import uuid

from llm import (
    extract_text_from_file,
    determine_document_task,
    get_llm_response_for_task,
    translate_text,
    chat_with_document
)

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# In-memory storage for document context (for demo purposes)
# In a production app, use a database (Redis, SQL, etc.)
document_store = {}

@app.route('/')
def index():
    """Renders the frontend HTML."""
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handles file upload, text extraction, summarization, and translation."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part provided'}), 400
    
    file = request.files['file']
    target_language = request.form.get('language', 'Hindi')
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        try:
            # 1. Save the file
            filename = file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # 2. Extract Text using the function from llm.py
            extracted_text = extract_text_from_file(file_path)
            if not extracted_text or not extracted_text.strip():
                return jsonify({'error': 'Could not extract text from the document. The file might be empty, corrupted, or an image-based PDF requiring OCR.'}), 400

            # 3. Determine document type and Generate Summary
            task = determine_document_task(extracted_text)
            summary = get_llm_response_for_task(task, extracted_text)

            # 4. Translate Summary
            translated_summary = translate_text(summary, target_language)

            # 5. Store context for Chat
            doc_id = str(uuid.uuid4())
            document_store[doc_id] = {
                'filename': filename,
                'text': extracted_text,
                'summary': summary,
                'chat_history': "" # Initialize chat history
            }

            return jsonify({
                'summary': summary,
                'translated_summary': translated_summary,
                'language': target_language,
                'doc_id': doc_id
            })

        except Exception as e:
            app.logger.error(f"Processing failed: {e}")
            return jsonify({'error': f"An error occurred during processing: {str(e)}"}), 500

    return jsonify({'error': 'Upload failed'}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handles chat interaction with the document."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Invalid JSON data'}), 400
        
    question = data.get('question')
    doc_id = data.get('doc_id')

    if not question or not doc_id:
        return jsonify({'error': 'Missing question or doc_id'}), 400

    if doc_id not in document_store:
        return jsonify({'error': 'Document session not found. Please upload again.'}), 404

    try:
        # Retrieve document context
        doc_context = document_store[doc_id]
        
        # Generate Answer using RAG from llm.py
        answer = chat_with_document(
            document_text=doc_context['text'],
            user_question=question,
            chat_history=doc_context.get('chat_history', '')
        )

        # Update conversation history
        doc_context['chat_history'] += f"User: {question}\nAssistant: {answer}\n"

        return jsonify({'answer': answer})

    except Exception as e:
        app.logger.error(f"Chat failed: {e}")
        return jsonify({'error': f"An error occurred during chat: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)