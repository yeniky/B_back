from flask import jsonify, request
from app import db
from app.api import bp
from app.models import Position, Container, Tag, ZoneAlertRule, ZoneAlert, Zone, Connector
from app.models import Batch, BatchAlertRule, BatchAlert
from datetime import datetime
from app.api.errors import bad_request
import requests
import json
import threading
from flask import current_app
from math import sqrt
from app.utils.alert import check_alerts, save_and_emit
from app.utils.cleanup_alert import update_cleanup_rule, check_cleanup_alert


@bp.route('/zones')
def get_zones():
    zones = Zone.query.filter(Zone.name != 'Sin Zona').all()
    return jsonify([z.to_dict() for z in zones])

@bp.route('/create_connector', methods=['POST'])
def create_connector():
    data = request.get_data().decode('utf-8')
    if data is None:
        return bad_request('invalid post message')
    new_connector = Connector.create(data)
    return jsonify({"status": "OK"})


@bp.route('/positions', methods=['POST'])
def create_position():
    data = request.get_data().decode('utf-8').split('\n')
    if data is None:
        return bad_request('invalid post message')
    payload = []
    tags = []
    for pos in data:
        new_position = Position.create(pos)
        if type(new_position) == Tag:
            tags.append(new_position)
            payload.append(new_position.to_dict())
    db.session.commit()

    for tag in tags:
        update_cleanup_rule(tag)

    if len(payload) > 0:
        try:
            requests.post('http://127.0.0.1:5001/data_message',
                          json={'data': payload})
        except requests.exceptions.ConnectionError:
            pass
        # return jsonify({"status": "OK"})

    if len(tags) > 0:
        check_alerts(tags)
        return jsonify({"status": "OK"})

    return bad_request("no data parsed")
