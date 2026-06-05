from unittest.mock import patch
from devenv_mcp.diagnostics.report import diagnose_ports

FAKE_PROCESS = {
    'pid': 1234,
    'name': 'postgres',
    'status': 'running',        # change this per test
    'memory_rss_mb': 50.0,
    'cpu_percent': 0.0,
    'net_connections': [],
    'create_time': 0.0
}

FAKE_PORT = {
    'port': 5432,
    'ip': '0.0.0.0',
    'protocol': 'TCP',
    'status': 'LISTEN',         # change this per test
    'pid': 1234,
    'fd': 10,
    'family': 'IPv4',
    'raddr': None,
    'name': 'postgres'
}

FAKE_CONTAINER = {
    'id': 'abc123',
    'name': 'db',
    'status': 'running',        # change this per test
    'health': 'healthy',        # change this per test
    'restart_count': 0,
    'exit_code': 0,
    'memory_limit_mb': 512.0,
    'created': '2024-01-01',
    'ports': {'5432/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '5432'}]},
    'pid': 1234
}

def test_port_not_found():
    with patch('devenv_mcp.diagnostics.report.collect_ports') as mock_ports, \
         patch('devenv_mcp.diagnostics.report.collect_processes') as mock_processes, \
         patch('devenv_mcp.diagnostics.report.collect_containers') as mock_containers:

        mock_ports.return_value = {'ports': [], 'errors': []}
        mock_processes.return_value = {'processes': [], 'access_denied': []}
        mock_containers.return_value = {'containers': []}

        result = diagnose_ports([5432])

        assert result[5432]['status'] == 'not found'

def test_healthy_native_process():
    with patch('devenv_mcp.diagnostics.report.collect_ports') as mock_ports, \
         patch('devenv_mcp.diagnostics.report.collect_processes') as mock_processes, \
         patch('devenv_mcp.diagnostics.report.collect_containers') as mock_containers:

        mock_ports.return_value = {'ports': [FAKE_PORT], 'errors': []}
        mock_processes.return_value = {'processes': [FAKE_PROCESS], 'access_denied': []}
        mock_containers.return_value = {'containers': []}

        result = diagnose_ports([5432])

        assert result[5432]['severity'] == 'ok'
        assert result[5432]['container'] == None

def test_zombie_process():
    with patch('devenv_mcp.diagnostics.report.collect_ports') as mock_ports, \
         patch('devenv_mcp.diagnostics.report.collect_processes') as mock_processes, \
         patch('devenv_mcp.diagnostics.report.collect_containers') as mock_containers:

        zombie_process = {**FAKE_PROCESS, 'status': 'zombie'}
        mock_ports.return_value = {'ports': [FAKE_PORT], 'errors': []}
        mock_processes.return_value = {'processes': [zombie_process], 'access_denied': []}
        mock_containers.return_value = {'containers': []}

        result = diagnose_ports([5432])

        assert result[5432]['severity'] == 'warning'

def test_unhealthy_container():
    with patch('devenv_mcp.diagnostics.report.collect_ports') as mock_ports, \
         patch('devenv_mcp.diagnostics.report.collect_processes') as mock_processes, \
         patch('devenv_mcp.diagnostics.report.collect_containers') as mock_containers:

        unhealthy_container = {**FAKE_CONTAINER,'health':'unhealthy'}
        mock_ports.return_value = {'ports': [FAKE_PORT], 'errors': []}
        mock_processes.return_value = {'processes': [FAKE_PROCESS], 'access_denied': []}
        mock_containers.return_value = {'containers': [unhealthy_container]}

        result = diagnose_ports([5432])

        assert result[5432]['severity'] == 'warning'

def test_Zombie_process_unhealthy_container():
    with patch('devenv_mcp.diagnostics.report.collect_ports') as mock_ports, \
         patch('devenv_mcp.diagnostics.report.collect_processes') as mock_processes, \
         patch('devenv_mcp.diagnostics.report.collect_containers') as mock_containers:

        unhealthy_container = {**FAKE_CONTAINER,'health':'unhealthy'}
        zombie_process = {**FAKE_PROCESS, 'status': 'zombie'}

        mock_ports.return_value = {'ports': [FAKE_PORT], 'errors': []}
        mock_processes.return_value = {'processes': [zombie_process], 'access_denied': []}
        mock_containers.return_value = {'containers': [unhealthy_container]}

        result = diagnose_ports([5432])

        assert result[5432]['severity'] == 'critical'

def test_exited_container_holding_port():
    with patch('devenv_mcp.diagnostics.report.collect_ports') as mock_ports, \
         patch('devenv_mcp.diagnostics.report.collect_processes') as mock_processes, \
         patch('devenv_mcp.diagnostics.report.collect_containers') as mock_containers:

        unhealthy_container = {**FAKE_CONTAINER,'status':'exited'}
        mock_ports.return_value = {'ports': [FAKE_PORT], 'errors': []}
        mock_processes.return_value = {'processes': [FAKE_PROCESS], 'access_denied': []}
        mock_containers.return_value = {'containers': [unhealthy_container]}

        result = diagnose_ports([5432])

        assert result[5432]['severity'] == 'critical'


def test_pid_none():
    with patch('devenv_mcp.diagnostics.report.collect_ports') as mock_ports, \
         patch('devenv_mcp.diagnostics.report.collect_processes') as mock_processes, \
         patch('devenv_mcp.diagnostics.report.collect_containers') as mock_containers:

        pid_none = {**FAKE_PORT,'pid':None}
        mock_ports.return_value = {'ports': [pid_none], 'errors': []}
        mock_processes.return_value = {'processes': [], 'access_denied': []}
        mock_containers.return_value = {'containers': [FAKE_CONTAINER]}

        result = diagnose_ports([5432])

        assert 'Port is Open but associated process is not running' not in result[5432]['issues']

def test_restart_crash_exit_code():
    with patch('devenv_mcp.diagnostics.report.collect_ports') as mock_ports, \
         patch('devenv_mcp.diagnostics.report.collect_processes') as mock_processes, \
         patch('devenv_mcp.diagnostics.report.collect_containers') as mock_containers:

        unhealthy_container = {**FAKE_CONTAINER,'restart_count':3,'exit_code':1}
        mock_ports.return_value = {'ports': [FAKE_PORT], 'errors': []}
        mock_processes.return_value = {'processes': [FAKE_PROCESS], 'access_denied': []}
        mock_containers.return_value = {'containers': [unhealthy_container]}

        result = diagnose_ports([5432])

        assert result[5432]['severity'] == 'warning'