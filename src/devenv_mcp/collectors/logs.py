from typing import Dict, Any, List
import os

def collect_logs(log_path: str, lines_to_read: int = 100) -> Dict[str, Any]:
    '''
    Collects and filters recent system logs for error keywords.
    Handles missing files, permission errors, and unreadable binary formats.
    Does not diagnose causes, rank severity, or interpret log content.
    '''
    result = {
        'log_path': log_path,
        'total_lines_read': 0,
        'errors_found': [],
        'error': None
    }
    
    error_keywords = ['ERROR', 'CRITICAL', 'FATAL', 'Exception', 'Traceback']

    try:
        if not os.path.exists(log_path):
            result['error'] = 'File not found'
            return result
            
        if os.path.isdir(log_path):
            result['error'] = 'The path points to a directory, not a file'
            return result

        if os.path.getsize(log_path) == 0:
            return result

        with open(log_path, 'rb') as log_file:
            log_file.seek(0, os.SEEK_END)
            pointer = log_file.tell()

            lines = []
            buffer = bytearray()

            if pointer > 0:
                log_file.seek(pointer - 1)
                if log_file.read(1) == b'\n':
                    pointer -= 1

            while pointer > 0 and len(lines) < lines_to_read:
                pointer -= 1
                log_file.seek(pointer)
                byte = log_file.read(1)
                
                if byte == b'\n':
                    lines.append(buffer[::-1].decode('utf-8', errors='replace'))
                    buffer = bytearray()
                else:
                    buffer.extend(byte)

            if buffer:
                lines.append(buffer[::-1].decode('utf-8', errors='replace'))
                
            ordered_lines = lines[::-1]
            result['total_lines_read'] = len(ordered_lines)

            null_byte_check = ''.join(ordered_lines[:5])
            if '\x00' in null_byte_check:
                result['total_lines_read'] = 0
                result['error'] = 'Unreadable binary file format detected'
                return result

            for line in ordered_lines:
                clean_line = line.strip()
                if any(kw in clean_line for kw in error_keywords):
                    result['errors_found'].append(clean_line)

    except FileNotFoundError:
        result['error'] = 'File not found'
    except PermissionError:
        result['error'] = 'Permission denied: Insufficient privileges to read this file'
    except Exception as e:
        result['error'] = f'Unexpected read failure: {str(e)}'

    return result

if __name__ == '__main__':
    import json
    
    log_data = collect_logs(
        log_path='src\\devenv_mcp\\collectors\\docker_collector.py', 
        lines_to_read=100
    )
    print(json.dumps(log_data, indent=2))
