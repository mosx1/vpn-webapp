from db.repository.devices import Devices

from flask import redirect, request


def auto_select_platform_by_download_app():
    request.headers.get('User-Agent')
    device_client: str = (request.headers.get('User-Agent').split("(")[1]).split(";")[0]
    if request.args.get('aw'):
        match device_client:
            case Devices.iphone.value:
                return redirect('https://apps.apple.com/ru/app/amneziawg/id6478942365')
            case Devices.macintosh.value:
                return redirect('https://github.com/amnezia-vpn/amnezia-client/releases/download/4.8.14.5/AmneziaVPN_4.8.14.5_macos.pkg')
            case Devices.windows.value:
                return redirect('https://github.com/amnezia-vpn/amnezia-client/releases/download/4.8.14.5/AmneziaVPN_4.8.14.5_x64.exe')
            case Devices.android.value:
                return redirect('https://play.google.com/store/apps/details?id=org.amnezia.vpn&utm_source=amnezia.org&utm_campaign=organic&utm_medium=referral')
            case _:
                return 'Воспользуйтесь ручной наастройкой'
            
    match device_client:
        case Devices.iphone.value | Devices.macintosh.value:
            return redirect('https://apps.apple.com/ru/app/incy/id6756943388')
        case Devices.android.value:
            return redirect('https://play.google.com/store/apps/details?id=llc.itdev.incy')
        case Devices.windows.value:
            return redirect('https://github.com/INCY-DEV/incy-platforms/releases/latest/download/incy-windows-setup.exe')
        case _:
            return 'Воспользуйтесь ручной наастройкой'