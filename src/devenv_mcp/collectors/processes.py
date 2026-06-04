from typing import List, Dict, Any
try:
    import psutil
except ImportError:
    psutil = None

def collect_processes() -> Dict[str, Any]:
    ''' Collects information about running processes on the system.
        Does not diagnose, assess, or rank process behavior.
    '''

    if not psutil:
        return {'processes': [], 'access_denied': [{'error': 'psutil library is not installed'}]}

    processes = []
    access_denied = []
    attrs = ('pid', 'name', 'status', 'memory_info', 'cpu_percent', 'net_connections','create_time')
    for proc in psutil.process_iter(attrs=attrs):
        try:
            proc_info = {
                'pid': proc.info['pid'],
                'name': proc.info['name'],
                'status': proc.info['status'],
                'memory_rss_mb': round(proc.info['memory_info'].rss / (1024 * 1024), 2) if proc.info['memory_info'] else None,  # Convert bytes to MB
                'cpu_percent': proc.info['cpu_percent'],
                'net_connections': [conn._asdict() for conn in proc.info['net_connections']] if proc.info['net_connections'] else [],
                'create_time': proc.info['create_time']
            }

            processes.append(proc_info)
        except (psutil.AccessDenied):
            access_denied.append({'pid': proc.info['pid'], 'name': proc.info['name'], 'status': 'Access Denied'})
        except (psutil.NoSuchProcess):
            continue
    
    return {'processes': processes, 'access_denied': access_denied}


if __name__ == '__main__':
    collect_processes()