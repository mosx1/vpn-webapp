from db.repository.devices import Devices

from flask import redirect, request


def auto_select_platform_by_download_app():
    request.headers.get('User-Agent')
    device_client: str = (request.headers.get('User-Agent').split("(")[1]).split(";")[0]
    if request.args.get('aw', type=bool):
        match device_client:
            case Devices.iphone.value | Devices.macintosh.value:
                return redirect('https://apps.apple.com/ru/app/amneziawg/id6478942365')
    match device_client:
        case Devices.iphone.value | Devices.macintosh.value:
            return redirect('https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973')
        case Devices.android.value:
            return redirect('https://play.google.com/store/apps/details?id=com.happproxy')
        case Devices.windows.value:
            return redirect('https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.exe')
        case _:
            return 'Воспользуйтесь ручной наастройкой'