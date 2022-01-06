# -*- coding: utf-8 -*-

import argparse
import datetime
import subprocess
import json

# token from https://oauth.yandex.ru/authorize?response_type=token&client_id=

def createBackup(filename):
    archive = '{}.{}.{}'.format(filename, datetime.datetime.now().strftime('%Y-%m-%d'), 'tar.zst')
    subprocess.call(['tar', '-I', 'zstd', '-cvf', archive, filename])
    return archive

def getUploadUrl(filename, token):
    url = f'https://cloud-api.yandex.net:443/v1/disk/resources/upload/?path=archive/{filename}&overwrite=true'
    oauth = f'Authorization: OAuth {token}'
    out = subprocess.check_output(['curl', '-s', '-H', oauth, url])
    return json.loads(out)['href']

def uploadBackup(uploadUrl, archive, token):
    oauth = f'Authorization: OAuth {token}'
    subprocess.call(['curl', '-s', '-T', archive, '-H', oauth, uploadUrl])

def encrypt(key, filename):
    subprocess.call(['gpg', '--encrypt', '-r', key, filename])
    return filename + '.gpg'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='python create_backup.py')
    parser.add_argument('-t', help='token, get it from https://oauth.yandex.ru')
    parser.add_argument('-f', help='file to backup')
    parser.add_argument('-r', help='gpg key')
    args = parser.parse_args()

    archive = createBackup(args.f)
    crypted = encrypt(args.r, archive)
    uploadUrl = getUploadUrl(crypted, args.t)
    uploadBackup(uploadUrl, crypted, args.t)
