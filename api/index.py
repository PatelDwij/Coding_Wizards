import os
import sys
from pathlib import Path

# Add project root to sys.path so app, database, ai_services, etc. are importable
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app import app

class VercelWSGIMiddleware:
    """
    Middleware to resolve URL path rewrites on Vercel Serverless.
    Restores the real user requested path from HTTP_X_INVOKE_PATH
    or strips internal /api/index.py rewrite prefix.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        # x-invoke-path is set by Vercel to the original user requested URL path
        invoke_path = environ.get('HTTP_X_INVOKE_PATH') or environ.get('HTTP_X_FORWARDED_URI')
        if invoke_path:
            environ['PATH_INFO'] = invoke_path.split('?')[0]
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
