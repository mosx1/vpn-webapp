import http, methods.common, uvicorn

from routers.vpn_app import vpn_app_bp
from routers.subscription import sub

from flask import Flask
from flask import request, redirect, send_from_directory, render_template

from db.repository.devices import Devices


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = ''
app.config['JSON_AS_ASCII'] = False
app.register_blueprint(vpn_app_bp)
app.register_blueprint(sub)


@app.route('/')
def index():
    
    return render_template('index.html')

# @app.route('/mobile')
# def linkIphone():
#     request.headers.get('User-Agent')
#     device_client: str = (request.headers.get('User-Agent').split("(")[1]).split(";")[0]

#     match device_client:
#         case Devices.iphone.value | Devices.macintosh.value:
#             deeplink_start = 'v2box://install-config?url='
#         case Devices.android.value:
#             deeplink_start = 'happ://add/'
#         case _:
#             return 'Воспользуйтесь ручной наастройкой'
        
#     link: str = request.args.get('link')
#     security: str = request.args.get('security')
#     encryption: str = request.args.get('encryption')
#     pbk: str = request.args.get('pbk')
#     fp: str = request.args.get('fp')
#     type: str = request.args.get('type')
#     flow: str = request.args.get('flow')
#     sni: str = request.args.get('sni')
#     sid: str = request.args.get('sid')
#     name: str = request.args.get('name')

#     return redirect(
#         '{}{}&security={}&encryption={}&pbk={}&fp={}&type={}&flow={}&sni={}&sid={}#{}'.format(
#             deeplink_start,
#             link,
#             security,
#             encryption,
#             pbk,
#             fp,
#             type,
#             flow,
#             sni,
#             sid,
#             name
#         )
#     )


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
    # app.run(
    #     host='0.0.0.0',
    #     port=8000,
    #     debug=True
    # )


