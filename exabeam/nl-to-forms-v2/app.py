# app.py
import os
from flask import Flask, render_template, request, jsonify, session
from uuid import uuid4
import json
import gemini_handler
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")

# In-memory storage for conversation history.
conversations = {}

def get_or_create_conversation(session_id: str) -> list:
    if session_id not in conversations:
        conversations[session_id] = []
    return conversations[session_id]

@app.route("/")
def index():
    if 'session_id' in session:
        conversations.pop(session['session_id'], None)
    session['session_id'] = str(uuid4())
    maps_api_key = os.environ.get("Maps_API_KEY")
    return render_template('index.html', maps_api_key=maps_api_key)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    history = get_or_create_conversation(session.get('session_id'))
    
    current_json = data.get("current_json")

    ai_raw_response = gemini_handler.get_gemini_chat_response(
        new_prompt=data.get("message"),
        current_json=current_json,
        file_b64=data.get("file_data"),
        mime_type=data.get("mime_type")
    )
    
    history.append({"role": "user", "content": data.get("message")})
    history.append({"role": "model", "content": ai_raw_response})

    extraction_result = gemini_handler.extract_json_from_response(ai_raw_response)
    if extraction_result:
        response_text, form_json = extraction_result
    else:
        response_text = "An error occurred processing the AI response. Please try again."
        form_json = None
    
    return jsonify({"response_text": response_text, "form_json": form_json})

@app.route("/enhance", methods=["POST"])
def enhance():
    data = request.get_json()
    form_json = data.get("form_json")
    action = data.get("action")
    language = data.get("language")

    if not form_json or not action:
        return jsonify({"error": "Missing form data or action"}), 400

    raw_response = gemini_handler.run_enhancement_action(form_json, action, language)

    if action in ["analyze_compliance", "suggest_workflows"]:
        return jsonify({"analysis_text": raw_response})
    else:
        try:
            updated_form_json = json.loads(raw_response)
            return jsonify({"updated_form_json": updated_form_json})
        except json.JSONDecodeError:
            _, updated_form_json = gemini_handler.extract_json_from_response(raw_response)
            if updated_form_json:
                return jsonify({"updated_form_json": updated_form_json})
            else:
                print(f"🚨 ERROR: Could not parse JSON from enhancement action. Response was: {raw_response}")
                return jsonify({"error": "AI returned invalid or non-JSON data for this action."}), 500

if __name__ == "__main__":
    print(f"✅ Starting Flask App...")
    app.run(debug=True, port=5000)