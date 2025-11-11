import subprocess
import json


def test_tools_list():
    proc = subprocess.Popen(
        ["openproj-mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # The MCP protocol requires proper initialization first
    # Send initialize request
    init_req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    }
    proc.stdin.write(json.dumps(init_req) + "\n")
    proc.stdin.flush()

    # Read initialize response
    init_response = proc.stdout.readline().strip()
    assert init_response
    init_data = json.loads(init_response)
    assert "result" in init_data

    # Send initialized notification
    initialized_notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    proc.stdin.write(json.dumps(initialized_notif) + "\n")
    proc.stdin.flush()

    # Now send tools/list request
    tools_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    proc.stdin.write(json.dumps(tools_req) + "\n")
    proc.stdin.flush()

    line = proc.stdout.readline().strip()
    assert line, "No output from tools/list"
    data = json.loads(line)
    assert "result" in data
    assert "tools" in data["result"]

    proc.kill()
