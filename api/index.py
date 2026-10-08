import sys
import urllib.parse
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app import app

class VercelWSGIMiddleware:
    """
    Restores the real URL path from the __path query parameter
    injected by Vercel's rewrite rule.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        query = environ.get('QUERY_STRING', '')
        if '__path' in query:
            params = urllib.parse.parse_qs(query, keep_blank_values=True)
            if '__path' in params:
                raw_path = params['__path'][0] if params['__path'] else ''
                clean_path = '/' + raw_path.lstrip('/') if raw_path else '/'
                environ['PATH_INFO'] = clean_path
                params.pop('__path', None)
                environ['QUERY_STRING'] = urllib.parse.urlencode(params, doseq=True)
        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelWSGIMiddleware(app.wsgi_app)
handler = app
