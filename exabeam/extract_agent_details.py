import json
import requests
import google.auth
import google.auth.transport.requests

def extract_detailed_agents(project_id, location, engine_id, output_file):
    try:
        credentials, project = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
    except Exception as e:
        print(f"Failed to load Google Cloud credentials: {e}")
        return

    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    access_token = credentials.token

    base_url = "https://discoveryengine.googleapis.com/v1alpha"
    parent = f"projects/{project_id}/locations/{location}/collections/default_collection/engines/{engine_id}/assistants/default_assistant"
    url = f"{base_url}/{parent}/agents"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        agents = data.get("agents", [])
        
        markdown_content = "# Employee-Made Agents: Comprehensive Details\n\n"

        count = 0
        for agent in agents:
            if "lowCodeAgentDefinition" in agent:
                count += 1
                display_name = agent.get("displayName", "Unknown Agent")
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
                            "name": node.get("displayName", "Sub-Agent"),
                            "instructions": node_instruction,
                            "tools": node_tools
                        })

                markdown_content += f"## {count}. {display_name}\n\n"
                markdown_content += "### Root Agent Instructions\n"
                markdown_content += f"```text\n{root_instructions}\n```\n\n"
                
                markdown_content += "### Root Agent Connectors & Tools\n"
                if root_tools:
                    for t in root_tools:
                        markdown_content += f"- `{t}`\n"
                else:
                    markdown_content += "- None configured\n"
                
                if sub_agents:
                    markdown_content += "\n### Sub-Agents\n"
                    for idx, sub in enumerate(sub_agents, 1):
                        markdown_content += f"#### Sub-Agent {idx}: {sub['name']}\n"
                        markdown_content += "**Instructions:**\n"
                        markdown_content += f"```text\n{sub['instructions']}\n```\n"
                        markdown_content += "**Connectors & Tools:**\n"
                        if sub["tools"]:
                            for t in sub["tools"]:
                                markdown_content += f"- `{t}`\n"
                        else:
                            markdown_content += "- None configured\n"
                
                markdown_content += "---\n\n"

        with open(output_file, "w") as f:
            f.write(markdown_content)
        
        print(f"Successfully extracted {count} detailed agents to {output_file}")
    else:
        print(f"Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    PROJECT_ID = "404109417257"
    LOCATION = "global"
    ENGINE_ID = "enterprise-search-17416389_1741638989378"
    OUTPUT_FILE = "/usr/local/google/home/ntuteja/.gemini/jetski/brain/952e536a-f572-466a-83db-56ef3916e50c/comprehensive_agents_details.md"
    
    extract_detailed_agents(PROJECT_ID, LOCATION, ENGINE_ID, OUTPUT_FILE)
