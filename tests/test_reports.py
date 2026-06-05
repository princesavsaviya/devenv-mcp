from unittest.mock import patch
from devenv_mcp.diagnostics.report import diagnose_ports,diagnose_containers,diagnose_environment

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

FAKE_CONTAINER_WITH_PORTS = {
    **FAKE_CONTAINER,
    'ports': {'5432/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '5432'}]}
}

FAKE_CONTAINER_NO_PORTS = {
    **FAKE_CONTAINER,
    'ports': {}
}

FAKE_ENV_VAR_PRESENT = {
    'name': 'DATABASE_URL',
    'present': True,
    'empty': False,
    'value': '***',
    'value_length': 20
}

FAKE_ENV_VAR_MISSING = {
    'name': 'DATABASE_URL',
    'present': False,
    'empty': False,
    'value': None,
    'value_length': None
}

FAKE_ENV_VAR_EMPTY = {
    'name': 'DATABASE_URL',
    'present': True,
    'empty': True,
    'value': '***',
    'value_length': 0
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

def test_zombie_process_unhealthy_container_ports():
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

        assert 'Port is open but associated process is not running' not in result[5432]['issues']

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

def test_container_not_found():
    with patch('devenv_mcp.diagnostics.report.collect_ports') as mock_ports, \
         patch('devenv_mcp.diagnostics.report.collect_processes') as mock_processes, \
         patch('devenv_mcp.diagnostics.report.collect_containers') as mock_containers:

        mock_ports.return_value = {'ports': [FAKE_PORT], 'errors': []}
        mock_processes.return_value = {'processes': [FAKE_PROCESS], 'access_denied': []}
        mock_containers.return_value = {'containers': []}

        result = diagnose_containers(['db'])

        assert result['db']['status'] == 'not found'

def test_healthy_container_with_ports():
    with patch('devenv_mcp.diagnostics.report.collect_ports') as mock_ports, \
         patch('devenv_mcp.diagnostics.report.collect_processes') as mock_processes, \
         patch('devenv_mcp.diagnostics.report.collect_containers') as mock_containers:

        mock_ports.return_value = {'ports': [FAKE_PORT], 'errors': []}
        mock_processes.return_value = {'processes': [FAKE_PROCESS], 'access_denied': []}
        mock_containers.return_value = {'containers': [FAKE_CONTAINER_WITH_PORTS]}

        result = diagnose_containers(['db'])

        assert result['db']['severity'] == 'ok'
        assert len(result['db']['ports']) == 1

def test_unhealthy_container_no_ports():
    with patch('devenv_mcp.diagnostics.report.collect_ports') as mock_ports, \
         patch('devenv_mcp.diagnostics.report.collect_processes') as mock_processes, \
         patch('devenv_mcp.diagnostics.report.collect_containers') as mock_containers:

        mock_ports.return_value = {'ports': [FAKE_PORT], 'errors': []}
        mock_processes.return_value = {'processes': [FAKE_PROCESS], 'access_denied': []}
        mock_containers.return_value = {'containers': [{**FAKE_CONTAINER_NO_PORTS,'health': 'unhealthy'}]}

        result = diagnose_containers(['db'])

        assert result['db']['severity'] == 'warning'
        assert result['db']['ports'] == []

def test_exited_container():
    with patch('devenv_mcp.diagnostics.report.collect_ports') as mock_ports, \
         patch('devenv_mcp.diagnostics.report.collect_processes') as mock_processes, \
         patch('devenv_mcp.diagnostics.report.collect_containers') as mock_containers:

        mock_ports.return_value = {'ports': [FAKE_PORT], 'errors': []}
        mock_processes.return_value = {'processes': [FAKE_PROCESS], 'access_denied': []}
        mock_containers.return_value = {'containers': [{**FAKE_CONTAINER,'status': 'exited'}]}

        result = diagnose_containers(['db'])

        assert result['db']['severity'] == 'critical'

def test_zombie_process_unhealthy_container():
    with patch('devenv_mcp.diagnostics.report.collect_ports') as mock_ports, \
         patch('devenv_mcp.diagnostics.report.collect_processes') as mock_processes, \
         patch('devenv_mcp.diagnostics.report.collect_containers') as mock_containers:

        unhealthy_container = {**FAKE_CONTAINER,'health':'unhealthy'}
        zombie_process = {**FAKE_PROCESS, 'status': 'zombie'}

        mock_ports.return_value = {'ports': [FAKE_PORT], 'errors': []}
        mock_processes.return_value = {'processes': [zombie_process], 'access_denied': []}
        mock_containers.return_value = {'containers': [unhealthy_container]}

        result = diagnose_containers(['db'])

        assert result['db']['severity'] == 'critical'

def test_env_present_no_service():
    with patch('devenv_mcp.diagnostics.report.collect_env') as mock_env, \
         patch('devenv_mcp.diagnostics.report.collect_ports') as mock_ports, \
         patch('devenv_mcp.diagnostics.report.collect_containers') as mock_containers:
        mock_ports.return_value = {'ports': [], 'errors': []}
        mock_containers.return_value = {'containers': []}
        mock_env.return_value = {'env_data': [FAKE_ENV_VAR_PRESENT], 'errors': []}

        result = diagnose_environment([{'name': 'DATABASE_URL'}])

        assert result['DATABASE_URL']['severity'] == 'ok'
        assert result['DATABASE_URL']['issues'] == ['No issues detected']


def test_env_missing_no_service():
    with patch('devenv_mcp.diagnostics.report.collect_env') as mock_env, \
         patch('devenv_mcp.diagnostics.report.collect_ports') as mock_ports, \
         patch('devenv_mcp.diagnostics.report.collect_containers') as mock_containers:
        mock_ports.return_value = {'ports': [], 'errors': []}
        mock_containers.return_value = {'containers': []}
        mock_env.return_value = {'env_data': [FAKE_ENV_VAR_MISSING], 'errors': []}

        result = diagnose_environment([{'name': 'DATABASE_URL'}])

        assert result['DATABASE_URL']['severity'] == 'warning'
        assert result['DATABASE_URL']['issues'] == ['DATABASE_URL is not set']

def test_env_empty_var():
    with patch('devenv_mcp.diagnostics.report.collect_env') as mock_env, \
         patch('devenv_mcp.diagnostics.report.collect_ports') as mock_ports, \
         patch('devenv_mcp.diagnostics.report.collect_containers') as mock_containers:
        mock_ports.return_value = {'ports': [], 'errors': []}
        mock_containers.return_value = {'containers': []}
        mock_env.return_value = {'env_data': [FAKE_ENV_VAR_EMPTY], 'errors': []}

        result = diagnose_environment([{'name': 'DATABASE_URL'}])

        assert result['DATABASE_URL']['severity'] == 'critical'
        assert result['DATABASE_URL']['issues'] == ['DATABASE_URL is set but empty']

def test_env_missing_service_running():
    with patch('devenv_mcp.diagnostics.report.collect_env') as mock_env, \
        patch('devenv_mcp.diagnostics.report.collect_ports') as mock_ports,\
        patch('devenv_mcp.diagnostics.report.collect_containers') as mock_containers:
        mock_ports.return_value = {'ports': [{**FAKE_PORT,'status':'LISTEN'}], 'errors': []}
        mock_env.return_value = {'env_data': [FAKE_ENV_VAR_MISSING], 'errors': []}
        mock_containers.return_value = {'containers' : []}

        result = diagnose_environment([{'name': 'DATABASE_URL','port': 5432}])

        assert result['DATABASE_URL']['severity'] == 'warning'

def test_env_present_service_not_running():
     with patch('devenv_mcp.diagnostics.report.collect_env') as mock_env, \
        patch('devenv_mcp.diagnostics.report.collect_ports') as mock_ports, \
        patch('devenv_mcp.diagnostics.report.collect_containers') as mock_containers:
        mock_ports.return_value = {'ports': [], 'errors': []}
        mock_containers.return_value = {'containers' : []}
        mock_env.return_value = {'env_data': [FAKE_ENV_VAR_PRESENT], 'errors': []}

        result = diagnose_environment([{'name': 'DATABASE_URL','port': 5432}])

        assert result['DATABASE_URL']['severity'] == 'critical'

def test_env_missing_service_not_running():
    with patch('devenv_mcp.diagnostics.report.collect_env') as mock_env,\
        patch('devenv_mcp.diagnostics.report.collect_ports') as mock_ports, \
        patch('devenv_mcp.diagnostics.report.collect_containers') as mock_containers:
        mock_env.return_value = {'env_data': [FAKE_ENV_VAR_MISSING], 'errors': []}
        mock_containers.return_value = {'containers' : []}
        mock_ports.return_value = {'ports': [], 'errors': []}

        result = diagnose_environment([{'name': 'DATABASE_URL','port': 5432}])

        assert result['DATABASE_URL']['severity'] == 'critical'