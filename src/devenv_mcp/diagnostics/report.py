from typing import List, Dict, Any

from devenv_mcp.collectors.ports import collect_ports
from devenv_mcp.collectors.docker_collector import collect_containers
from devenv_mcp.collectors.processes import collect_processes

RESTART_COUNT_THRESHOLD = 2 # >= comparison for restarts
PROBLEMATIC_PROCESS_STATUSES = {'zombie', 'disk-sleep', 'stopped'}
CRITICAL_CONTAINER_STATUSES = {'exited', 'dead'}
PROBLEMATIC_CONTAINER_STATUSES = {'restarting'}
PROBLEMATIC_CONTAINER_HEALTH = {'unhealthy'}
CRASH_EXIT_CODES = {1, 137, 143}
PROBLEMATIC_PORT_STATES = {'CLOSE_WAIT', 'TIME_WAIT'}


def diagnose_ports(PORTS:List[int]):
    '''
    Diagnoses potential port-related issues based on state and usage.
    '''
    PORTS = list(set(PORTS))  # Ensure unique ports
    results = {key: {} for key in PORTS}

    clctd_ports = collect_ports()
    mtched_ports = [p for p in clctd_ports['ports'] if p['port'] in PORTS]
    ntmtched_ports = list(set(PORTS) - {p['port'] for p in mtched_ports})

    for port in ntmtched_ports:
        results[port]['status'] = 'not found'
        results[port]['issues'] = ['Port not found in active connections']

    clctd_processes = collect_processes()
    process_ids = set(p['pid'] for p in clctd_processes['processes'])

    clctd_containers = collect_containers()

    port_to_container = {}
    for container in clctd_containers['containers']:
        if not container['ports']:
            continue
        for port_info in container['ports'].values():
            if port_info:
                for binding in port_info:
                    if binding.get('HostPort') is not None:
                        host_port = int(binding['HostPort'])
                        port_to_container[host_port] = container

    for port in mtched_ports:
        port_number = port['port']
        pid = port['pid']
        issues = []
        process_severity = 'ok'
        container_severity = 'ok'
        port_severity = 'ok'
        severity = 'ok'

        if pid is not None and pid not in process_ids:
            issues.append('Port is open but associated process is not running')
            process_severity = 'warning'

        process = next((p for p in clctd_processes['processes'] if p['pid'] == pid), None)
        container = port_to_container.get(port_number)

        if process:
            if process['status'] in PROBLEMATIC_PROCESS_STATUSES:
                issues.append(f"Process status is {process['status']}")
                process_severity = 'warning'
        if container:
            if container['status'] in CRITICAL_CONTAINER_STATUSES:
                issues.append(f"Container status is {container['status']}")
                container_severity = 'critical'
            elif container['status'] in PROBLEMATIC_CONTAINER_STATUSES:
                issues.append(f"Container status is {container['status']}")
                container_severity = max(container_severity, 'warning', key=lambda s: ['ok', 'warning', 'critical'].index(s))
            if container['health'] in PROBLEMATIC_CONTAINER_HEALTH:
                issues.append(f"Container health is {container['health']}")
                container_severity = max(container_severity, 'warning', key=lambda s: ['ok', 'warning', 'critical'].index(s))
            
            if container['restart_count'] >= RESTART_COUNT_THRESHOLD and container['exit_code'] in CRASH_EXIT_CODES:
                issues.append(f"Container has restarted {container['restart_count']} times with exit code {container['exit_code']}")
                container_severity = max(container_severity, 'warning', key=lambda s: ['ok', 'warning', 'critical'].index(s))

        if port['status'] in PROBLEMATIC_PORT_STATES:
            issues.append(f"Port state is {port['status']}")
            port_severity = 'warning'

        if container_severity == 'critical':
            severity = 'critical'
        elif process_severity == 'warning' and container_severity == 'warning':
            severity = 'critical'   # combination rule
        elif 'warning' in (process_severity, container_severity, port_severity):
            severity = 'warning'


        results[port['port']]['status'] = port['status']
        results[port['port']]['severity'] = severity
        results[port['port']]['port_info'] = {
            'ip': port['ip'],
            'protocol': port['protocol'],
            'pid': port['pid'],
            'process_name': port['name'],
            'container_name': container['name'] if container else None
        }
        results[port['port']]['process'] = {
            'pid': process['pid'] if process else None,
            'name': process['name'] if process else None,
            'status': process['status'] if process else None,
            'memory_rss_mb': process['memory_rss_mb'] if process else None,
            'cpu_percent': process['cpu_percent'] if process else None
        } if process else None
        results[port['port']]['container'] = {
            'id': container['id'] if container else None,
            'name': container['name'] if container else None,
            'status': container['status'] if container else None,
            'health': container['health'] if container else None,
            'restart_count': container['restart_count'] if container else None,
            'exit_code': container['exit_code'] if container else None,
            'memory_limit_mb': container['memory_limit_mb'] if container else None
        } if container else None
        results[port['port']]['issues'] = issues if issues else ['No issues detected']
        
    
    return results

if __name__ == '__main__':
    import json
    PORTS_TO_DIAGNOSE = [80, 7260]
    diagnosis_result = diagnose_ports(PORTS_TO_DIAGNOSE)
    print(json.dumps(diagnosis_result, indent=2))