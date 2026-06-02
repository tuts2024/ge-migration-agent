import json
import os
import subprocess
import sys
from google.adk.agents.llm_agent import Agent
from google.adk.tools.tool_context import ToolContext

PROJECT_NUMBER = os.environ.get("GEMINI_API_PROJECT")
LOCATION = "global"

def _run_cli(args_list: list) -> str:
    """Invokes the migrate.py CLI synchronously and returns its stdout."""
    agent_dir = os.path.dirname(os.path.abspath(__file__))
    migrate_py_path = os.path.join(os.path.dirname(agent_dir), "migrate.py")
    
    cmd = [sys.executable, migrate_py_path, "--json"] + args_list
    try:
        # Run subprocess inheriting current environment
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            env=os.environ
        )
        return res.stdout
    except subprocess.CalledProcessError as e:
        stderr_msg = e.stderr.strip() if e.stderr else str(e)
        return json.dumps({
            "success": False,
            "error": f"CLI command failed with exit code {e.returncode}.",
            "detail": stderr_msg
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to run CLI command: {str(e)}"
        })

def list_notebooks(tool_context: ToolContext, project_number: str = PROJECT_NUMBER, location: str = LOCATION) -> str:
    """Call this tool to get a list of recently viewed notebooks.
    
    Args:
        project_number: The Google Cloud project number. Defaults to source project.
        location: The geographic location. Defaults to global.
    """
    cmd = ["list-notebooks"]
    if project_number:
        cmd += ["--project", project_number]
    if location:
        cmd += ["--location", location]
    return _run_cli(cmd)

def list_sources_and_types(tool_context: ToolContext, notebook_id: str, project_number: str = PROJECT_NUMBER, location: str = LOCATION) -> str:
    """Call this tool to list sources and their types for a specific notebook.

    Args:
        notebook_id: The ID of the notebook.
        project_number: The Google Cloud project number. Defaults to source project.
        location: The geographic location. Defaults to global.
    """
    cmd = ["list-sources", notebook_id]
    if project_number:
        cmd += ["--project", project_number]
    if location:
        cmd += ["--location", location]
    return _run_cli(cmd)

def create_notebook(tool_context: ToolContext, target_project_number: str, target_location: str, title: str) -> str:
    """Call this tool to create a new notebook in a target project.

    Args:
        target_project_number: The Google Cloud project number of the target app.
        target_location: The geographic location of the data store (e.g., global).
        title: The title of the notebook to create.
    """
    cmd = ["create-notebook", title]
    if target_project_number:
        cmd += ["--target-project", target_project_number]
    if target_location:
        cmd += ["--target-location", target_location]
    return _run_cli(cmd)

def add_source_to_notebook(tool_context: ToolContext, target_project_number: str, target_location: str, notebook_id: str, source_content: str) -> str:
    """Call this tool to add a source to a notebook in a target project.

    Args:
        target_project_number: The Google Cloud project number of the target app.
        target_location: The geographic location of the data store.
        notebook_id: The ID of the notebook to add the source to.
        source_content: The JSON string of the userContent to add.
    """
    cmd = ["add-source-to-notebook", notebook_id, source_content]
    if target_project_number:
        cmd += ["--target-project", target_project_number]
    if target_location:
        cmd += ["--target-location", target_location]
    return _run_cli(cmd)

def migrate_notebook_pipeline(
    tool_context: ToolContext,
    notebook_id_or_title: str,
    target_project_number: str,
    target_location: str,
    source_project_number: str,
    source_location: str = "global"
) -> str:
    """Call this tool to migrate an entire notebook and all of its sources from source to target in a single execution.
    
    Args:
        notebook_id_or_title: The ID or Title of the source notebook to migrate.
        target_project_number: The Google Cloud project number of the target app.
        target_location: The geographic location of the target data store (e.g., global).
        source_project_number: The Google Cloud project number of the source app.
        source_location: The geographic location of the source data store (e.g., global).
    """
    cmd = ["migrate-notebook", notebook_id_or_title]
    if source_project_number:
        cmd += ["--source-project", source_project_number]
    if target_project_number:
        cmd += ["--target-project", target_project_number]
    if source_location:
        cmd += ["--source-location", source_location]
    if target_location:
        cmd += ["--target-location", target_location]
    return _run_cli(cmd)

def list_employee_agents(tool_context: ToolContext, project_id: str = PROJECT_NUMBER, location: str = LOCATION, engine_id: str = "enterprise-search-17416389_1741638989378") -> str:
    """Call this tool to list all employee-made low-code agents in a given engine.
    
    Args:
        project_id: The Google Cloud project number. Defaults to source project.
        location: The geographic location. Defaults to global.
        engine_id: The Discovery Engine engine ID containing the agents.
    """
    cmd = ["list-agents", "--engine-id", engine_id]
    if project_id:
        cmd += ["--project", project_id]
    if location:
        cmd += ["--location", location]
    return _run_cli(cmd)

def extract_agent_datastores(
    tool_context: ToolContext,
    source_agent_name: str,
    source_project_id: str = PROJECT_NUMBER,
    source_location: str = LOCATION,
    source_engine_id: str = "enterprise-search-17416389_1741638989378"
) -> str:
    """Call this tool to extract and list the names of datastores used by an agent and its subagents.
    
    Args:
        source_agent_name: The exact display name of the source agent (e.g., "QBR Generator").
        source_project_id: The Google Cloud project number of the source environment.
        source_location: The geographic location of the source environment.
        source_engine_id: The Discovery Engine engine ID of the source environment.
    """
    cmd = ["extract-datastores", source_agent_name, "--engine-id", source_engine_id]
    if source_project_id:
        cmd += ["--project", source_project_id]
    if source_location:
        cmd += ["--location", source_location]
    return _run_cli(cmd)

def migrate_employee_agent(
    tool_context: ToolContext,
    source_agent_name: str,
    target_project_id: str,
    target_location: str,
    target_engine_id: str,
    source_project_id: str = PROJECT_NUMBER,
    source_location: str = LOCATION,
    source_engine_id: str = "enterprise-search-17416389_1741638989378",
    force: bool = False
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
        force: Set to True to proceed with migration even if some dependencies (connectors/datastores) are missing in the target environment.
    """
    cmd = ["migrate-agent", source_agent_name, "--source-engine", source_engine_id, "--target-engine", target_engine_id]
    if source_project_id:
        cmd += ["--source-project", source_project_id]
    if target_project_id:
        cmd += ["--target-project", target_project_id]
    if source_location:
        cmd += ["--source-location", source_location]
    if target_location:
        cmd += ["--target-location", target_location]
    if force:
        cmd += ["--force"]
    return _run_cli(cmd)

def create_agent_from_gem(
    tool_context: ToolContext,
    name: str,
    instructions: str,
    target_project_id: str,
    target_engine_id: str,
    description: str = "",
    target_location: str = LOCATION
) -> str:
    """Call this tool to create a new Gemini Enterprise agent from a Gem definition (name and instructions).
    
    Args:
        name: The name of the Gem (will be used as agent display name).
        instructions: The custom instructions or prompt for the Gem.
        target_project_id: The target Google Cloud project number.
        target_location: The target location. Defaults to global.
        target_engine_id: The target Discovery Engine engine ID.
    """
    cmd = ["create-agent-from-gem", name, instructions, "--target-engine", target_engine_id]
    if target_project_id:
        cmd += ["--target-project", target_project_id]
    if target_location:
        cmd += ["--target-location", target_location]
    if description:
        cmd += ["--description", description]
    return _run_cli(cmd)

def import_gems_from_file(
    tool_context: ToolContext,
    file_path: str,
    target_project_id: str,
    target_engine_id: str,
    target_location: str = "global"
) -> str:
    """Call this tool to import multiple Gems from a local HTML file dump.
    
    Args:
        file_path: The absolute path to the HTML file containing Gems data.
        target_project_id: The target Google Cloud project number.
        target_engine_id: The target Discovery Engine engine ID.
        target_location: The target location. Defaults to global.
    """
    cmd = ["import-gems", file_path, "--target-engine", target_engine_id]
    if target_project_id:
        cmd += ["--target-project", target_project_id]
    if target_location:
        cmd += ["--target-location", target_location]
    return _run_cli(cmd)

def export_agent_to_gcs(
    tool_context: ToolContext,
    source_agent_name: str,
    object_name: str,
    bucket_name: str = "",
    source_project_id: str = PROJECT_NUMBER,
    source_location: str = LOCATION,
    source_engine_id: str = "enterprise-search-17416389_1741638989378"
) -> str:
    """Call this tool to export an employee-made low-code agent definition to a GCS bucket.
    
    Args:
        source_agent_name: The exact display name of the source agent to export.
        object_name: The name of the object (file path) in the bucket.
        bucket_name: The name of the GCS bucket to save the definition to. If not provided, reads from GCS_BUCKET_NAME env var.
        source_project_id: The Google Cloud project number of the source environment.
        source_location: The geographic location of the source environment.
        source_engine_id: The Discovery Engine engine ID of the source environment.
    """
    cmd = ["export-agent-gcs", source_agent_name, object_name, "--engine-id", source_engine_id]
    if bucket_name:
        cmd += ["--bucket", bucket_name]
    if source_project_id:
        cmd += ["--project", source_project_id]
    if source_location:
        cmd += ["--location", source_location]
    return _run_cli(cmd)

def import_agent_from_gcs(
    tool_context: ToolContext,
    object_name: str,
    target_project_id: str,
    target_location: str,
    target_engine_id: str,
    bucket_name: str = "",
) -> str:
    """Call this tool to import an agent definition from GCS and create it in a target environment.
    
    Args:
        object_name: The name of the object (file path) in the bucket.
        target_project_id: The Google Cloud project number of the target environment.
        target_location: The geographic location of the target environment.
        target_engine_id: The Discovery Engine engine ID of the target environment.
        bucket_name: The name of the GCS bucket containing the definition. If not provided, reads from GCS_BUCKET_NAME env var.
    """
    cmd = ["import-agent-gcs", object_name, "--target-engine", target_engine_id]
    if bucket_name:
        cmd += ["--bucket", bucket_name]
    if target_project_id:
        cmd += ["--target-project", target_project_id]
    if target_location:
        cmd += ["--target-location", target_location]
    return _run_cli(cmd)

AGENT_INSTRUCTION = """
You are the Gemini Enterprise App Migration Agent. Your job is to migrate notebooks from one Gemini app to another, and to help users list employee-made agents.

CRITICAL RULES:
1. **Always start the interaction by asking the user for source and target environment details.** Do not perform any default actions until these details are confirmed.
2. **Once the user provides these details, keep them in your memory and do not ask again** for the duration of the session unless requested by the user.
3. The user must specify source details (e.g., project number, project id, region, engine id) and target details (e.g., project number, project id, region, target engine id).
   *Example Source:* Project Number 404109417257, Project ID learn-w-me, Region global, Engine ID enterprise-search-17416389_1741638989378
   *Example Target:* Project Number 580163670732, Project ID ipg-corp, Region global, Target Engine ID gemini-enterprise-17782044_1778204475194

Workflow:
1. List all notebook apps from the source app (using `list_notebooks`).
2. Ask the user which notebook they want to migrate, or if they want to migrate all of them.
3. Ask the user for the target Gemini Enterprise app details (Project Number and Location).
4. To migrate a notebook:
   a. You should highly prefer using the `migrate_notebook_pipeline` tool to automatically list, create, map, and migrate the notebook and all of its sources in a single robust execution. This is the recommended way to perform migrations.
   b. Alternatively, you can use the individual tools step-by-step:
      i. Get sources and types using `list_sources_and_types`.
      ii. Create a new notebook in the target app using `create_notebook`.
      iii. For each source, map it to the correct format and add it to the new notebook using `add_source_to_notebook`.
5. List employee-made agents when requested using `list_employee_agents`.
6. Migrate (create) employee-made low-code agents to a target Gemini Enterprise environment using `migrate_employee_agent`. This will also implicitly save a backup to a GCS bucket.
7. Export employee-made low-code agents to a GCS bucket using `export_agent_to_gcs` when requested.
8. Import employee-made low-code agents from a GCS bucket to a target environment using `import_agent_from_gcs` when requested.
9. Create a new agent from Gem instructions using `create_agent_from_gem`. ALWAYS ask the user for the target project ID and engine ID before calling this tool!
10. Import multiple Gems from a local file dump using `import_gems_from_file`. ALWAYS ask the user for the target project ID and engine ID before calling this tool!


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
    model=f"projects/{os.environ.get('GEMINI_API_PROJECT')}/locations/{os.environ.get('GEMINI_API_LOCATION')}/publishers/google/models/gemini-2.5-flash",
    name="Navneet_Tuteja",
    description="Gemini Enterprise App Migration Agent that migrates notebooks between apps and lists custom agents.",
    instruction=AGENT_INSTRUCTION,
    tools=[list_notebooks, list_sources_and_types, create_notebook, add_source_to_notebook, migrate_notebook_pipeline, list_employee_agents, migrate_employee_agent, export_agent_to_gcs, import_agent_from_gcs, create_agent_from_gem, import_gems_from_file],
)
