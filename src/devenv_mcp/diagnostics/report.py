from typing import List, Dict, Any

from devenv_mcp.collectors.ports import collect_ports
from devenv_mcp.collectors.docker_collector import collect_containers
from devenv_mcp.collectors.processes import collect_processes
from devenv_mcp.collectors.env import collect_env

RESTART_COUNT_THRESHOLD = 2 # >= comparison for restarts
PROBLEMATIC_PROCESS_STATUSES = {'zombie', 'disk-sleep', 'stopped'}
CRITICAL_CONTAINER_STATUSES = {'exited', 'dead'}
PROBLEMATIC_CONTAINER_STATUSES = {'restarting'}
PROBLEMATIC_CONTAINER_HEALTH = {'unhealthy'}
CRASH_EXIT_CODES = {1, 137, 143}
PROBLEMATIC_PORT_STATES = {'CLOSE_WAIT', 'TIME_WAIT'}

ACTIVE_PORT_STATUSES = {'LISTEN','ESTABLISHED'}
ACTIVE_CONTAINER_STATUSES = {'running'}


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

def diagnose_containers(containers:List[str]):
    '''
        Diagnosis Potential Container Related Issues
    '''

    containers = list(set(containers))
    results = {key : {} for key in containers}


    clctd_containers = collect_containers()
    mtchd_containers = [c for c in clctd_containers['containers'] if c['name'] in containers]
    named_mtchd_containers = {c['name']:c for c in mtchd_containers}
    ntmtchd_containers = list(set(containers) - {c['name'] for c in mtchd_containers})


    clctd_ports = collect_ports()
    clctd_ports = {key['port']: key for key in clctd_ports['ports']}

    container_to_port = {key['name']:[] for key in mtchd_containers}

    for container in ntmtchd_containers:
        results[container]['status'] = 'not found'
        results[container]['issues'] = ['Container is not Running.']
        results[container]['ports'] = []

    for container in mtchd_containers:
        ports = container['ports']
        if not ports:
            continue            
        for port_info in ports.values():
            if port_info:
                for binding in port_info:
                    if binding.get('HostPort') is not None:
                        host_port = int(binding['HostPort'])
                        port_data = clctd_ports.get(host_port)
                        if port_data:
                            container_to_port[container['name']].append(port_data)

    clctd_processes = collect_processes()
    process_ids = set(p['pid'] for p in clctd_processes['processes'])
    

    for container_name in container_to_port:
        ports = container_to_port[container_name]
        overall_severity = 'ok'
        severities = []
        container = named_mtchd_containers[container_name]
        
        if ports:
            for port in ports:
                port_number = port['port']
                pid = port['pid']
                issues = []
                process_severity = 'ok'
                container_severity = 'ok'
                port_severity = 'ok'
                severity = 'ok'

                result = {}
                result[port['port']] = {}

                if pid is not None and pid not in process_ids:
                    issues.append('Port is open but associated process is not running')
                    process_severity = 'warning'

                process = next((p for p in clctd_processes['processes'] if p['pid'] == pid), None)

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

                severities.append(severity)
                result[port['port']]['status'] = port['status']
                result[port['port']]['severity'] = severity
                result[port['port']]['port_info'] = {
                    'ip': port['ip'],
                    'protocol': port['protocol'],
                    'pid': port['pid'],
                    'process_name': port['name'],
                    'container_name': container['name'] if container else None
                }
                result[port['port']]['process'] = {
                    'pid': process['pid'] if process else None,
                    'name': process['name'] if process else None,
                    'status': process['status'] if process else None,
                    'memory_rss_mb': process['memory_rss_mb'] if process else None,
                    'cpu_percent': process['cpu_percent'] if process else None
                } if process else None
                result[port['port']]['issues'] = issues if issues else ['No issues detected']
            
                if 'ports' not in results[container_name]:
                    results[container_name]['ports'] = [] 
                results[container_name]['ports'].append(result[port['port']])
        else:
            results[container_name]['ports'] = []
            issues = []
            container_severity = 'ok'
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

            severities.append(container_severity)
            results[container_name]['issues'] = issues if issues else ['No issues detected']

        if severities.count('critical')>0:
            overall_severity = 'critical'
        elif severities.count('warning')>0:
            overall_severity = 'warning'

        results[container_name]['container_info'] = {
            'id': container['id'] if container else None,
            'name': container['name'] if container else None,
            'status': container['status'] if container else None,
            'health': container['health'] if container else None,
            'restart_count': container['restart_count'] if container else None,
            'exit_code': container['exit_code'] if container else None,
            'memory_limit_mb': container['memory_limit_mb'] if container else None
        }
        results[container_name]['severity'] = overall_severity

    return results

def diagnose_environment(variables: List[Dict]) -> Dict[str, Any]:
    '''
    Diagnoses environment variable presence and correlates with service state.
    Does not diagnose causes or interpret variable values.
    '''
    results = {}

    clctd_ports = collect_ports()
    clctd_containers = collect_containers()

    active_ports = {p['port'] for p in clctd_ports['ports'] if p['status'] in ACTIVE_PORT_STATUSES}
    named_containers = {key['name']: key for key in clctd_containers['containers'] if key['status'] in ACTIVE_CONTAINER_STATUSES}


    for var in variables:
        name = var['name']
        port = var.get('port')        # optional
        container = var.get('container')  # optional
        var_redacted = var.get('redacted', True)  # safe by default
        issues = []
        severity = 'ok'

        env_result = collect_env([name],var_redacted)
        var_info = env_result['env_data'][0]
        present = var_info['present']
        empty = var_info['empty']

        port_active = None
        if port:
            port_active = True if port in active_ports else False

        container_status = None
        if container:
            container_status = container in named_containers

        severity = 'ok'
        running = None
        if port_active is not None and container_status is not None:
            running = port_active & container_status
        elif port_active is not None:
            running = port_active
        elif container_status is not None:
            running = container_status
        
        if running is None:
            if not present:
                issues.append(f'{name} is not set')
                severity = 'warning'
            elif empty:
                pass
        elif present and running:
            severity = 'ok'
        elif present and not running:
            issues.append(f'{name} is set but the service is not running')
            severity = 'critical'
        elif not present and running:
            issues.append(f'{name} is missing but the service is running')
            severity = 'warning'
        else:
            issues.append(f'{name} is missing and the service is not running')
            severity = 'critical'

        if empty:
            severity = 'critical'
            issues.append(f'{name} is set but empty')
        
        results[name] = {
            'severity': severity,
            'present': present,
            'empty': empty,
            'value_length': var_info['value_length'],
            'service': {
                'port': port,
                'port_active': port_active,
                'container': container,
                'container_status': container_status
            } if port or container else None,
            'issues': issues if issues else ['No issues detected']
        }
        
    return results

if __name__ == '__main__':
    import json
    PORTS_TO_DIAGNOSE = [80, 7260]
    diagnosis_result = diagnose_ports(PORTS_TO_DIAGNOSE)
    print(json.dumps(diagnosis_result, indent=2))

    CONTAINERS_TO_DIAGNOSE = ['buildx_buildkit_mybuilder0']
    diagnosis_result = diagnose_containers(CONTAINERS_TO_DIAGNOSE)
    print(json.dumps(diagnosis_result, indent=2))

    ENV_VARS_TO_DIAGNOSE = [
    {'name': 'PATH'},
    {'name': 'SOME_MISSING_VAR'},
    ]
    diagnosis_result = diagnose_environment(ENV_VARS_TO_DIAGNOSE)
    print(json.dumps(diagnosis_result, indent=2))