from flask import jsonify, request
from app import db
from app.api import bp
from datetime import datetime
from app.models import ZoneAlert, BatchAlert, ProximityAlert, \
    ZoneAlertRule, ProximityAlertRule, BatchAlertRule, Batch, CleanupAlert, CleanupAlertRule, InactivityAlert
from app.api.errors import bad_request
from app.utils.user_auth import token_auth
from app.models import Role
import requests


@bp.route('/alerts', methods=['GET'])
@token_auth.login_required
def get_alerts():
    zone_alerts = ZoneAlert.query.filter_by(active=True).all()
    batch_alerts = BatchAlert.query.filter_by(active=True).all()
    proximity_alerts = ProximityAlert.query.filter_by(active=True).all()
    cleanup_alerts = CleanupAlert.query.filter_by(active=True).all()
    inactivity_alerts = InactivityAlert.query.filter_by(active=True).all()
    payload = {
        'zone': [z.to_dict() for z in zone_alerts],
        'batch': [z.to_dict() for z in batch_alerts],
        'proximity': [z.to_dict() for z in proximity_alerts],
        'cleanup': [z.to_dict() for z in cleanup_alerts],
        'inactivity': [z.to_dict() for z in inactivity_alerts]
    }
    return jsonify(payload)


@bp.route('/alerts/acknowledge', methods=['POST'])
@token_auth.login_required(role=[Role.Admin, Role.Supervisor])
def close_alert():
    user = token_auth.current_user()
    data = request.get_json()
    alert = None
    if data['alert_type'] == 'proximity':
        alert = ProximityAlert.query.filter_by(id=data['id']).first_or_404()
    elif data['alert_type'] == 'batch':
        alert = BatchAlert.query.filter_by(id=data['id']).first_or_404()
    elif data['alert_type'] == 'zone':
        alert = ZoneAlert.query.filter_by(id=data['id']).first_or_404()
    elif data['alert_type'] == 'cleanup':
        alert = CleanupAlert.query.filter_by(id=data['id']).first_or_404()
    elif data['alert_type'] == 'inactivity':
        alert = InactivityAlert.query.filter_by(id=data['id']).first_or_404()
    if alert == None:
        return jsonify({'error': 'no alert found'})
    alert.active = False
    alert.close_timestamp = datetime.utcnow()
    alert.user = user
    balizas = []
    if(data['alert_type']!="inactivity"):
        balizas = [*alert.balizas]
        alert.balizas.clear()
    db.session.commit()
    for b in balizas:
        b.check_deactive()
    try:
        requests.post('http://127.0.0.1:5001/closed_alert',
                      json={'data': alert.to_dict()})
    except requests.exceptions.ConnectionError as ec:
        print("Connection Error:", ec)
        pass
    return jsonify({'alert': alert.to_dict()})


@bp.route('/rules', methods=['GET'])
@token_auth.login_required
def get_rules():
    zone_alerts = ZoneAlertRule.query.filter_by(active=True).all()
    proximity_alerts = ProximityAlertRule.query.filter_by(active=True).all()
    batch_alerts = BatchAlertRule.query.filter_by(active=True).all()
    cleanup_alerts = CleanupAlertRule.query.all()
    payload = {
        'zone_rules': [z.to_dict() for z in zone_alerts],
        'batch_rules': [z.to_dict() for z in batch_alerts],
        'proximity_rules': [z.to_dict() for z in proximity_alerts],
        'cleanup_rules': [z.to_dict() for z in cleanup_alerts],
    }
    return jsonify(payload)


@bp.route('/rules/zone', methods=['POST'])
@token_auth.login_required(role=[Role.Admin])
def create_zone_rule():
    data = request.get_json()
    if(check_repited_zones(data['zones'])):
        return bad_request('A zone in this rule already exists in another rule')
    zone_rule = None
    updated_rule = update_time_rule(data['time'], data['zones'])
    if(updated_rule):
        zone_rule = updated_rule
    else:
        zone_rule = ZoneAlertRule(zones=','.join(
            data['zones']), time=data['time'])
        db.session.add(zone_rule)
        db.session.commit()
    return jsonify(zone_rule.to_dict())

@bp.route('/rules/zone/<id>', methods=['PUT'])
@token_auth.login_required(role=[Role.Admin])
def edit_zone_rule(id):
    data = request.get_json()
    zone_rule = ZoneAlertRule.query.filter_by(id=id).first_or_404()
    if(check_repited_zones(data['zones'],zone_rule)):
        return bad_request('A zone in this rule already exists in another rule')
    updated_rule = update_time_rule(data['time'], data['zones'],zone_rule)
    if(updated_rule):
        users= zone_rule.users
        db.session.delete(zone_rule)
        zone_rule = updated_rule
        zone_rule.users.extend(users)
    else:
        zone_rule.time = data['time']
        zone_rule.zones = ','.join(data['zones'])
    db.session.commit()
    return jsonify(zone_rule.to_dict())


def check_repited_zones(zones,rule = None):
    rules = ZoneAlertRule.query.filter_by(active=True).all()
    for z in zones:
        for r in rules:
            if(rule and r.id == rule.id):
                continue
            if z in r.zones.split(','):
                return True


def update_time_rule(time, zones,old_rule=None):
    rule = ZoneAlertRule.query.filter_by(time=time, active=True).first()
    if(rule and ((not old_rule) or old_rule.id!= rule.id)):
        old_zones = rule.zones.split(',')
        rule.zones = ','.join(list(set().union(zones, old_zones)))
        db.session.commit()
        return rule
    return None


@bp.route('/rules/zone/<zone_id>', methods=['DELETE'])
@token_auth.login_required(role=[Role.Admin])
def delete_zone_rule(zone_id):
    zone_rule = ZoneAlertRule.query.filter_by(id=zone_id).first_or_404()
    zone_rule.active = False
    db.session.commit()
    return jsonify({'status': 'ok'})


@bp.route('/rules/proximity', methods=['POST'])
@token_auth.login_required(role=[Role.Admin])
def create_proximity_rule():
    data = request.get_json()
    proximity_rule = ProximityAlertRule.query.first()
    if(proximity_rule):
        proximity_rule.distance = data['distance']
        proximity_rule.zones = ','.join(data['zones'])
    else:
        proximity_rule = ProximityAlertRule(
            distance=data['distance'],
            zones=','.join(data['zones'])
        )
        db.session.add(proximity_rule)
    db.session.commit()
    return jsonify(proximity_rule.to_dict())


@bp.route('/rules/proximity/<id>', methods=['DELETE'])
@token_auth.login_required(role=[Role.Admin])
def delete_proximity_rule(id):
    proximity_rule = ProximityAlertRule.query.filter_by(
        id=id).first_or_404()
    proximity_rule.active = False
    db.session.commit()
    return jsonify({'status': 'ok'})


@bp.route('/rules/batch', methods=['POST'])
@token_auth.login_required(role=[Role.Admin])
def create_batch_rule():
    data = request.get_json()
    batch_rule = BatchAlertRule.query.first()
    if(batch_rule):
        batch_rule.distance = data['distance']
        batch_rule.time = data['time']
    else:
        batch_rule = BatchAlertRule(
            distance=data['distance'],
            time=data['time']
        )
        db.session.add(batch_rule)
    db.session.commit()
    return jsonify(batch_rule.to_dict())


@bp.route('/rules/batch/<batch_id>', methods=['DELETE'])
@token_auth.login_required(role=[Role.Admin])
def delete_batch_rule(batch_id):
    batch_rule = BatchAlertRule.query.filter_by(id=batch_id).first_or_404()
    # db.session.delete(batch_rule)
    batch_rule.active = False
    db.session.commit()
    return jsonify({'status': 'ok'})


@bp.route('/rules/subscribe', methods=['POST'])
@token_auth.login_required
def subscribe():
    user = token_auth.current_user()
    data = request.get_json()
    rule = None
    if data['alert_type'] == 'proximity':
        rule = ProximityAlertRule.query.filter_by(id=data['id']).first_or_404()
    elif data['alert_type'] == 'batch':
        rule = BatchAlertRule.query.filter_by(id=data['id']).first_or_404()
    elif data['alert_type'] == 'zone':
        rule = ZoneAlertRule.query.filter_by(id=data['id']).first_or_404()
    elif data['alert_type'] == 'cleanup':
        rule = CleanupAlertRule.query.filter_by(id=data['id']).first_or_404()
    if rule == None:
        return jsonify({'error': 'no rule found'})
    rule.users.append(user)
    db.session.commit()
    return jsonify({'status': 'ok'})

@bp.route('/rules/subscriptions', methods=['GET'])
@token_auth.login_required
def get_subscription():
    user = token_auth.current_user()
    return jsonify(user.subscriptions())

@bp.route('/rules/unsubscribe', methods=['POST'])
@token_auth.login_required
def unsubscribe():
    user = token_auth.current_user()
    data = request.get_json()
    rule = None
    if data['alert_type'] == 'proximity':
        rule = ProximityAlertRule.query.filter_by(id=data['id']).first_or_404()
    elif data['alert_type'] == 'batch':
        rule = BatchAlertRule.query.filter_by(id=data['id']).first_or_404()
    elif data['alert_type'] == 'zone':
        rule = ZoneAlertRule.query.filter_by(id=data['id']).first_or_404()
    elif data['alert_type'] == 'cleanup':
        alert = CleanupAlert.query.filter_by(id=data['id']).first_or_404()
    if rule == None:
        return jsonify({'error': 'no rule found'})
    rule.users.remove(user)
    db.session.commit()
    return jsonify({'status': 'ok'})
