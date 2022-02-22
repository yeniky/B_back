from flask import Flask, request
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*')


@app.route('/data_message', methods=['POST'])
def received_data_message():
    try:
        data = request.get_json()
    except TypeError:
        data = {'data': []}
    socketio.emit('data_message', data)
    return "ok"


@app.route('/data_alert', methods=['POST'])
def received_data_alert():
    try:
        data = request.get_json()
    except TypeError:
        data = {'data': []}
    socketio.emit('data_alert', data)
    return "ok"

@app.route('/closed_alert', methods=['POST'])
def closed_alert():
    try:
        data = request.get_json()
    except TypeError:
        data = {'data': []}
    socketio.emit('closed_alert', data)
    return "ok"

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)
