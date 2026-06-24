import http, methods.common, uvicorn, threads

from routers.vpn_app import vpn_app_bp
from routers.subscription import sub
from routers.auth import auth
from routers.admin_panel import admin_panel_bp
from routers.payment import payment_bp

from urllib.parse import urlencode

from flask import Flask
from flask import send_from_directory, redirect, request
try:
    from flasgger import Swagger  # type: ignore[reportMissingImports]
except ModuleNotFoundError:
    Swagger = None


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = ''
app.config['JSON_AS_ASCII'] = False
app.config['SWAGGER'] = {
    'title': 'VPN WebApp API',
    'uiversion': 3
}
swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "VPN WebApp API",
        "version": "1.0.0",
        "description": "API documentation for vpn-webapp"
    }
}
if Swagger is not None:
    Swagger(app, template=swagger_template)
app.register_blueprint(vpn_app_bp)
app.register_blueprint(sub)
app.register_blueprint(auth)
app.register_blueprint(admin_panel_bp)
app.register_blueprint(payment_bp)

@app.route('/')
def index():
    """
    Redirect to auth page preserving query params.
    ---
    tags:
      - Common
    parameters:
      - in: query
        name: any
        required: false
        type: string
        description: Any query parameters are forwarded to /auth/.
    responses:
      302:
        description: Redirect to /auth/
    """
    query_params = request.args.to_dict(flat=False)
    query_string = urlencode(query_params, doseq=True)
    auth_url = '/auth/'
    if query_string:
        auth_url = f'{auth_url}?{query_string}'
    return redirect(auth_url)


@app.route('/download_app')
def _():
    """
    Auto-select and return app download target.
    ---
    tags:
      - Common
    responses:
      200:
        description: Platform-specific download response.
    """
    return methods.common.auto_select_platform_by_download_app()


@app.route('/.well-known/pki-validation/<path:filename>', methods=['GET', 'POST'])
def download(filename):
    """
    Return ACME/PKI validation file.
    ---
    tags:
      - Common
    parameters:
      - in: path
        name: filename
        required: true
        type: string
        description: Validation file name inside .well-known path.
    responses:
      200:
        description: Validation file content.
      404:
        description: File not found.
    """
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


if __name__ == '__main__':
    conn = http.client.HTTPConnection("ifconfig.me")
    conn.request("GET", "/ip")
    url = conn.getresponse().read().decode("utf-8")
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        interface="wsgi",
    )