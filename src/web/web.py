import os
from threading import Thread
from urllib.parse import quote

from flask import Flask, jsonify, send_file

from util import config

app = Flask(__name__)


def is_sanitized(filename: str) -> bool:
    return not any(x in filename for x in ['/', '\\', '..', '$', '%', '&'])


@app.route('/backgrounds/<filename>', methods=['GET'])
def background(filename: str):
    if not is_sanitized(filename):
        return jsonify(status=403, message='Invalid file name.')

    file = os.path.join('../', config.BACKGROUNDS_DIR + filename)

    return send_file(file)


@app.route('/banners/<filename>', methods=['GET'])
def banner(filename: str):
    if not is_sanitized(filename):
        return jsonify(status=403, message='Invalid file name.')

    file = os.path.join('../', config.BANNERS_DIR + filename)

    return send_file(file)


def get_url(filename: str, directory: str) -> str:
    return f'emojicaptcha.fumaz.dev/{directory}/{quote(filename)}'


def run():
    thread = Thread(target=lambda: app.run(host='0.0.0.0', debug=False))
    thread.start()
