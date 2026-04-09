from agents.notebook_agent.agent import migrate_employee_agent

result = migrate_employee_agent(
    tool_context=None,
    source_agent_name="NYC Weather Reporter",
    target_project_id="1031943295592",
    target_location="global",
    target_engine_id="ge-target_1775590244233",
    source_project_id="404109417257",
    source_location="global",
    source_engine_id="enterprise-search-17416389_1741638989378"
)

print(result)
