import json
import requests
import google.auth
import google.auth.transport.requests

def list_employee_agents(project_id, location, engine_id, collection_id="default_collection", assistant_id="default_assistant"):
    """
    Fetches a list of agents and their metadata from Gemini Enterprise,
    specifically targeting employee-made agents.
    """
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
    parent = f"projects/{project_id}/locations/{location}/collections/{collection_id}/engines/{engine_id}/assistants/{assistant_id}"
    url = f"{base_url}/{parent}/agents"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    print(f"Fetching agents from: {parent}...")
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        agents = data.get("agents", [])
        print(f"Found {len(agents)} agents.")
        
        # Filter and display employee-made agents
        employee_agents = []
        for agent in agents:
            # Employee-made low-code agents typically have a lowCodeAgentDefinition
            if "lowCodeAgentDefinition" in agent:
                employee_agents.append(agent)
        
        print(f"\n--- Found {len(employee_agents)} Employee-Made Agents ---\n")
        for idx, agent in enumerate(employee_agents, 1):
            print(f"{idx}. Display Name: {agent.get('displayName')}")
            print(f"   ID/Name: {agent.get('name')}")
            print(f"   Description: {agent.get('description', 'N/A')}")
            print(f"   Created At: {agent.get('createTime')}")
            print(f"   State: {agent.get('state', 'N/A')}")
            print("-" * 50)
    else:
        print(f"Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    PROJECT_ID = "404109417257"
    LOCATION = "global"
    ENGINE_ID = "enterprise-search-17416389_1741638989378"
    
    list_employee_agents(PROJECT_ID, LOCATION, ENGINE_ID)
