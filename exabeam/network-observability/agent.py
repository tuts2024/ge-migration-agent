import os
import uuid
import time
import random
import threading
import json
import io
from typing import Any, Dict, Generator
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt

from google.genai import Client
from google.genai import types
from google.adk.tools.tool_context import ToolContext

from google.cloud import pubsub_v1
from google.adk.agents.llm_agent import Agent
from google.adk.tools import agent_tool
from google.adk.tools.long_running_tool import LongRunningFunctionTool
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools import load_artifacts

# --- Configuration ---
MODEL_ID='gemini-2.5-flash'
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "learn-w-me") # Set this in your environment
PUBSUB_TOPIC_ID = os.environ.get("PUBSUB_TOPIC_ID", "network-anomalies")
client = Client()

# --- State Management ---
monitoring_tasks: Dict[str, Dict[str, Any]] = {}
analysis_tasks: Dict[str, Dict[str, Any]] = {}



# --- Pub/Sub Publisher Function ---
def publish_to_pubsub(project_id: str, topic_id: str, message: str):
    if not project_id or project_id == "xxx":
        print("🔥 PUBSUB WARNING: GCP_PROJECT_ID is not set. Cannot publish.", flush=True)
        return
    try:
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(project_id, topic_id)
        data = message.encode("utf-8")
        future = publisher.publish(topic_path, data)
        print(f"✅ PUBSUB: Published message ID {future.result()}", flush=True)
    except Exception as e:
        print(f"🔥 PUBSUB ERROR: {e}", flush=True)

def list_devices_and_status(region: str) -> dict[str, Any]:
    print(f"⚙️ DEVICE_LIST: Fetching active devices in {region}...")
    
    if region.lower() != 'us-central1':
        return {
            'status': 'error',
            'message': f'Device listing is only available for the us-central1 region in this demo.'
        }
    
    devices = [
        {'id': 'device-001', 'name': 'web-server-01', 'status': 'Warning'},
        {'id': 'device-002', 'name': 'database-server-01', 'status': 'Healthy'},
        {'id': 'device-003', 'name': 'load-balancer-01', 'status': 'Warning'},
        {'id': 'device-004', 'name': 'firewall-01', 'status': 'Healthy'}
    ]
    
    device_list_str = "\n".join([f"- {d['name']} ({d['id']}): Status: {d['status']}" for d in devices])
    
    return {
        'status': 'completed',
        'region': region,
        'devices': devices,
        'message': f'Found the following active devices in {region}:\n{device_list_str}\n\n'
                   f'Would you like to start monitoring any of these devices for anomalies?'
    }

def perform_rca(monitoring_id: str) -> dict[str, Any]:
    print(f"⚙️ RCA: Starting root cause analysis for {monitoring_id}...")
    task = monitoring_tasks.get(monitoring_id)
    if not task:
        return {'status': 'error', 'message': 'Unknown Monitoring ID'}
    
    anomalies_count = sum(1 for entry in task.get('log', []) if entry['packet']['resets'] > 50)
    
    if anomalies_count > 10:
        findings = f"Multiple anomalies detected ({anomalies_count}). This suggests a potential misconfiguration or a targeted attack on the network segment."
        recommendations = "Recommendation: Isolate the affected segment, review firewall rules, and inspect recent changes to the network configuration."
    elif anomalies_count > 0:
        findings = f"A few isolated anomalies were detected ({anomalies_count}). This could be due to a transient network issue or a single faulty device."
        recommendations = "Recommendation: Monitor the device for a longer period and check for firmware updates or known bugs."
    else:
        findings = "No significant anomalies found in the provided log data. The reported issues were likely false positives or a result of normal network behavior under specific load conditions."
        recommendations = "Recommendation: No immediate action required. Continue monitoring."
        
    return {
        'status': 'completed',
        'monitoring_id': monitoring_id,
        'findings': findings,
        'recommendations': recommendations
    }

# --- Data Science Agent Tools ---
def start_traffic_analysis(target_resource: str, time_window: str) -> dict[str, Any]:
    print(f"✅ DATA_SCIENCE: Staging data for '{target_resource}'...")
    analysis_id = f"analysis-{uuid.uuid4()}"
    source_data = []
    for task in monitoring_tasks.values():
        if task.get('log'): source_data = task['log']; break
    if not source_data: return {'status': 'error', 'message': 'Could not find monitoring data.'}
    analysis_tasks[analysis_id] = {'data': source_data}
    return {'status': 'pending', 'analysis_id': analysis_id}

async def check_analysis_status(analysis_id: str, tool_context: ToolContext) -> dict[str, Any]:
    print(f"⚙️ DATA_SCIENCE: Analyzing data and creating plot artifact for {analysis_id}...")
    task = analysis_tasks.get(analysis_id)
    if not task: return {'status': 'error', 'message': 'Unknown analysis ID.'}
    data = task['data']
    timestamps = [item['timestamp'] for item in data]
    resets = [item['packet']['resets'] for item in data]
    df = pd.DataFrame({'timestamp': pd.to_datetime(timestamps), 'resets': resets}).set_index('timestamp')
    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df['resets'], label='Normal Traffic', color='cornflowerblue')
    anomalies = df[df['resets'] > 50]
    plt.scatter(anomalies.index, anomalies['resets'], color='red', label='Anomaly Detected', s=50)
    plt.title('Network Traffic Analysis: TCP Resets'); plt.xlabel('Time'); plt.ylabel('Number of TCP Resets')
    plt.legend(); plt.tight_layout()
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png'); plt.close(); buffer.seek(0)
    image_bytes = buffer.read()
    plot_filename = f"{analysis_id}.png"
    plot_artifact = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
    version = await tool_context.save_artifact(filename=plot_filename, artifact=plot_artifact)
    print(f"✅ DATA_SCIENCE: Plot artifact '{plot_filename}' v{version} saved.")
    return {'status': 'completed', 'findings': 'Analysis complete. A plot has been generated.', 'artifact_filename': plot_filename, 'artifact_version': version}

async def generate_image(prompt: str, tool_context: ToolContext):
    print(f"🎨 IMAGE_AGENT: Generating image for prompt: '{prompt}'")
    response = client.models.generate_images(model='imagen-3.0-generate-002', prompt=prompt, config={'number_of_images': 1})
    if not response.generated_images: return {'status': 'failed'}
    image_bytes = response.generated_images[0].image.image_bytes
    version = await tool_context.save_artifact('generated_image.png', types.Part.from_bytes(data=image_bytes, mime_type='image/png'))
    print(f"✅ IMAGE_AGENT: Image artifact 'generated_image.png' v{version} saved.")
    return {'status': 'success', 'filename': 'generated_image.png', 'version': version}




# --- Monitoring Tool Logic (Unchanged) ---
def simulate_network_traffic() -> Generator[Dict[str, Any], None, None]:
    while True:
        if random.randint(1, 10) == 1: packet = {'type': 'TCP', 'resets': random.randint(100, 200)}
        else: packet = {'type': 'TCP', 'resets': random.randint(1, 20)}
        yield packet
        time.sleep(1)
def monitor_and_detect(monitoring_id: str, target_resource: str):
    print(f"▶️  Starting continuous monitoring thread for {target_resource}...", flush=True)
    traffic_generator = simulate_network_traffic()
    for packet in traffic_generator:
        if monitoring_id not in monitoring_tasks or monitoring_tasks[monitoring_id]['status'] == 'stopped':
            print(f"⏹️  Stopping background thread for {monitoring_id}", flush=True)
            break
        current_time = datetime.now()
        log_entry = {'timestamp': current_time, 'packet': packet}
        monitoring_tasks[monitoring_id]['log'].append(log_entry)
        if packet['resets'] > 50:
            print(f"🚨 ANOMALY on {target_resource}: {packet['resets']} TCP resets.", flush=True)
            message_payload = { "monitoring_id": monitoring_id, "target_resource": target_resource, "timestamp_utc": current_time.isoformat(), "anomaly_details": packet }
            publish_to_pubsub(GCP_PROJECT_ID, PUBSUB_TOPIC_ID, json.dumps(message_payload))
        else:
            print(f"👁️  Monitoring {target_resource}: {packet}", flush=True)
def start_monitoring(target_resource: str) -> dict[str, Any]:
    monitoring_id = f"monitor-{uuid.uuid4()}"
    print(f"✅ Initiating continuous monitoring for {target_resource}. ID: {monitoring_id}")
    monitoring_tasks[monitoring_id] = {'status': 'running', 'log': []}
    monitor_thread = threading.Thread(target=monitor_and_detect, args=(monitoring_id, target_resource), daemon=True)
    monitor_thread.start()
    return {'status': 'running', 'monitoring_id': monitoring_id, 'message': f"Monitoring has started for {target_resource}."}
def check_monitoring_status(monitoring_id: str) -> dict[str, Any]:
    print(f"⚙️ Checking status for Monitoring ID: {monitoring_id}")
    task = monitoring_tasks.get(monitoring_id)
    if not task: return {'status': 'error', 'message': 'Unknown Monitoring ID'}
    activity_log = []
    for entry in task.get('log', []):
        packet = entry['packet']
        if packet['resets'] > 50:
            activity_log.append(f"🚨 ANOMALY: High TCP resets detected ({packet['resets']}).")
        else:
            activity_log.append(f"👁️  Normal traffic: {packet}")
    activity_report = "\n".join(activity_log) if activity_log else "No new activity since last check."
    return {'status': task.get('status'), 'activity': activity_report}
def stop_monitoring(monitoring_id: str) -> dict[str, Any]:
    task = monitoring_tasks.get(monitoring_id)
    if task: task['status'] = 'stopped'
    return {'status': 'stopped', 'message': f"Successfully stopped monitoring for {monitoring_id}."}


    # --- Agent Definitions with Enhanced Instructions ---

data_science_agent = Agent(
    model=MODEL_ID,
    name="data_science_agent",
    # ENHANCED INSTRUCTION:
    instruction="""
       You are a data-specialist agent: a meticulous Data Scientist. Your purpose is to provide deep insights through data analysis and create visual representations.
       When a network analysis is requested, you will first use start_traffic_analysis to stage the data. Then, you will run check_analysis_status to process the data, detect anomalies, and generate a time-series plot. After the analysis is complete, you MUST summarize the findings in a clear, concise sentence. Then, present the artifact as the primary result, for example: "Analysis complete. I've generated a time-series plot that clearly visualizes the anomalies, and it's now available to view. The artifact is named '[artifact_filename]'."
    """,
    tools=[start_traffic_analysis, check_analysis_status, generate_image]
)

monitoring_agent = Agent(
    model=MODEL_ID,
    name="monitoring_agent",
    # ENHANCED INSTRUCTION:
    instruction="""
      You are a specialist Network Monitoring Agent, acting as the first line of defense for network health. Your purpose is to proactively watch network traffic for unusual patterns and alert the team.
      - When asked to `start_monitoring`, you should confirm the action and report the `monitoring_id` clearly, emphasizing its importance for tracking purposes. For example: "Monitoring has been initiated. Your monitoring ID is [monitoring_id]. I'll keep a close watch on traffic and let you know if anything significant arises."
      - When a user asks to list devices in a specific region, you should use the `list_devices_and_status` tool to provide the information and then proactively suggest monitoring for anomalies.
      - When you `check_monitoring_status` and find anomalies, you must act as a first responder. Summarize the anomalies found (e.g., "I've detected several anomalies, including high TCP resets.") and then proactively recommend the next steps, presenting a clear choice to the user: "To understand the root cause, I recommend a detailed visual analysis. Shall I proceed, or would you prefer a root cause analysis report?"
      - When requested to `perform_rca`, you will provide a detailed root cause analysis report based on the monitoring data. Present the findings and recommendations clearly and directly.
    """,
    tools=[start_monitoring, check_monitoring_status, stop_monitoring, perform_rca, list_devices_and_status],
)

root_agent = Agent(
    model=MODEL_ID,
    name="observability_supervisor",
    # ENHANCED INSTRUCTION:
    instruction="""
        You are the Observability Supervisor, the central command for a team of specialist agents. Your primary role is to act as the user's interface, understanding their needs and delegating tasks to the correct expert on your team. You do not perform tasks yourself.
        - For **monitoring network traffic**, **checking the status** of a monitor, **listing network devices**, or performing a **root cause analysis (RCA)**, you must delegate the task to the `monitoring_agent`.
        - For **in-depth data analysis**, **plotting anomalies**, or **generating creative images**, delegate the task to the `data_science_agent`.
        - When a user wants to **view a plot or image** that has been created, use the `load_artifacts` tool.
        - Always begin the conversation by introducing yourself and asking how you can help. Maintain a professional yet helpful demeanor throughout the conversation.
    """,
    tools=[
        agent_tool.AgentTool(monitoring_agent),
        agent_tool.AgentTool(data_science_agent),
        load_artifacts
    ],
)