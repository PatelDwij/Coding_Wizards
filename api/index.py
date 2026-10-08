import os
import sys
import json
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app import app

class VercelWSGIMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        # Quick debug inspect
        if 'dump-headers' in str(environ.get('QUERY_STRING', '')) or 'dump-headers' in str(environ.get('HTTP_X_FORWARDED_URI', '')):
            headers_dump = {k: str(v) for k, v in environ.items() if isinstance(v, (str, int, float, bool))}
            body = json.dumps(headers_dump, indent=2).encode('utf-8')
            start_response('200 OK', [('Content-Type', 'application/json'), ('Content-Length', str(len(body)))])
            return [body]

        # Vercel sets the original path in one of these headers:
        # Check x-forwarded-url, x-original-uri, x-matched-path, x-vercel-forwarded-for, etc.
        orig_path = (
            environ.get('HTTP_X_FORWARDED_URL') or
            environ.get('HTTP_X_ORIGINAL_URI') or
            environ.get('HTTP_X_FORWARDED_URI') or
            environ.get('HTTP_X_NOW_ROUTE_MATCHES')
        )
        if orig_path:
            environ['PATH_INFO'] = orig_path.split('?')[0]
        else:
            path_info = environ.get('PATH_INFO', '')
            for prefix in ['/api/index.py', '/api/index']:
                if path_info.startswith(prefix):
                    remainder = path_info[len(prefix):]
                    environ['PATH_INFO'] = remainder if remainder.startswith('/') else ('/' + remainder)
                    break
                    
        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelWSGIMiddleware(app.wsgi_app)
app.debug = False
handler = app
