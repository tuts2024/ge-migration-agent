import json
import requests
import google.auth
import google.auth.transport.requests

def inspect_agent():
    credentials, project = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    access_token = credentials.token

    base_url = "https://discoveryengine.googleapis.com/v1alpha"
    engine_id = "enterprise-search-17416389_1741638989378"
    endpoint = f"{base_url}/projects/404109417257/locations/global/collections/default_collection/engines/{engine_id}/assistants/default_assistant/agents"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "x-goog-user-project": "404109417257"
    }
    response = requests.get(endpoint, headers=headers)
    if response.status_code == 200:
        agents = response.json().get("agents", [])
        for agent in agents:
            if "NYC Weather Reporter" in agent.get("displayName", ""):
                print(json.dumps(agent, indent=2))
                break

if __name__ == "__main__":
    inspect_agent()
