# coding: utf-8
import os
import zipfile
from flask import Blueprint, request, current_app
from flask import abort, redirect, Response
from cStringIO import StringIO
from shutil import copyfileobj
from .models import AndroidVersion, Enable

bp = Blueprint('common', __name__)
ANDROID_URL = '/static/android/%(version)s/%(name)s_%(version)s_%(channel)d.apk'
ANDROID_PATH = 'android/%(version)s/%(name)s_%(version)s.apk'
apkinfo = {
    'version': '',
    'version_code': 0,
    'apk': None,
    'name': '',
}


def build_apk(apk, channel, uid):
    zipped = zipfile.ZipFile(apk, 'a', zipfile.ZIP_DEFLATED)
    channel_file = 'META-INF/CHANNEL_{channel}'.format(channel=channel)
    invite_file = 'META-INF/INVITE_{uid}'.format(uid=uid)
    zipped.writestr(channel_file, "")
    zipped.writestr(invite_file, "")
    zipped.close()


def get_apk(version, version_code, channel, uid):
    global apkinfo
    if version != apkinfo['version'] or not apkinfo['apk']:
        apkinfo['version'] = version
        apkinfo['version_code'] = version_code
        apkinfo['apk'] = StringIO()
        apkinfo['name'] = current_app.config.get('NAME')
        static_folder = current_app.config.get('WEB_STATIC_FOLDER')
        path = os.path.join(static_folder, ANDROID_PATH % apkinfo)
        with open(path) as fd:
            apkinfo['apk'].write(fd.read())
    apkinfo['apk'].seek(0)
    apk = StringIO()
    copyfileobj(apkinfo['apk'], apk)
    build_apk(apk, channel, uid)
    apk.seek(0)
    return apk


@bp.route('/android/latest.html')
def android_latest():
    channel = request.args.get('channel', 1001, int)
    item = AndroidVersion.objects(enable__in=Enable.get()).order_by('-id').first()
    if not item:
        abort(404)

    uid = request.args.get('uid')
    name = current_app.config.get('NAME')
    if not uid:
        url = ANDROID_URL % dict(
            name=name,
            version=item.version,
            channel=channel,
        )
        return redirect(url)
    res = get_apk(item.version, item.id, channel, uid)
    filename = '%s_%s_%d_%s.apk' % (name, item.version, channel, uid)
    return Response(res.read(), headers={
        'Content-Type': "application/octet-stream",
        'Content-Disposition': 'attachment;filename=%s' % filename,
    })
