import json
import logging
from google.adk.agents.llm_agent import Agent
from google.adk.tools.tool_context import ToolContext
import google.auth
from google.auth.transport.requests import AuthorizedSession

PROJECT_NUMBER = "404109417257"
LOCATION = "global"
ENDPOINT_LOCATION = "global"

def get_session():
    credentials, project = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    return AuthorizedSession(credentials)

def list_notebooks(tool_context: ToolContext, project_number: str = PROJECT_NUMBER, location: str = LOCATION) -> str:
    """Call this tool to get a list of recently viewed notebooks.
    
    Args:
        project_number: The Google Cloud project number. Defaults to source project.
        location: The geographic location. Defaults to global.
    """
    session = get_session()
    url = f"https://{ENDPOINT_LOCATION}-discoveryengine.googleapis.com/v1alpha/projects/{project_number}/locations/{location}/notebooks:listRecentlyViewed"

    try:
        resp = session.get(url)
        resp.raise_for_status()
        data = resp.json()
        notebooks = data.get("notebooks", [])
        return json.dumps(notebooks)
    except Exception as e:
        return json.dumps({"error": str(e)})

def list_sources_and_types(tool_context: ToolContext, notebook_id: str, project_number: str = PROJECT_NUMBER, location: str = LOCATION) -> str:
    """Call this tool to list sources and their types for a specific notebook.

    Args:
        notebook_id: The ID of the notebook.
        project_number: The Google Cloud project number. Defaults to source project.
        location: The geographic location. Defaults to global.
    """
    session = get_session()
    base_url = f"https://{ENDPOINT_LOCATION}-discoveryengine.googleapis.com/v1alpha/projects/{project_number}/locations/{location}/notebooks/{notebook_id}"

    try:
        get_resp = session.get(base_url)
        get_resp.raise_for_status()
        nb_data = get_resp.json()
        sources = nb_data.get("sources", [])

        results = []
        for src in sources:
            src_id = src.get("sourceId", {}).get("id")
            src_title = src.get("title")

            src_url = f"{base_url}/sources/{src_id}"
            src_resp = session.get(src_url)
            src_resp.raise_for_status()
            src_data = src_resp.json()

            metadata = src_data.get("metadata", {})

            source_type = "copied text"
            source_location = "N/A"

            if "webpageMetadata" in metadata:
                source_type = "website"
                source_location = metadata["webpageMetadata"].get("webpageUrl")
            elif "googleDocsMetadata" in metadata:
                source_type = "google docs"
                doc_id = metadata["googleDocsMetadata"].get("documentId")
                source_location = f"https://docs.google.com/document/d/{doc_id}/edit"

            results.append({
                "title": src_title,
                "id": src_id,
                "type": source_type,
                "location": source_location
            })

        return json.dumps(results)
    except Exception as e:
        return json.dumps({"error": str(e)})

def create_notebook(tool_context: ToolContext, target_project_number: str, target_location: str, title: str) -> str:
    """Call this tool to create a new notebook in a target project.

    Args:
        target_project_number: The Google Cloud project number of the target app.
        target_location: The geographic location of the data store (e.g., global).
        title: The title of the notebook to create.
    """
    logging.info(f"DEBUG: create_notebook called with title='{title}', project='{target_project_number}', location='{target_location}'")
    session = get_session()
    endpoint_location = "global"
    url = f"https://{endpoint_location}-discoveryengine.googleapis.com/v1alpha/projects/{target_project_number}/locations/{target_location}/notebooks"

    try:
        resp = session.post(url, json={"title": title})
        resp.raise_for_status()
        data = resp.json()
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": str(e)})

def add_source_to_notebook(tool_context: ToolContext, target_project_number: str, target_location: str, notebook_id: str, source_content: str) -> str:
    """Call this tool to add a source to a notebook in a target project.

    Args:
        target_project_number: The Google Cloud project number of the target app.
        target_location: The geographic location of the data store.
        notebook_id: The ID of the notebook to add the source to.
        source_content: The JSON string of the userContent to add.
    """
    logging.info(f"DEBUG: add_source_to_notebook called with notebook_id='{notebook_id}', project='{target_project_number}'")
    session = get_session()
    endpoint_location = "global"
    url = f"https://{endpoint_location}-discoveryengine.googleapis.com/v1alpha/projects/{target_project_number}/locations/{target_location}/notebooks/{notebook_id}/sources:batchCreate"

    try:
        content_obj = json.loads(source_content)
        logging.info(f"DEBUG: Sending request to {url} with payload: {json.dumps(content_obj)}")
        resp = session.post(url, json={"userContents": [content_obj]}, timeout=60)
        logging.info(f"DEBUG: Response status: {resp.status_code}")
        logging.info(f"DEBUG: Response body: {resp.text}")
        resp.raise_for_status()
        data = resp.json()
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": str(e)})

def list_employee_agents(tool_context: ToolContext, project_id: str = PROJECT_NUMBER, location: str = LOCATION, engine_id: str = "enterprise-search-17416389_1741638989378") -> str:
    """Call this tool to list all employee-made low-code agents in a given engine.
    
    Args:
        project_id: The Google Cloud project number. Defaults to source project.
        location: The geographic location. Defaults to global.
        engine_id: The Discovery Engine engine ID containing the agents.
    """
    session = get_session()
    base_url = "https://discoveryengine.googleapis.com/v1alpha"
    parent = f"projects/{project_id}/locations/{location}/collections/default_collection/engines/{engine_id}/assistants/default_assistant"
    url = f"{base_url}/{parent}/agents"

    try:
        logging.info(f"DEBUG: list_employee_agents called for {parent}")
        resp = session.get(url)
        resp.raise_for_status()
        data = resp.json()
        agents = data.get("agents", [])
        
        employee_agents = []
        for agent in agents:
            if "lowCodeAgentDefinition" in agent:
                definition = agent.get("lowCodeAgentDefinition", {})
                nodes = definition.get("nodes", [])
                root_id = definition.get("rootAgentId")
                
                root_instructions = "No instructions found."
                root_tools = []
                sub_agents = []
                
                for node in nodes:
                    node_id = node.get("id")
                    llm_node = node.get("llmAgentNode", {})
                    node_instruction = llm_node.get("instruction", "No instructions found.")
                    
                    # Extract tools for this node
                    node_tools = []
                    for t in llm_node.get("selectedTools", {}).get("tool", []):
                        node_tools.append(t.get("name", "Unknown Tool"))
                    for spec in llm_node.get("dataStoreSpecs", {}).get("specs", []):
                        ds = spec.get("dataStore", "")
                        if ds:
                            ds_name = ds.split("/")[-1]
                            node_tools.append(f"DataStore: {ds_name}")
                        
                    if node_id == root_id:
                        root_instructions = node_instruction
                        root_tools = node_tools
                    else:
                        sub_agents.append({
                            "displayName": node.get("displayName", "Sub-Agent"),
                            "description": llm_node.get("description", ""),
                            "model": llm_node.get("model", "Unknown Model"),
                            "instructions": node_instruction,
                            "tools": node_tools
                        })

                employee_agents.append({
                    "displayName": agent.get("displayName"),
                    "name": agent.get("name"),
                    "description": agent.get("description"),
                    "instructions": root_instructions,
                    "connectors_and_tools": root_tools,
                    "sub_agents": sub_agents
                })
        return json.dumps(employee_agents)
    except Exception as e:
        return json.dumps({"error": str(e)})

def migrate_employee_agent(
    tool_context: ToolContext,
    source_agent_name: str,
    target_project_id: str,
    target_location: str,
    target_engine_id: str,
    source_project_id: str = PROJECT_NUMBER,
    source_location: str = LOCATION,
    source_engine_id: str = "enterprise-search-17416389_1741638989378"
) -> str:
    """Call this tool to migrate (create) an employee-made low-code agent to a target environment.
    
    Args:
        source_agent_name: The exact display name of the source agent to migrate (e.g., "QBR Generator").
        target_project_id: The Google Cloud project number of the target environment.
        target_location: The geographic location of the target environment.
        target_engine_id: The Discovery Engine engine ID of the target environment.
        source_project_id: The Google Cloud project number of the source environment.
        source_location: The geographic location of the source environment.
        source_engine_id: The Discovery Engine engine ID of the source environment.
    """
    session = get_session()
    base_url = "https://discoveryengine.googleapis.com/v1alpha"
    
    # 1. Fetch the source agent definition
    source_parent = f"projects/{source_project_id}/locations/{source_location}/collections/default_collection/engines/{source_engine_id}/assistants/default_assistant"
    source_url = f"{base_url}/{source_parent}/agents"
    
    try:
        logging.info(f"Fetching source agent from {source_url}")
        resp = session.get(source_url)
        resp.raise_for_status()
        agents = resp.json().get("agents", [])
        
        agent_to_migrate = None
        for agent in agents:
            if agent.get("displayName") == source_agent_name and "lowCodeAgentDefinition" in agent:
                agent_to_migrate = agent
                break
                
        if not agent_to_migrate:
            return json.dumps({"error": f"Source agent '{source_agent_name}' not found or is not a low-code agent."})
            
        # 2. Create the payload for the target environment
        target_parent = f"projects/{target_project_id}/locations/{target_location}/collections/default_collection/engines/{target_engine_id}/assistants/default_assistant"
        target_url = f"{base_url}/{target_parent}/agents"
        
        payload_str = json.dumps({
            "displayName": agent_to_migrate.get("displayName"),
            "description": agent_to_migrate.get("description", ""),
            "lowCodeAgentDefinition": agent_to_migrate.get("lowCodeAgentDefinition")
        })
        payload_str = payload_str.replace(f"projects/{source_project_id}", f"projects/{target_project_id}")
        payload_str = payload_str.replace(source_engine_id, target_engine_id)
        payload = json.loads(payload_str)
        
        logging.info(f"Creating new agent at target {target_url}")
        create_resp = session.post(target_url, json=payload)
        create_resp.raise_for_status()
        
        return json.dumps({
            "success": True,
            "message": f"Successfully migrated agent '{source_agent_name}' to target environment.",
            "target_agent": create_resp.json()
        })
    except Exception as e:
        error_detail = getattr(getattr(e, "response", None), "text", str(e))
        return json.dumps({"error": str(e), "detail": error_detail})

AGENT_INSTRUCTION = """
You are the Notebooklm Migration Agent. Your job is to migrate notebooks from one Gemini app to another, and to help users list employee-made agents.

Workflow:
1. List all notebook apps from the source app (using `list_notebooks`).
2. Ask the user which notebook they want to migrate, or if they want to migrate all of them.
3. Ask the user for the target Gemini Enterprise app details (Project Number and Location).
4. For each notebook to migrate:
   a. Get its sources and types using `list_sources_and_types`.
   b. Create a new notebook in the target app using `create_notebook`.
   c. For each source, map it to the correct format and add it to the new notebook using `add_source_to_notebook`.
5. List employee-made agents when requested using `list_employee_agents`.
6. Migrate (create) employee-made low-code agents to a target Gemini Enterprise environment using `migrate_employee_agent`. You MUST pass the provided source_project_id, source_location, and source_engine_id explicitly to the tool, along with the target parameters. Ensure all subagents, connectors, instructions, and configurations are faithfully copied to the target.

Mapping sources:
- Type "google docs": use "googleDriveContent" with documentId extracted from location URL and mimeType "application/vnd.google-apps.document". Do NOT include "sourceName" at the root of the object.
- Type "website": use "webContent" with url. Do NOT include "sourceName" at the root unless confirmed valid.
- Type "copied text": use "textContent" with content.
- Type "youtube": use "videoContent" with youtubeUrl.

Critical Rule: Do NOT delete the source notebook or its sources after migration. This is a read-and-copy operation only.

Output Format:
When presenting lists of notebooks or sources, you MUST use standard Markdown tables to make the output look grand and readable.
Do NOT output raw JSON or A2UI JSON, as the client cannot render it.

When a user asks for the details of an employee agent (e.g. "give details on QBR Generator"), output the details in exactly the following format without markdown code blocks:

[Agent Description]

Instructions: [Agent Instructions]

Model: [Model Name or "Gemini 3 Flash"]

Connectors: [List of connectors/tools/datastores]

Knowledge: None

SubAgent : [SubAgent Display Name]
Description: [SubAgent Description]
Instructions: [SubAgent Instructions]
Model: [SubAgent Model]
Connectors: [SubAgent Connectors]
Output Format: [SubAgent Output Format]
Label: [SubAgent Label]

"""

root_agent = Agent(
    model="projects/404109417257/locations/us-central1/publishers/google/models/gemini-2.5-flash",
    name="notebook_agent",
    description="Notebooklm Migration Agent that migrates notebooks between apps and lists custom agents.",
    instruction=AGENT_INSTRUCTION,
    tools=[list_notebooks, list_sources_and_types, create_notebook, add_source_to_notebook, list_employee_agents, migrate_employee_agent],
)
