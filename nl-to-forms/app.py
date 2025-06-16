import os
import json
import pandas as pd
from flask import Flask, render_template_string, request, jsonify, session
from google import genai
from google.genai import types
import re
from uuid import uuid4
from io import StringIO
import base64

# --- Configuration ---
PROJECT_ID = "learn-w-me"
app = Flask(__name__)
# A secret key is required for Flask session management
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-for-session")

# In-memory storage for conversation history.
conversations = {}

# --- HTML Template ---
TEMPLATE_CHAT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Gemini Next-Gen Form Engine</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --border-color: #dee2e6; --primary-blue: #0d6efd; --hover-blue: #0b5ed7;
            --text-dark: #212529; --text-light: #6c757d; --bg-light: #f8f9fa;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 0; background-color: #fff; display: flex; height: 100vh; overflow: hidden;
        }
        .container { display: flex; width: 100%; }
        #chat-column {
            flex: 1; display: flex; flex-direction: column;
            border-right: 1px solid var(--border-color); height: 100vh;
        }
        #chat-header {
            display: flex; justify-content: space-between; align-items: center;
            padding: 10px 20px; border-bottom: 1px solid var(--border-color);
        }
        #chat-header h1 { font-size: 1.2em; margin: 0; color: var(--text-dark); }
        #new-form-btn {
            background-color: #dc3545; color: white; border: none;
            padding: 8px 12px; border-radius: 6px; cursor: pointer;
        }
        #chat-log { flex-grow: 1; overflow-y: auto; padding: 20px; }
        .message {
            margin-bottom: 20px; padding: 12px 18px; border-radius: 18px;
            max-width: 90%; line-height: 1.5; word-wrap: break-word; position: relative;
        }
        .user-message {
            background-color: var(--primary-blue); color: white; align-self: flex-end;
            margin-left: auto; border-bottom-right-radius: 4px;
        }
        .ai-message {
            background-color: var(--bg-light); color: var(--text-dark); align-self: flex-start;
            border-bottom-left-radius: 4px;
        }
        .ai-message ul { padding-left: 20px; margin: 5px 0; }
        .user-message img.thumbnail, .user-message video.thumbnail {
             max-width: 200px; border-radius: 8px; margin-top: 10px;
        }
        .file-preview { font-style: italic; color: #fff; }
        .message-actions { margin-top: 10px; position: relative; }
        .actions-btn {
            font-size: 0.8em; background-color: #17a2b8; color: white; border: none;
            padding: 4px 8px; border-radius: 12px; cursor: pointer;
        }
        .actions-menu {
            display: none; position: absolute; background-color: white; border: 1px solid var(--border-color);
            border-radius: 6px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); padding: 5px; z-index: 10;
        }
        .actions-menu span {
            display: block; padding: 5px 10px; cursor: pointer;
        }
        .actions-menu span:hover { background-color: var(--bg-light); }
        #chat-form-container {
            padding: 15px; border-top: 1px solid var(--border-color); background-color: #fff;
        }
        #chat-form { display: flex; }
        #chat-form input[type="text"] {
            flex-grow: 1; border: 1px solid var(--border-color); border-radius: 20px;
            padding: 10px 15px; font-size: 1em; margin-right: 10px;
        }
        #chat-form button {
            background-color: var(--primary-blue); color: white; border: none; border-radius: 20px;
            padding: 10px 20px; cursor: pointer; font-size: 1em; transition: background-color 0.2s;
        }
        #chat-form button:hover { background-color: var(--hover-blue); }
        #chat-form button:disabled { background-color: #adb5bd; cursor: not-allowed; }
        #upload-container { display: flex; align-items: center; padding-top: 10px; }
        #file-upload-btn {
            background-color: #6c757d; color: white; padding: 5px 10px; border-radius: 15px;
            cursor: pointer; font-size: 0.8em; margin-right: 10px;
        }
        #file-info { font-size: 0.8em; color: var(--text-light); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        #preview-column { flex: 1; padding: 20px; overflow-y: auto; background-color: #fdfdfd; }
        .page-container {
            border: 1px solid #e9ecef; border-radius: 8px; margin-bottom: 20px;
            background-color: #fff; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .page-header {
            font-size: 1.2em; font-weight: bold; padding: 15px 20px;
            background-color: var(--bg-light); border-bottom: 1px solid #e9ecef;
            border-top-left-radius: 8px; border-top-right-radius: 8px;
        }
        .page-content { padding: 20px; }
        .form-field { margin-bottom: 25px; position: relative; }
        label { display: block; font-weight: 700; margin-bottom: 8px; font-size: 1em; color: #495057; }
        label small { font-weight: normal; color: var(--text-light); display: block; font-size: 0.85em; }
        input[type=text], select, textarea {
            width: 100%; padding: 10px; border: 1px solid #ced4da;
            border-radius: 4px; box-sizing: border-box; font-size: 1em;
        }
        .radio-group div, .checklist-group div { margin-bottom: 8px; }
        .photo-upload, .signature-pad {
            height: 120px; border: 2px dashed #ccc; display: flex; align-items: center;
            justify-content: center; color: #aaa; border-radius: 4px;
        }
        .address-block, .dynamic-table {
            border: 1px solid #ced4da; padding: 15px; border-radius: 4px;
        }
        .address-block input { margin-bottom: 5px; }
        .dynamic-table table { width: 100%; border-collapse: collapse; }
        .dynamic-table th, .dynamic-table td { border: 1px solid #ddd; padding: 8px; text-align: left;}
        .dynamic-table button { background-color: #28a745; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; margin-top: 10px;}
        .conditional-rule-indicator {
            position: absolute; top: 0; right: 0; font-size: 0.7em;
            background-color: #ffc107; color: #333; padding: 2px 5px; border-radius: 10px;
            cursor: help;
        }
        pre { background-color: #e9ecef; padding: 15px; border-radius: 8px; white-space: pre-wrap; word-wrap: break-word; font-size: 0.9em; }
        h2 { color: var(--text-dark); }
    </style>
</head>
<body>
    <div class="container">
        <div id="chat-column">
            <div id="chat-header">
                <h1>AI Form Engine</h1>
                <button id="new-form-btn" title="Clear chat and form preview">Start New Build</button>
            </div>
            <div id="chat-log">
                <div class="message ai-message">
                    Welcome to the Next-Gen Form Engine! Upload an image, video, or data file, or simply describe the complex form you need.
                </div>
            </div>
            <div id="chat-form-container">
                <form id="chat-form">
                    <input type="text" id="user-input" placeholder="Describe the form or upload a file..." autocomplete="off">
                    <button type="submit" id="send-button">Send</button>
                </form>
                <div id="upload-container">
                     <label for="file-upload" id="file-upload-btn">📎 Attach File</label>
                     <input type="file" id="file-upload" style="display: none;">
                     <span id="file-info"></span>
                </div>
            </div>
        </div>
        <div id="preview-column">
            <h2>Live Form Preview</h2>
            <div id="form-preview-area">
                <p style="color: var(--text-light);">Your form preview will appear here.</p>
            </div>
            <hr>
            <h2>Generated JSON</h2>
            <pre id="json-preview-area"><code>{}</code></pre>
        </div>
    </div>

    <script>
    document.addEventListener('DOMContentLoaded', () => {
        const chatLog = document.getElementById('chat-log');
        const chatForm = document.getElementById('chat-form');
        const userInput = document.getElementById('user-input');
        const sendButton = document.getElementById('send-button');
        const formPreviewArea = document.getElementById('form-preview-area');
        const jsonPreviewArea = document.getElementById('json-preview-area');
        const fileUpload = document.getElementById('file-upload');
        const fileInfo = document.getElementById('file-info');
        const newFormBtn = document.getElementById('new-form-btn');
        let sessionForms = {};

        newFormBtn.addEventListener('click', () => { location.reload(); });
        
        fileUpload.addEventListener('change', (event) => {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    fileInfo.textContent = `Attached: ${file.name}`;
                    chatForm.dataset.fileData = e.target.result; 
                    chatForm.dataset.fileMimeType = file.type;
                };
                reader.readAsDataURL(file);
            }
        });

        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const messageText = userInput.value.trim();
            const fileData = chatForm.dataset.fileData;
            const fileMimeType = chatForm.dataset.fileMimeType;
            if (!messageText && !fileData) return;

            toggleSendButton(true);
            appendMessage(messageText, 'user', {data: fileData, mimeType: fileMimeType});
            
            userInput.value = '';
            delete chatForm.dataset.fileData;
            delete chatForm.dataset.fileMimeType;
            fileInfo.textContent = "";
            fileUpload.value = "";

            try {
                const payload = { message: messageText, file_data: fileData, mime_type: fileMimeType };

                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) throw new Error(`Server error: ${response.statusText}`);

                const data = await response.json();
                const messageId = `msg-${Date.now()}`;
                appendMessage(data.response_text, 'ai', null, messageId);

                if (data.form_json) {
                    sessionForms[messageId] = data.form_json;
                    renderJsonPreview(data.form_json);
                    renderFormPreview(data.form_json);
                    addAiActions(messageId);
                }
            } catch (error) {
                console.error('An error occurred during form processing:', error);
                appendMessage('Sorry, an error occurred while rendering the form preview. Please check the developer console for details.', 'ai');
            } finally {
                toggleSendButton(false);
            }
        });

        function appendMessage(text, sender, file = null, messageId = '') {
            if (typeof text !== 'string') return;
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}-message`;
            if (messageId) messageDiv.id = messageId;
            
            let content = text.replace(/\\n/g, '<br>');
            if (file && file.data && sender === 'user') {
                if (file.mimeType && file.mimeType.startsWith('image/')) {
                    content += `<br><img src="${file.data}" class="thumbnail" alt="Uploaded image">`;
                } else if (file.mimeType && file.mimeType.startsWith('video/')) {
                    content += `<br><video src="${file.data}" class="thumbnail" controls></video>`;
                } else {
                    content += `<br><div class="file-preview">📄 File Attached</div>`;
                }
            }
            messageDiv.innerHTML = content;
            chatLog.appendChild(messageDiv);
            chatLog.scrollTop = chatLog.scrollHeight;
        }
        
        function addAiActions(messageId) {
            const messageDiv = document.getElementById(messageId);
            if (!messageDiv) return;

            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'message-actions';
            
            const actionsBtn = document.createElement('button');
            actionsBtn.className = 'actions-btn';
            actionsBtn.textContent = '🤖 AI Actions';
            
            const menuDiv = document.createElement('div');
            menuDiv.className = 'actions-menu';
            const actions = {
                'Translate...': 'translate',
                'Analyze for Compliance': 'analyze_compliance',
                'Suggest Workflows': 'suggest_workflows',
                'Generate Help Text': 'generate_help_text'
            };
            
            Object.entries(actions).forEach(([label, action]) => {
                const actionSpan = document.createElement('span');
                actionSpan.textContent = label;
                actionSpan.onclick = () => runAiAction(messageId, action, label, actionsBtn);
                menuDiv.appendChild(actionSpan);
            });

            actionsBtn.onclick = (e) => {
                e.stopPropagation();
                const allMenus = document.querySelectorAll('.actions-menu');
                allMenus.forEach(m => { if(m !== menuDiv) m.style.display = 'none' });
                menuDiv.style.display = menuDiv.style.display === 'block' ? 'none' : 'block';
            };

            actionsDiv.appendChild(actionsBtn);
            actionsDiv.appendChild(menuDiv);
            messageDiv.appendChild(actionsDiv);
        }

        async function runAiAction(messageId, action, label, btn) {
            const formJson = sessionForms[messageId];
            if (!formJson) return;
            
            btn.textContent = 'Thinking...';
            btn.disabled = true;
            document.querySelector(`#${messageId} .actions-menu`).style.display = 'none';

            let language = null;
            if (action === 'translate') {
                language = prompt("Which language would you like to translate to? (e.g., Spanish, Japanese)");
                if (!language) {
                    btn.textContent = '🤖 AI Actions';
                    btn.disabled = false;
                    return;
                }
            }

            try {
                const response = await fetch('/enhance', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        form_json: formJson,
                        action: action,
                        language: language
                    })
                });
                if (!response.ok) throw new Error(`Action '${label}' failed`);
                
                const result = await response.json();

                if(result.updated_form_json) {
                    sessionForms[messageId] = result.updated_form_json;
                    renderFormPreview(result.updated_form_json);
                    renderJsonPreview(result.updated_form_json);
                    appendMessage(`OK, I've applied the action: ${label}. The form has been updated.`, 'ai');
                } else if(result.analysis_text) {
                     appendMessage(`Here is the analysis you requested for '${label}':\\n${result.analysis_text}`, 'ai');
                }

            } catch (error) {
                console.error("AI Action Error:", error);
                appendMessage(`Sorry, the action '${label}' failed.`, 'ai');
            } finally {
                btn.textContent = '🤖 AI Actions';
                btn.disabled = false;
            }
        }
        
        function toggleSendButton(isSending) {
            if (sendButton) {
                sendButton.disabled = isSending;
                sendButton.textContent = isSending ? '...' : 'Send';
            }
        }

        function renderFormPreview(formData) {
            formPreviewArea.innerHTML = '';
            
            if (!formData || !Array.isArray(formData.pages) || formData.pages.length === 0) {
                formPreviewArea.innerHTML = '<p style="color: var(--text-light);">Form has no pages or is malformed.</p>';
                return;
            }
            
            let formTitle = document.createElement('h2');
            formTitle.textContent = formData.form_name || 'Untitled Form';
            formPreviewArea.appendChild(formTitle);

            formData.pages.forEach(page => {
                const pageContainer = document.createElement('div');
                pageContainer.className = 'page-container';
                pageContainer.innerHTML = `<div class="page-header">${page.page_name || 'Untitled Page'}</div>`;
                const pageContent = document.createElement('div');
                pageContent.className = 'page-content';

                if (Array.isArray(page.fields)) {
                    page.fields.forEach(field => {
                        if (!field || typeof field !== 'object') return;

                        const fieldDiv = document.createElement('div');
                        fieldDiv.className = 'form-field';
                        
                        const displayName = field.display_name || 'Untitled Field';
                        const helpText = field.help_text ? `<small>${field.help_text}</small>` : '';
                        let fieldHtml = `<label>${displayName}${helpText}</label>`;
                        
                        if (field.visibility_rule) {
                            const rule = field.visibility_rule;
                            const ruleText = `Visible if '${rule.field_id || ''}' ${rule.operator || ''} '${rule.value || ''}'`;
                            fieldHtml += `<span class="conditional-rule-indicator" title="${ruleText}">C</span>`;
                        }
                        
                        const options = Array.isArray(field.options) ? field.options : [];
                        const fieldType = field.type || 'text';
                        
                        let inputHtml = '';
                        switch (fieldType) {
                            case 'text': inputHtml = `<input type="text" placeholder="${field.placeholder || ''}">`; break;
                            case 'textarea': inputHtml = `<textarea placeholder="${field.placeholder || ''}"></textarea>`; break;
                            case 'dropdown': inputHtml = `<select><option value="">-- Select --</option>${options.map(o => `<option value="${o}">${o}</option>`).join('')}</select>`; break;
                            case 'radio':
                            case 'checklist':
                                const inputType = fieldType === 'radio' ? 'radio' : 'checkbox';
                                inputHtml = `<div class="${fieldType}-group">${options.map(o => `<div><input type="${inputType}" name="${field.field_id || displayName}" value="${o}"> ${o}</div>`).join('')}</div>`;
                                break;
                            case 'photo': inputHtml = '<div class="photo-upload">PHOTO UPLOAD AREA</div>'; break;
                            case 'signature': inputHtml = '<div class="signature-pad">SIGNATURE PAD</div>'; break;
                            case 'address': inputHtml = '<div class="address-block"><input type="text" placeholder="Street Address"><input type="text" placeholder="City"><input type="text" placeholder="State"><input type="text" placeholder="Zip Code"></div>'; break;
                            case 'dynamic_table': inputHtml = '<div class="dynamic-table"><table><tr><th>Description</th><th>Quantity</th><th>Unit Price</th></tr><tr><td></td><td></td><td></td></tr></table><button>+ Add Row</button></div>'; break;
                            default: inputHtml = `<input type="text" placeholder="Unsupported field type: ${fieldType}">`;
                        }
                        fieldDiv.innerHTML = fieldHtml + inputHtml;
                        pageContent.appendChild(fieldDiv);
                    });
                }
                pageContainer.appendChild(pageContent);
                formPreviewArea.appendChild(pageContainer);
            });
        }
        
        function renderJsonPreview(jsonData) {
            if (jsonPreviewArea) {
                jsonPreviewArea.querySelector('code').textContent = JSON.stringify(jsonData, null, 2);
            }
        }
    });
    </script>
</body>
</html>
"""

# --- Backend Logic and New Endpoints ---

def get_or_create_conversation(session_id: str) -> list:
    """Gets the conversation history for a session, or creates a new one."""
    if session_id not in conversations:
        conversations[session_id] = []
    return conversations[session_id]

def extract_json_from_response(text: str) -> (str, dict):
    """Extracts the JSON block and the conversational text from the AI's response."""
    print("\n--- EXTRACTING JSON FROM RAW RESPONSE ---")
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
        response_text = re.sub(r"```json\s*(\{.*?\})\s*```", "", text, flags=re.DOTALL).strip()
        print("✅ Found JSON block.")
        try:
            form_json = json.loads(json_str)
            print("✅ JSON is valid.")
            return response_text, form_json
        except json.JSONDecodeError:
            print("🚨 ERROR: AI returned invalid JSON.")
            return f"The AI returned invalid JSON.", None
    else:
        print("⚠️ WARNING: No JSON block found.")
        return text, None


def get_gemini_chat_response(history: list, new_prompt: str, file_b64: str = None, mime_type: str = None) -> str:
    """Manages the conversation turn with the Gemini API."""
    print("\n--- PREPARING TO CALL GEMINI API (CHAT) ---")
    try:
        metadata_df = pd.read_csv("metadata.csv")
        output = StringIO()
        metadata_df.to_csv(output, index=False)
        metadata_context = output.getvalue()
    except FileNotFoundError:
        return '{"error": "metadata.csv not found."}'

    system_prompt = f"""
    You are a world-class, multimodal AI assistant for building complex business forms. You can interpret text, images, videos, and data files (CSV/JSON) to generate forms.

    **JSON STRUCTURE RULES:**
    - The root must have `form_name` and `pages`. Each page must have `page_name` and `fields`.
    - A field can have a `visibility_rule` object for conditional logic.
    - A field can have a `help_text` string for tooltips.

    **CAPABILITIES & RULES:**
    1.  **MULTIMODAL INPUT:**
        - If an **image or video** is provided, interpret it as a form and convert it to the JSON structure.
        - If a **CSV or JSON file** is provided, analyze its structure and generate a form designed to capture that data.
    2.  **AI ANALYSIS & ENHANCEMENT:**
        - **Compliance/Accessibility:** If asked to analyze for standards like WCAG or HIPAA, provide a bulleted list of suggestions in your text response.
        - **Workflow Suggestions:** If asked for workflows, describe potential post-submission automation triggers and actions.
        - **Help Text Generation:** If asked to generate help text, add a `help_text` key to each field in the JSON.
    3.  **CORE LOGIC:**
        - Always create multi-page forms for clarity.
        - Always implement conditional logic when requested via `visibility_rule`.
    4.  **OUTPUT:** For any form generation/modification, provide BOTH a text reply AND the complete JSON in a ```json block. For analysis tasks, provide text only.
    ---
    **DATA SCHEMA CONTEXT (in CSV format):**
    {metadata_context}
    ---
    """
    
    api_contents = []
    api_contents.append(types.Content(role="user", parts=[types.Part(text=system_prompt)]))
    api_contents.append(types.Content(role="model", parts=[types.Part(text="Okay, I am a multimodal, next-gen form engine. I will interpret files and text to build and enhance complex forms, providing both conversational responses and structured JSON.")]))

    for entry in history:
        api_contents.append(types.Content(role=entry["role"], parts=[types.Part(text=entry["content"])]))
        
    prompt_parts = [types.Part(text=new_prompt)]
    if file_b64 and mime_type:
        try:
            header, encoded = file_b64.split(",", 1)
            file_data = base64.b64decode(encoded)
            prompt_parts.insert(0, types.Part(inline_data=types.Blob(mime_type=mime_type, data=file_data)))
            print(f"✅ File ({mime_type}) successfully processed for API call.")
        except Exception as e:
            return f"There was an error processing the uploaded file: {e}"

    api_contents.append(types.Content(role="user", parts=prompt_parts))
    
    try:
        client = genai.Client(vertexai=True, project=PROJECT_ID, location="us-central1")
        model = "gemini-2.0-flash" 
        config = types.GenerateContentConfig(temperature=0.4)
        response = client.models.generate_content(model=model, contents=api_contents, config=config)
        return response.text
    except Exception as e:
        return f"Sorry, an error occurred communicating with the AI: {e}"

def run_enhancement_action(form_json: dict, action: str, language: str = None) -> str:
    """Runs a specific enhancement task using a targeted prompt."""
    print(f"\n--- PREPARING TO CALL GEMINI API (ENHANCE: {action}) ---")
    
    prompts = {
        "translate": f"Translate the user-facing text in this JSON object to {language}. Specifically, translate `form_name`, `page_name`, and `display_name`. Do NOT translate other keys or values. Return ONLY the raw, translated JSON object.",
        "analyze_compliance": "You are a compliance expert. Analyze the following form JSON for potential issues related to web accessibility (WCAG) and sensitive data handling (like PII or HIPAA). Provide a bulleted list of concerns and suggestions. Do not return JSON.",
        "suggest_workflows": "You are a business process automation consultant. Based on the following form, suggest 3 potential post-submission workflows. For each, describe the trigger (e.g., a field value), the action (e.g., send an email), and the systems involved. Do not return JSON.",
        "generate_help_text": "You are a UX writer. For the following form JSON, add a new key `help_text` to each field object containing a concise, helpful tooltip or placeholder text for the end-user. Return the complete, updated JSON object and nothing else."
    }
    
    if action not in prompts:
        return json.dumps({"error": "Invalid action"})

    full_prompt = f"{prompts[action]}\n\nForm JSON:\n```json\n{json.dumps(form_json, indent=2)}\n```"

    try:
        client = genai.Client(vertexai=True, project=PROJECT_ID, location="us-central1")
        model = "gemini-2.0-flash"
        config = types.GenerateContentConfig(temperature=0.5)
        response = client.models.generate_content(model=model, contents=[full_prompt], config=config)
        print(f"✅ Enhancement action '{action}' successful.")
        return response.text
    except Exception as e:
        return json.dumps({"error": f"Failed to perform action '{action}': {e}"})

# --- Flask Routes ---
@app.route("/")
def index():
    if 'session_id' in session:
        conversations.pop(session['session_id'], None)
    session['session_id'] = str(uuid4())
    return render_template_string(TEMPLATE_CHAT)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    history = get_or_create_conversation(session.get('session_id'))
    
    ai_raw_response = get_gemini_chat_response(
        history=history,
        new_prompt=data.get("message"),
        file_b64=data.get("file_data"),
        mime_type=data.get("mime_type")
    )
    
    # --- FIX: Corrected the typo here ---
    history.append({"role": "user", "content": data.get("message")})
    history.append({"role": "model", "content": ai_raw_response})

    response_text, form_json = extract_json_from_response(ai_raw_response)
    return jsonify({"response_text": response_text, "form_json": form_json})


@app.route("/enhance", methods=["POST"])
def enhance():
    """New endpoint to handle all AI enhancement actions."""
    data = request.get_json()
    form_json = data.get("form_json")
    action = data.get("action")
    language = data.get("language")

    if not form_json or not action:
        return jsonify({"error": "Missing form data or action"}), 400

    raw_response = run_enhancement_action(form_json, action, language)

    if action in ["analyze_compliance", "suggest_workflows"]:
        return jsonify({"analysis_text": raw_response})
    else:
        response_text, updated_form_json = extract_json_from_response(f"```json\n{raw_response}\n```")
        if updated_form_json:
            return jsonify({"updated_form_json": updated_form_json})
        else:
            try:
                return jsonify({"updated_form_json": json.loads(raw_response)})
            except json.JSONDecodeError:
                return jsonify({"error": "AI returned invalid data for this action."}), 500


if __name__ == "__main__":
    print(f"✅ Starting Flask App for doForms AI Demo on [http://127.0.0.1:5000](http://127.0.0.1:5000)")
    app.run(debug=True, port=5000)