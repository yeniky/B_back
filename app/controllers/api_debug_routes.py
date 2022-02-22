from flask import jsonify, request, Blueprint
from app import db
from app.models import TagType, Zone, User, InactivityAlertRule, DeviceType
import json
bp = Blueprint('api_debug_routes', __name__)

tags = [
    {
        "id": "005",
        "seed": "Seed type here",
        "type": "seed type here",
        "code": "codewillbe",
        "batch": "00AF",
        "description": "tag de pruebas",
        "state": "warning",
        "position": {
            "zone": "Warehouse",
            "timestamp": "2020-01-15T14:58:17.571Z",
            "battery": 45,
            "signal": 145,
            "x": 450,
            "y": 500
        },
        "alerts": [
            {
                "level": "warning",
                "date": "2020-01-15T14:58:17.571Z",
                "type": "position",
                "detail": "Detencion en zona A"
            }
        ]
    },
    {
        "id": "A77",
        "seed": "Seed type here",
        "type": "seed type here",
        "code": "codewillbe",
        "batch": "00AF",
        "description": "tag de pruebas",
        "state": "alert",
        "position": {
            "zone": "Warehouse",
            "timestamp": "2020-01-15T14:58:17.571Z",
            "battery": 45,
            "signal": 145,
            "x": 490,
            "y": 520
        },
        "alerts": [
            {
                "level": "alert",
                "date": "2020-01-15T14:58:17.571Z",
                "type": "proximity",
                "detail": "TOO CLOSE FOR COMFORT"
            }
        ]
    },
    {
        "id": "Z57",
        "seed": "Seed type here",
        "type": "seed type here",
        "code": "codewillbe",
        "batch": "00AG",
        "description": "tag de pruebas 02",
        "state": "alert",
        "position": {
            "zone": "Warehouse",
            "timestamp": "2020-01-15T14:58:17.571Z",
            "battery": 45,
            "signal": 145,
            "x": 390,
            "y": 720
        },
        "alerts": [
            {
                "level": "alert",
                "date": "2020-01-15T14:58:17.571Z",
                "type": "proximity",
                "detail": "TOO CLOSE FOR COMFORT"
            }
        ]
    },
    {
        "id": "002",
        "seed": "Seed type here",
        "type": "seed type here",
        "code": "codewillbe",
        "batch": "00AF",
        "description": "tag de pruebas",
        "state": "ok",
        "position": {
            "zone": "Cleaning",
            "timestamp": "2020-01-15T14:58:17.571Z",
            "battery": 45,
            "signal": 145,
            "x": 350,
            "y": 510
        },
        "alerts": []
    }
]


@bp.route('/tag', methods=['GET', 'POST'])
def tag_data():
    return "OK"


@bp.route('/tags')
def get_tags():
    return jsonify(tags)


@bp.route('/first_time')
def setup():
    db.drop_all()
    db.create_all()
    init_tag_types()
    init_zones()
    init_admin()
    init_inactivity()
    db.session.commit()
    return "DONE"


def init_zones():
    db.session.add(Zone())

    with open('app/api/zones.json') as f:
        zones = json.load(f)
        for zone in zones:
            min_x = zone['area'][0][0]
            min_y = zone['area'][0][1]
            max_x = zone['area'][1][0]
            max_y = zone['area'][1][1]
            new_zone = Zone(name=zone['name'], min_x=min_x,
                            min_y=min_y, max_x=max_x, max_y=max_y)
            db.session.add(new_zone)


def init_tag_types():
    types = ["CAJA", "BIN", "BANDEJA", "LIMPIEZA"]
    for t in types:
        tag_type = TagType(name=t)
        db.session.add(tag_type)


def init_admin():
    admin = User(username='admin', role='Admin')
    admin.set_password('password')
    db.session.add(admin)

def init_inactivity():
    rule_tag = InactivityAlertRule(time = 1, device_type = DeviceType.Tag)
    rule_connector = InactivityAlertRule(time = 1, device_type = DeviceType.Connector)
    db.session.add(rule_tag)
    db.session.add(rule_connector)
