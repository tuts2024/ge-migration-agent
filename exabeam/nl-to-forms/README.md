
# AI-Powered Form Generator Demo

## Vision

From a single sentence to a fully interactive form in seconds, this demo showcases a future where form creation is a conversation, not a configuration.

## Overview

This project is a high-fidelity prototype demonstrating how Google's **Vertex AI** and **Gemini models** can be integrated into a platform  to revolutionize the form creation process. Instead of manually dragging and dropping fields, administrators can simply describe their needs in plain English. The AI interprets the request, consults a pre-defined data dictionary (`metadata.csv`), and generates a suggested form.

The true innovation is in the editing process, where the administrator can continue to use natural language to collaboratively refine the form with the AI, making for an unprecedentedly fast and intuitive workflow.

## Features

This demo showcases a complete, end-to-end workflow:

* **Natural Language to Form**: Users can initiate form creation with a simple English sentence (e.g., "I need a work order for site inspections").
* **Contextual Field Generation**: The AI uses a `metadata.csv` file as a company's data dictionary to intelligently select relevant fields and their properties.
* **Smart Field Type Guessing**: Gemini automatically suggests the best HTML input type for each field (Text, Dropdown, Radio Buttons, Checklist) based on the metadata and context.
* **Interactive Form Editor ("The Canvas")**:
    * **Manual Editing**: Full control to change display names, field types, and options for dropdowns/radios.
    * **Drag-and-Drop Reordering**: Easily change the order of questions.
    * **Add/Delete Fields**: Remove unwanted fields or add new ones from scratch.
* **Creative AI-Powered Refinement**:
    * A **Natural Language Command Bar** allows the user to make further edits by typing commands.
    * **Real-time Updates**: The form canvas dynamically updates based on AI-driven commands like:
        * "Change 'Inspector Name' to 'Lead Inspector'"
        * "Add a text field for notes at the end"
        * "Make the priority level a dropdown instead of radio buttons"
        * "Remove the job title field"

## How It Works: The Flow

1.  **Initial Prompt**: The user visits the main page and types a description of the form they need.
2.  **AI Generation**: The Flask backend sends this prompt, along with the entire `metadata.csv` context, to the Gemini AI model. Gemini returns a structured JSON object representing the suggested fields.
3.  **Interactive Editing**: The application renders the "Edit & Validate Fields" page. This page is a dynamic, client-side application where the user can manually edit the form or use the AI command bar.
4.  **AI Refinement (Optional)**: If the user types a command and clicks "Apply AI Edit," the JavaScript captures the current state of the form and the command. It sends both to a second AI endpoint, which returns a new, modified JSON structure. The page then redraws the form to reflect the changes.
5.  **Final Creation**: Once satisfied, the user clicks "Create Final Form." The final structure is submitted, and the backend renders the definitive HTML form.

## Tech Stack

* **Backend**: Python 3, Flask
* **AI**: Google Cloud Vertex AI with the `gemini` model
* **Data Handling**: Pandas
* **Frontend**: HTML5, CSS3, Vanilla JavaScript
* **Third-Party Libraries**: SortableJS (for drag-and-drop functionality)

---

## Setup and Installation

Follow these steps to get the demo running on your local machine.

### 1. Prerequisites

* You must have a Google Cloud Project with the **Vertex AI API** enabled.
* You must have the `gcloud` CLI installed and authenticated. Run the following command to set up your Application Default Credentials:

    ```bash
    gcloud auth application-default login
    ```

### 2. Get the Files

Ensure you have the following two files in a single project directory :

* `app.py`
* `metadata.csv`

### 3. Set up a Virtual Environment (Recommended)

Using a virtual environment is recommended to manage project dependencies and avoid conflicts with other Python projects.

```bash
sudo apt update
sudo apt install python3-venv
python3 -m venv form
source form/bin/activate
```

If you are on Windows, the activation command might be different (e.g., `.\form\Scripts\activate`).

### 4. Install Dependencies

With your virtual environment activated, open your terminal in the project directory and install the required Python libraries:

```bash
pip install Flask pandas google-generativeai
```

### 5. Configure the Project ID

Open the `app.py` file in a text editor.

Find the line `PROJECT_ID = "learn-w-me"` and change the value to your actual Google Cloud Project ID.

## Running the Application

With your terminal in the project directory and your virtual environment activated, run the following command:

```bash
python app.py
```

You will see output indicating the server has started, including:

```
✅ Starting Flask App for forms AI Demo on http://127.0.0.1:5000
```

Open your web browser and navigate to `http://127.0.0.1:5000`.

### Prompts to Try

Once the application is running, try entering prompts like these in the form generator:

Showcase 1: From Physical to Digital in Seconds

* "I need a work order form to track the service type and priority level for the job, plus the inspector's name."

    Click "📎 Attach File" and select the handwritten HealthForm_1920.png image.
    - "Digitize this handwritten patient intake form. Please organize it into logical pages for 'Patient Information' and 'Medical History'."
    - Click the "🤖 AI Actions" button on the AI's response.
    Select "Analyze for Compliance".
    Prompt - Can you add Aria label?
    - Click "🤖 AI Actions".
    Select "Suggest Workflows".

Showcase 2: From Raw Data to Perfect Form
- Click "Start New Build".
    Upload a simple CSV file named leads.csv (you can create this in a text editor).
    Use this prompt:
    Prompt: "Here is a CSV export from our old sales system. Build a new lead capture form designed to capture this exact data structure."

Showcase 3: Conversational Development & Complex Logic
- Click "Start New Build".
    Prompt 1: > "Create a form for IT hardware requests. Include 'Employee Name' and a dropdown for 'Device Type' with options for Laptop, Monitor, and Keyboard."
    Prompt 2 (after it appears): > "That's perfect. Now, add a 'Laptop Model' dropdown with options for MacBook Pro and Dell XPS, but only show it if the user selects 'Laptop' as the Device Type."


---

## File Structure

Your project directory should look like this to begin:

```
/forms-ai-demo/
├── app.py          # The main Flask application
└── metadata.csv    # The data dictionary for the AI
```

---

## Future Enhancements

This demo provides a strong foundation that can be extended with more advanced features:

* **Connect to a Real Database**: Swap the `metadata.csv` file with a connection to a real SQL or NoSQL database for enterprise-grade data management.
* **User-Specific Pre-population**: Integrate user data to pre-fill known fields (e.g., "Inspector Name," "Employee ID") when a form is opened.
* **Advanced Conditional Logic**: Allow the AI to understand and create rules like, "Only show the 'Reason for Repair' field if the 'Service Type' is 'Repair'."
* **Saving and Loading Templates**: Allow users to save their edited form designs as templates for future use.