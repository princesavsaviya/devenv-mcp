from typing import Dict,Any
try:
    import docker
except ImportError:
    docker = None

def collect_containers() -> Dict[str,Any]:
    '''
        Collects Docker container state and resource configuration.
        Does not diagnose, assess, or rank container behavior.
    '''

    if not docker:
        return {'containers': [], 'error': 'Docker SDK not installed'}
    
    try:
        client = docker.from_env()
        containers = client.containers.list(all=True)
        container_info = []
        for container in containers:
            try:
                info = {
                    'id': container.id[:12],
                    'name': container.name,
                    'status': container.status,
                    'health': container.attrs['State'].get('Health', {}).get('Status', None),
                    'restart_count': container.attrs['RestartCount'],
                    'exit_code': container.attrs['State'].get('ExitCode', 0),
                    'memory_limit_mb': round(container.attrs['HostConfig']['Memory'] / (1024 * 1024), 2) if container.attrs['HostConfig']['Memory'] else None,
                    'created': container.attrs['Created'],
                    'ports': container.attrs['NetworkSettings']['Ports']
                }
                container_info.append(info)
            except docker.errors.NotFound:
                continue
    
    except docker.errors.DockerException as e:
        return {'containers': [], 'error': str(e)}
    
    return {'containers': container_info}
    
    


if __name__ == '__main__':
    import json
    data = collect_containers()
    print(json.dumps(data, indent=2))