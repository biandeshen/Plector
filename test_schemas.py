from core.agent_loop import AgentLoop
a = AgentLoop()
schemas = a.tool_registry.get_tool_schemas()
for s in schemas:
    assert s['type'] == 'function'
    assert s['function']['strict'] == True
    assert s['function']['parameters']['additionalProperties'] == False
print('OK: 所有 Schema 符合 OpenAI Function Calling 格式')
