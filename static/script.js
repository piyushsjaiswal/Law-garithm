document.addEventListener('DOMContentLoaded', () => {

    const uploadForm = document.getElementById('upload-form');
    const chatForm = document.getElementById('chat-form');
    const fileInput = document.getElementById('file-input');
    const chatInput = document.getElementById('chat-input');
    const chatWindow = document.getElementById('chat-window');
    const loader = document.getElementById('loader');
    const chatLoader = document.getElementById('chat-loader');
    const uploadError = document.getElementById('upload-error');
    const uploadButton = document.getElementById('upload-button');

    const resultsSection = document.getElementById('results-section');
    const chatSection = document.getElementById('chat-section');
    const summaryOutput = document.getElementById('summary-output');
    const translatedSummaryOutput = document.getElementById('translated-summary-output');
    const translatedSummaryTitle = document.getElementById('translated-summary-title');

    /* VOICE ELEMENTS */
    const micBtn = document.getElementById('mic-btn');
    const chatLanguage = document.getElementById('chat-language');
    const voiceToggle = document.getElementById('voice-toggle');

    let docId = null;

    /* ---------------- Upload ---------------- */
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData(uploadForm);
        loader.style.display = 'block';
        uploadButton.disabled = true;
        uploadError.textContent = ''; // Clear previous errors

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
 
            const result = await response.json();

            if (!response.ok) {
                // If the server returned an error, use the message from the JSON body
                throw new Error(result.error || `Request failed with status ${response.status}`);
            }

            summaryOutput.textContent = result.summary;
            translatedSummaryOutput.textContent = result.translated_summary;
            translatedSummaryTitle.textContent =
                `Translated Summary (${result.language})`;
 
            docId = result.doc_id;
            resultsSection.style.display = 'block';
            chatSection.style.display = 'flex';

        } catch (err) {
            uploadError.textContent = `Error: ${err.message}`;
            resultsSection.style.display = 'none';
            chatSection.style.display = 'none';
        } finally {
            loader.style.display = 'none';
            uploadButton.disabled = false;
        }
    });

    /* ---------------- Chat ---------------- */
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!chatInput.value || !docId) return;
        
        const question = chatInput.value;
        addChatMessage(question, 'user');
        chatInput.value = '';

        chatLoader.style.display = 'block';

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question,
                    doc_id: docId
                })
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || `Request failed with status ${response.status}`);
            }

            addChatMessage(result.answer, 'bot');

        } catch (err) {
            addChatMessage(`Error: ${err.message}`, "bot");
        } finally {
            chatLoader.style.display = 'none';
        }
    });

    function addChatMessage(message, sender) {
        const div = document.createElement('div');
        div.classList.add('chat-message', sender);

        const p = document.createElement('p');
        p.textContent = message;

        div.appendChild(p);
        chatWindow.appendChild(div);
        chatWindow.scrollTop = chatWindow.scrollHeight;

        if (sender === 'bot' && voiceToggle.checked) {
            speak(message);
        }
    }

    /* ---------------- VOICE OUTPUT ---------------- */
    function speak(text) {
        if (!window.speechSynthesis) return;
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = chatLanguage.value;
        speechSynthesis.speak(utterance);
    }

    /* ---------------- VOICE INPUT ---------------- */
    const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition) {
        const recognition = new SpeechRecognition();

        micBtn.addEventListener('click', () => {
            recognition.lang = chatLanguage.value;
            recognition.start();
        });

        recognition.onresult = (event) => {
            chatInput.value = event.results[0][0].transcript;
        };
    } else {
        micBtn.disabled = true;
        micBtn.textContent = "🎤 Not Supported";
    }

});
