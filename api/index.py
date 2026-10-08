import sys
import json
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app import app

def application(environ, start_response):
    if 'debug' in environ.get('PATH_INFO', '') or 'debug' in environ.get('RAW_URI', '') or 'debug' in str(environ.get('QUERY_STRING', '')):
        data = {k: str(v) for k, v in environ.items() if isinstance(v, (str, int, float, bool))}
        res = json.dumps(data, indent=2).encode('utf-8')
        start_response('200 OK', [('Content-Type', 'application/json')])
        return [res]
    return app(environ, start_response)

handler = application
