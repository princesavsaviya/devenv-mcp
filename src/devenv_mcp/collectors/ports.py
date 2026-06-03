from typing import Dict,Any
import socket
try:
    import psutil
except ImportError:
    psutil = None


def collect_ports() -> Dict[str,Any]:
    """ Collects information about open ports on the system.
        Does not diagnose, assess, or rank port behavior.
        fd: file descriptor, may not be available on all platforms or for all connections.
    """

    if not psutil:
        return {"ports": [], "errors": [{'error': 'psutil library is not installed'}]}

    ports = []
    errors = []
    try:
        for conn in psutil.net_connections(kind='inet'):
            try:
                try:
                    process_name = psutil.Process(conn.pid).name() if conn.pid else None
                except (psutil.NoSuchProcess):
                    process_name = None
                port_info = {
                    "port": conn.laddr.port if conn.laddr else None,
                    "ip": conn.laddr.ip if conn.laddr else None,
                    "protocol": "TCP" if conn.type == socket.SOCK_STREAM else "UDP" if conn.type == socket.SOCK_DGRAM else "Other",
                    "status": conn.status,
                    "pid": conn.pid,
                    "fd": conn.fd,
                    "family": "IPv4" if conn.family == socket.AF_INET else "IPv6" if conn.family == socket.AF_INET6 else "Other",
                    "raddr": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                    "name": process_name
                }
                ports.append(port_info)
            except (psutil.AccessDenied):
                errors.append({
                    "port": conn.laddr.port if conn.laddr else None,
                    "ip": conn.laddr.ip if conn.laddr else None,
                    "protocol": "TCP" if conn.type == socket.SOCK_STREAM else "UDP" if conn.type == socket.SOCK_DGRAM else "Other",
                    "status": conn.status,
                    "pid": conn.pid,
                    "raddr": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                    "name": 'Access Denied'
                })
            except (psutil.NoSuchProcess):
                continue
    except Exception as e:
        errors.append({"error": str(e)})
    return {"ports": ports, "errors": errors}

if __name__ == "__main__":
    collect_ports()