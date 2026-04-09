"""
doform_text_to_form_upgraded.py

This script uses the Gemini API's function calling to dynamically generate
and modify a complex, nested JSON structure for web forms.
"""

# 1. SETUP AND INSTALLATION
# %pip install -qU 'google-genai>=1.0.0'
# %pip install -qU 'pandas'

import csv
import json
import pandas as pd
# from google.colab import userdata # Use this for API keys in Colab
from google import genai
from google.genai import types
from typing import Optional, List
import re, os
from dotenv import load_dotenv
load_dotenv()

project_id = os.getenv("GCP_PROJECT_ID")
location = os.getenv("GCP_LOCATION")
model_id = os.getenv("MODEL_ID") 

def extract_json_from_response(text):
    """Extracts the JSON string from a Markdown code block."""
    # The pattern looks for a ```json block and captures everything inside it
    match = re.search(r'```json\n(.*)\n```', text, re.DOTALL)
    if match:
        # group(1) returns the content of the first capturing group
        return match.group(1)
    # Return None if no JSON block is found
    return None

# 2. FILE AND TOOL SETUP
def setup_lookup_file():
    """Creates the lookups.json file for the tool to use."""
    print("Setting up lookups.json file...")
    lookup_data = {
      "state_codes": ["AL", "FL", "GA", "NC", "SC", "TN"],
      "issue_urgency": ["Low", "Medium", "High", "Critical"],
      "parts": [
        {"part_name": "Aerator-Long Spike", "price": 39.99},
        {"part_name": "3-Prong Hand Weeder", "price": 16.99},
        {"part_name": "Carrot Seeds", "price": 0.99}
      ]
    }
    with open('lookups.json', 'w') as f:
        json.dump(lookup_data, f, indent=2)
    print("✅ lookups.json created.")

# 2. DEFINE THE TOOL (FUNCTION) FOR THE MODEL
def get_lookup_values(field_name: Optional[str] = None) -> List[str]:
    """
    Looks up values from a local JSON file. If field_name is provided, it returns
    the corresponding values. If field_name is None, it returns all
    unique lookup names (the top-level keys).
    """
    print(f"--- TOOLBOX: Performing lookup from lookups.json for: '{field_name}' ---")
    try:
        with open('lookups.json', 'r') as f:
            data = json.load(f)
        if field_name is None:
            return list(data.keys())
        else:
            return data.get(field_name, [])
    except Exception as e:
        print(f"🚨 ERROR in get_lookup_values: {e}")
        return []

# 3. CONFIGURE THE MODEL AND SYSTEM PROMPT

# --- Define the  System Prompt for the Gemini Model ---
#  It teaches the model the complex schema
# and how to interact with the user.
def get_system_prompt():
    """Generates the detailed system prompt for the model."""
    try:
        with open('lookups.json', 'r') as f:
            data = json.load(f)
        available_lookups = list(data.keys())
    except Exception:
        available_lookups = "Not available"

    
    system_prompt = f"""

    You are a specialized AI assistant for creating and modifying complex JSON form definitions.

    **Primary Directive:**
    Your goal is to help the user build a form definition step-by-step. You must strictly adhere to the JSON schema provided below. When the user provides a new instruction, you will modify the `CURRENT_FORM_JSON` and return the complete, updated JSON.

    **Interaction Protocol:**
    1.  **ASK for Clarification:** For complex elements like `grid`, `table`, or `stack`, you MUST ask the user for details before generating the JSON. For example, if the user says "add a table for parts," you MUST ask, "Great! What columns should the parts table have?"
    2.  **Acknowledge and Confirm:** After generating the JSON, provide a brief, friendly confirmation that you have completed the request.
    3.  **Output Format:** Your response MUST START with a Markdown JSON code block (```json ... ```) containing the *entire and complete* form JSON. Conversational text MUST come AFTER the JSON block.

    **JSON Schema Definition:**
    The root object has a `form_name` (string) and `fields` (an array of field objects).

    **Field/Container Objects:**
    **Every object in the `fields` array MUST contain the following base keys:**
    **- `display_name` (string): The user-visible label for the field (e.g., "First Name").**
    **- `field_id` (string): A unique, computer-friendly identifier, usually in snake_case (e.g., "first_name").**
    **- `type` (string): The type of the field, chosen from the lists below.**

    **1. Container Types:**
        - `type: "grid"`: A container to lay out fields in columns. `columns` (number), `fields` (array).
        - `type: "stack"`: A container to group fields vertically. `fields` (array).
        - `type: "table"`: A container for repeating rows of data. `row_count` (number, optional), `fields` (array).

    **2. Basic Field Types:**
        - `type: "text"`: A single-line text input. Can have `line_count` > 1 for a textarea.
        - `type: "numeric"`, `type: "date"`, `type: "datetime"`, `type: "currency"`.
        - `type: "autonumber"`: Automatically generates a number. `prefix` (string, optional).
        - `type: "label"`: Just displays text. Use `hint` for the text content.
        - `type: "signature"`, `type: "image"`, `type: "barcode"`, `type: "gps"`, `type: "attachment"`, `type: "sketch"`.

    **3. Selection Field Types:**
        - `type: "radiogroup"`, `type: "checkboxgroup"`: `options` (array of strings), `direction` ("row" or "column").
        - `type: "combobox"`: A dropdown list. `options` (array of strings).
        - `type: "lookup"`: A searchable dropdown for complex objects. `items` (array of objects), `value` (string).

    **4. Dynamic/Calculated Attributes:**
        - `formula` (string): Defines a calculation. Example: `"formula": "quantity*price"`. For aggregation, use `sum(field_id)`.
        - `source` (string): Populates a field based on another. Example: `"source": "part.price"`.
        - `required` (boolean, optional), `hint` (string, optional).

    **Tool Usage (for `combobox` or `lookup`):**
    - If the user asks for a field with predefined choices, you MUST use the `get_lookup_values` tool.
    - Available lookup fields for the tool: **{available_lookups}**

    """

    return system_prompt

# 4. INITIALIZE CLIENT AND CHAT FOR VERTEX AI

def initialize_chat(project_id: str, location: str):
    """
    Initializes and returns the Gemini chat client and session via Vertex AI.

    Args:
        project_id (str): Your Google Cloud project ID.
        location (str): The Google Cloud location for your project (e.g., "us-central1").
    """

    
    # Define the model and generation config

    gen_config = types.GenerateContentConfig(
        temperature=0.1,
        system_instruction=get_system_prompt(),
        tools=[get_lookup_values],
    )

    # Initialize the client for Vertex AI
    print(f"Initializing client for Vertex AI project '{project_id}' in '{location}'...")
    client = genai.Client(vertexai=True, project=project_id, location=location)
    
    # Create a new chat session using the Vertex AI client
    # The model name for this client does not require the 'models/' prefix.
    chat = client.chats.create(
        model=model_id,
        config=gen_config
    )
    print("✅ Gemini chat session via Vertex AI initialized successfully.")
    return chat


# 5. MAIN CHAT LOOP
def run_chat():
    """Main function to run the interactive chat session."""
    setup_lookup_file()

    chat_session = initialize_chat(project_id=project_id, location=location)

    if not chat_session:
        print("Exiting due to initialization failure.")
        return

    current_form_json = {} 

    print("\n--- Form Generation Assistant (Vertex AI) ---")
    print("Hello! I'm here to help you build a form. Type 'exit' to end.")
    print("You can start by saying something like 'Create a customer sales form'.")

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == 'exit':
            print("Goodbye!")
            break

        prompt = f"""
        **Instruction:**
        {user_input}

        **CURRENT_FORM_JSON:**
        {json.dumps(current_form_json, indent=4)}
        """

        try:
            print("... Gemini is thinking ...")
            response = chat_session.send_message(prompt)
            
            json_str = extract_json_from_response(response.text)
            conversation_text = re.sub(r'```json\n(.*)\n```', '', response.text, flags=re.DOTALL).strip()

            if json_str:
                print("\n--- Updated Form JSON ---")
                print(json_str)
                try:
                    current_form_json = json.loads(json_str)
                except json.JSONDecodeError:
                    print("🚨 Warning: Model returned invalid JSON. State not updated.")

            if conversation_text:
                print("\n--- Gemini's Reply ---")
                print(conversation_text)

        except Exception as e:
            print(f"🚨 An error occurred: {e}")


# --- Start the application ---
if __name__ == "__main__":
    # NOTE: To run this in a non-Colab environment, you'll need to manage
    # your API key and dependencies (pip install google-generativeai pandas).
    # You might need to remove or adjust the `from google.colab import userdata` line.
    run_chat()