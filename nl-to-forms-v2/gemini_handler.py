# gemini_handler.py
import os
import json
import pandas as pd
from dotenv import load_dotenv
from google import genai 
from google.genai.types import FunctionDeclaration, GenerateContentConfig, Part, Tool  # Specific components for function calling
import re
from google.genai import types
# from google.generativeai.types import GenerationConfig

# --- Load Environment Variables ---
# Load environment variables from .env file at the start
load_dotenv()

# Now, access them throughout the script
PROJECT_ID = os.getenv("PROJECT_ID")
GCP_LOCATION = os.getenv("GCP_LOCATION")
MODEL_NAME = os.getenv("MODEL_NAME")
print("MODEL_NAME", MODEL_NAME)
# --- Initialize Vertex AI Client ---
#  For Vertex AI, this connects the google-generativeai SDK to a Vertex backend.
client = genai.Client(vertexai=True,project=PROJECT_ID, location=GCP_LOCATION)

# This function uses Gemini to find the best match.
def get_lookup_values(field_name: str) -> list[str]:
    """
    Looks up values for a field by finding the semantically closest match in a CSV.
    Uses a separate Gemini call to perform the semantic matching.
    
    Args:
        field_name (str): A user-provided field name (e.g., 'data center options', 'urgency').
    
    Returns:
        list[str]: A list of values for the best-matching lookup.
    """
    print(f"--- TOOLBOX: Starting SEMANTIC LOOKUP for: '{field_name}' ---")
    try:
        df = pd.read_csv("lookups.csv")
        # Use Gemini to find the best semantic match for the field_name
        match_prompt = f"""
        Analyze the user's requested field name and find the best match from the available options.
        Lookup has format as lookup_name, lookup_values:{df}
        The user requested field name: "{field_name}".   
        Which lookup_name is the closest semantic match (at least 70% similar in meaning) to user requested field name?
        Respond with only the single best-matching lookup name and multiple corresponding lookup values. If no option is a good match, respond with the exact word 'None'.
        delimited output format:
        lookup_name| lookup_values
        """
    
        # Use the globally initialized client and model
        match_response = client.models.generate_content(
            model=MODEL_NAME,
            contents=match_prompt,
            config=GenerateContentConfig(temperature=0),)

        best_match = match_response.text.strip().replace("'", "").replace('"', '')
        parts = best_match.split('|', 1)
        lookup_keys = parts[0]
        lookup_values = parts[1]
        print("best_match keys:", lookup_keys)
        print("best_match values:", lookup_values)

        if best_match != "None" :
            print(f"✅ Semantic match found: '{field_name}' -> '{lookup_keys}'")
            print(f"✅ Found values: {lookup_values}")
            return lookup_values
        else:
            print(f"⚠️ No suitable semantic match found for '{field_name}'.")
            return []

    except Exception as e:
        print(f"🚨 ERROR in get_lookup_values: {e}")
        return []


def extract_json_from_response(text: str) -> tuple:

    print("\n--- EXTRACTING JSON FROM RAW RESPONSE ---")
    if not isinstance(text, str):
        return "Error: Invalid input received from AI.", None
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
        response_text = text.replace(json_match.group(0), "").strip()
        try:
            form_json = json.loads(json_str)
            return response_text, form_json
        except json.JSONDecodeError as e:
            return f"The AI returned invalid JSON: {e}", None
    else:
        return text, None



def get_gemini_chat_response(new_prompt: str, current_json: dict = None, file_b64: str = None, mime_type: str = None) -> str:
    """Manages the conversation turn with the Gemini API using an explicit state."""
    print("\n--- PREPARING TO CALL GEMINI API (STATEFUL CHAT) ---")
    

    system_prompt = f"""
 You are a highly precise AI assistant that generates and modifies JSON for web forms based on user instructions.

    **Primary Directive:** Your most important task is to generate a valid JSON object that conforms perfectly to the specified schema.

    **Output Format Rules:**
    1.  Your response MUST START with a Markdown JSON code block: ```json ... ```. No exceptions.
    2.  Any conversational text MUST come AFTER the JSON block.

    **JSON Structure Rules:**
    - The root object MUST have "form_name" (string) and "pages" (array).
    - Each object inside "pages" MUST have "page_name" (string) and "fields" (array).

    **Field Object Schema:**
    EVERY object inside the "fields" array MUST use these exact keys:
    - `display_name`: The user-visible title for the field (e.g., "Last Name").
    - `field_id`: A unique, snake_case identifier (e.g., "last_name").
    - `type`: The field type. Examples: 'text', 'textarea', 'dropdown', 'radio_group', 'checklist', 'photo_upload', 'signature_pad', 'group'.
    - `options`: (ONLY for dropdown, radio_group, checklist) An array of strings.
    - `required`: (Optional) A boolean (true/false).
    - `help_text`: (Optional) A string with extra instructions.
    
    **Tool Usage for Lookups:**
    - If the user asks for a field that implies a predefined list of choices (e.g., "a dropdown for our data center locations", "a checklist of issue types", "radio buttons for urgency level"), you MUST use the `get_lookup_values` tool.
    - When calling the tool, provide a plausible `field_name` that would be used as a key in a database, such as `data_center_locations` or `issue_urgency`.
    - If user has already provided the list of values then user provided values override the `get_lookup_values` tool values.
    - If user asks to edit the values from `get_lookup_values` tool then do so.
    - Do NOT invent your own options for these types of fields; always use the tool to get the real data.

    **Task Logic:**
    -   If you are NOT given a "CURRENT_FORM_JSON", create a new form from scratch based on the user's request.
    -   If you ARE given a "CURRENT_FORM_JSON", you MUST modify it based on the user's new instruction. Add to or alter the JSON. **Do not remove existing fields unless explicitly asked to.** Output the new, complete JSON.
    
    **Example**
    

    """
    
    api_contents = [
        types.Content(role="user", parts=[types.Part(text=system_prompt)]),
        types.Content(role="model", parts=[types.Part(text="Okay, I will generate and modify form JSON based on the user's instructions, always starting my response with the JSON block.")])
    ]

    prompt_parts = []
    if current_json:
        # If there's a current form, frame the prompt as a modification request
        prompt_parts.append(types.Part(text=f"Here is the CURRENT_FORM_JSON:\\n```json\\n{json.dumps(current_json, indent=2)}\\n```\\n\\nNow, apply this instruction: {new_prompt}"))
    else:
        # Otherwise, it's a new form request
        prompt_parts.append(types.Part(text=new_prompt))
    
    # prompt_parts = [types.Part(text=new_prompt)]
    # if file_b64 and mime_type:
    #     try:
    #         header, encoded = file_b64.split(",", 1)
    #         file_data = base64.b64decode(encoded)
    #         prompt_parts.insert(0, types.Part(inline_data=types.Blob(mime_type=mime_type, data=file_data)))
    #     except Exception as e:
    #         return f"There was an error processing the uploaded file: {e}"

    api_contents.append(types.Content(role="user", parts=prompt_parts))
    
    try:
        # Use the globally initialized model

        response = client.models.generate_content(
            model=MODEL_NAME, 
            contents=api_contents, 
            config=GenerateContentConfig(tools=[get_lookup_values], temperature=0),)

        
        return response.text
    except Exception as e:
        return f"Sorry, an error occurred communicating with the AI: {e}"


def run_enhancement_action(form_json: dict, action: str, language: str = None) -> str:
    """Runs a specific enhancement task using a targeted prompt."""
    print(f"\n--- PREPARING TO CALL GEMINI API (ENHANCE: {action}) ---")
    
    prompts = {
        "translate": f"Translate all user-facing text in the following JSON object to {language}. Specifically, translate the values for 'form_name', 'page_name', 'display_name', 'help_text', and any strings in an 'options' array. Do NOT translate any other keys or values. Return ONLY the raw, complete, translated JSON object.",
        "analyze_compliance": "You are a compliance expert. Analyze the following form JSON for potential issues related to web accessibility (WCAG) and sensitive data handling (like PII or HIPAA). Provide a bulleted list of concerns and suggestions. Do not return JSON.",
        "suggest_workflows": "You are a business process automation consultant. Based on the following form, suggest 3 potential post-submission workflows. For each, describe the trigger, the action, and the systems involved. Do not return JSON.",
        "generate_help_text": "You are a UX writer. For the following form JSON, add a `help_text` key to each field object containing a concise, helpful instruction for the end-user. Return the complete, updated JSON object and nothing else."
    }
    
    if action not in prompts:
        return json.dumps({"error": "Invalid action"})

    full_prompt = f"{prompts[action]}\n\nForm JSON:\n```json\n{json.dumps(form_json, indent=2)}\n```"

    try:
        # Use the globally initialized client
        # Use a more powerful model for these nuanced tasks if needed, can also be an env variable
        # enhancement_model = genai.GenerativeModel(MODEL_NAME)
        response = client.models.generate_content(
            model=MODEL_NAME, 
            contents=[full_prompt], 
            config=GenerateContentConfig(temperature=0),)

        print(f"✅ Enhancement action '{action}' successful.")
        return response.text
    except Exception as e:
        print(f"🚨 ERROR during enhancement action: {e}")
        return json.dumps({"error": f"Failed to perform action '{action}': {e}"})