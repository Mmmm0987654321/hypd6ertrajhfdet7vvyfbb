#!/usr/bin/env python3
"""Personal-use, least-privilege Andee variant. Preserves Andee name and credits."""
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

base = Path(sys.argv[1]).resolve()
manifest_path = base / 'app/src/main/AndroidManifest.xml'
license_path = base / 'LICENSE'
if not license_path.exists():
    raise SystemExit('Andee LICENSE is missing')
tree = ET.parse(manifest_path)
root = tree.getroot()
A = '{http://schemas.android.com/apk/res/android}'
removed = {
    'android.permission.READ_SMS',
    'android.permission.SEND_SMS',
    'android.permission.RECEIVE_SMS',
    'android.permission.READ_CALL_LOG',
    'android.permission.CALL_PHONE',
    'android.permission.READ_CONTACTS',
    'android.permission.READ_CALENDAR',
    'android.permission.WRITE_CALENDAR',
    'android.permission.ACCESS_COARSE_LOCATION',
    'android.permission.ACCESS_FINE_LOCATION',
    'android.permission.ACTIVITY_RECOGNITION',
    'android.permission.CAMERA',
    'android.permission.WRITE_SECURE_SETTINGS',
    'android.permission.QUERY_ALL_PACKAGES',
    'android.permission.PACKAGE_USAGE_STATS',
    'android.permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS',
}
for element in list(root):
    if element.tag == 'uses-permission' and element.get(A + 'name') in removed:
        root.remove(element)
application = root.find('application')
if application is None:
    raise SystemExit('Andee manifest lacks application')
# These services trigger Google's automatic Internet-sideloading block on
# supported markets.  This edition intentionally loses Accessibility-based
# cross-app control and notification reading: no spoofed/hidden permission.
for service in list(application):
    if service.tag != 'service':
        continue
    name = service.get(A + 'name', '')
    if name == '.device.NotificationRelayService':
        application.remove(service)
ET.indent(tree, space='    ')
tree.write(manifest_path, encoding='utf-8', xml_declaration=True)
check = ET.parse(manifest_path).getroot()
permissions = [e.get(A + 'name') for e in check.findall('uses-permission')]
services = [e.get(A + 'name') for e in check.findall('application/service')]
assert not (set(permissions) & removed), 'sensitive permission remained'
assert '.ScreenBodyService' in services
assert '.device.NotificationRelayService' not in services
assert not any('ACCESSIBILITY' in str(p) or 'SMS' in str(p) for p in permissions)
assets = base / 'app/src/main/assets'
assets.mkdir(parents=True, exist_ok=True)
(assets / 'ANDEE_LICENSE.txt').write_bytes(license_path.read_bytes())
(assets / 'MODIFIED_BUILD_NOTICE.txt').write_text(
    'Andee v0.11.0 — modified private-use build.\n'
    'Source: https://github.com/kuafuai/andee (KUAFUAI 2026)\n'
    'Changes: retained user-approved Accessibility; removed NotificationListener service '
    'registration, SMS, contacts, call logs, location, calendar and other '
    'optional sensitive permissions. Non-financial app screen control is opt-in; notifications '
    'monitoring are unavailable by design. No Play Protect bypass. '
    'No AI/voice API keys are bundled.\n'
    'Not an official KUAFUAI release.\n', encoding='utf-8'
)
print('BANK-EXCLUDING BUILD: removed', len(removed), 'permission types and 2 sensitive services')
print('Remaining app-declared permissions:', permissions)
