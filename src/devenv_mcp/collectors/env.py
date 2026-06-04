from typing import List,Dict,Any
import os

def collect_env(variables: List[str],redacted: bool = True) -> Dict[str, Any]:
    '''
    Collects specified environment variables from the system.
    Does not diagnose, assess, or rank variable behavior.
    '''
    env_data = []
    try:    
        for var in variables:
            value = os.getenv(var)
            env_data.append({
                'name': var,
                'present': value is not None,
                'empty': value == '' if value is not None else False,
                'value': '***' if redacted and value is not None else value if value is not None else None,
                'value_length': len(value) if value is not None else None
            })
    except Exception as e:
        return {'env_data': env_data, 'errors': [{'error': str(e)}]}

    return {'env_data': env_data, 'errors': []}

if __name__ == '__main__':
    import json
    variables_to_collect = [
        'PATH',
        'HOME',
        'USER',
        'SHELL',
        'LANG',
        'PYTHONPATH'
    ]
    result = collect_env(variables_to_collect)
    print(json.dumps(result, indent=2))

