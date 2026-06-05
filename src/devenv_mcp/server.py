from typing import List,Dict
from fastmcp import FastMCP
from .diagnostics import report
import json

mcp = FastMCP(
    name="devenv_mcp")

def _filter_result(results):
    filtered = {}
    for key, value in results.items():
        if value.get('severity') == 'ok':
            if isinstance(key, int):
                filtered[key] = {'severity' : value.get('severity'),
                                 'issues' : value.get('issues')
                }
            elif value.get('present',0):
                filtered[key] = { 'severity' : value.get('severity'),
                                  'service' : value.get('service'),
                                  'issues' : value.get('issues')
                }
            else:
                if value.get('issues',0):
                    filtered[key] = { 'severity' : value.get('severity'),
                                      'container': {
                                            'id': value.get('container_info')['id'],
                                            'name': value.get('container_info')['name'],
                                            'status': value.get('container_info')['status']
                                        },
                                       'issues' : value.get('issues')
                    }
                else:
                    filtered[key] = { 'severity' : value.get('severity'),
                                      'container': {
                                            'id': value.get('container_info')['id'],
                                            'name': value.get('container_info')['name'],
                                            'status': value.get('container_info')['status']
                                        },
                                      'ports' : value.get('ports')
                    }
        else:
            filtered[key] = value
    return filtered


@mcp.tool
def diagnose_ports(ports: List[int])->str:
    """
    Diagnoses port-related issues by correlating port state, owning process,
    and linked Docker container for each requested port.

    Pass a list of port numbers to check. Returns a severity-filtered report:
    - 'ok': port, process, and container are all in normal state
    - 'warning': one signal is abnormal (zombie process, unhealthy container,
    problematic port state)
    - 'critical': multiple signals are abnormal, or container is dead/exited
    while holding the port

    Does not diagnose code errors, suggest fixes, or interpret application behaviour.
    """

    raw_result = report.diagnose_ports(ports)
    filtered = _filter_result(raw_result)
    return json.dumps(filtered, separators=(',', ':'))

@mcp.tool()
def diagnose_containers(containers: List[str])->str:
    """
    Diagnoses container-related issues by correlating container state, health, restart history,
    and mapped port states for each requested container.

    Pass a list of container name to check. Returns a severity-filtered report:
    - 'ok': container is running and healthy, all mapped ports are in normal state
    - 'warning': container is unhealthy, restarting, or has crash restarts;
    or a mapped port is in a problematic state
    - 'critical': container is dead or exited; or both container and process
    signals are abnormal

    Does not diagnose code errors, suggest fixes, or interpret application behaviour.
    """

    raw_result = report.diagnose_containers(containers)
    filtered = _filter_result(raw_result)
    return json.dumps(filtered, separators=(',', ':'))

@mcp.tool
def diagnose_environment(variables: List[Dict])->str:
    """
    Diagnoses environment variable issues by correlating variable presence
    and value state with linked service availability (ports and containers).

    Pass a list of variable descriptors to check — each with a variable name
    and optional port or container to correlate against. Returns a severity-filtered report:
    - 'ok': variable is present, non-empty, and linked service is running
    - 'warning': variable is missing with no service to correlate against;
    or variable is missing but the linked service is still running
    - 'critical': variable is present but linked service is not running;
    or variable is missing and linked service is also down;
    or variable exists but is empty

    Does not interpret variable values, suggest fixes, or diagnose application behaviour.
    """

    raw_result = report.diagnose_environment(variables)
    filtered = _filter_result(raw_result)
    return json.dumps(filtered, separators=(',', ':'))

def main():
    mcp.run()

if __name__ == "__main__":
    main()