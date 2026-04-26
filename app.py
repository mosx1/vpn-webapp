import http, methods.common, uvicorn, threads

from routers.vpn_app import vpn_app_bp
from routers.subscription import sub
from routers.auth import auth
from routers.admin_panel import admin_panel_bp

from flask import Flask
from flask import send_from_directory, redirect


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = ''
app.config['JSON_AS_ASCII'] = False
app.register_blueprint(vpn_app_bp)
app.register_blueprint(sub)
app.register_blueprint(auth)
app.register_blueprint(admin_panel_bp)

@app.route('/')
def index():
    return redirect('/auth/')


@app.route('/download_app')
def _():
    return methods.common.auto_select_platform_by_download_app()


@app.route('/.well-known/pki-validation/<path:filename>', methods=['GET', 'POST'])
def download(filename):
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