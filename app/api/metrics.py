from flask import jsonify, request
from app import db
from app.api import bp
from app.models import Batch,Container,ZoneEntry, BinBatchAssociation, Alert,ProximityAlert, ZoneAlert, BatchAlert, CleanupAlert, InactivityAlert
from app.utils.user_auth import token_auth
from app.models import Role
from app.utils.helpers import build_page
from app.utils.helpers import generate_order_by
from sqlalchemy.orm import with_polymorphic
from dateutil import parser


@bp.route('/metrics/zone', methods=['GET'])
@token_auth.login_required
def get_zone_entries():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    order_by = request.args.get('order_by', "")
    order = request.args.get('order', "asc")
    query = ZoneEntry.query
    if order_by:
        query = generate_order_by(query, ZoneEntry, order_by,order,ZoneEntry.prop_to_order)
    query = query.paginate(page, per_page, False)
    return jsonify(build_page(query,order_by,order, ZoneEntry.to_dict))

@bp.route('/metrics/filtered_zone', methods=['POST'])
@token_auth.login_required
def get_filtered_zone_entries():
    params = request.json
    query = ZoneEntry.query
    if('batch' in params):
        batchs = [x.id for x in Batch.query.filter(Batch.name.in_(params['batch'])).all()]
        query = query.filter(ZoneEntry.batch_id.in_(batchs))
    if('container' in params):
        containers =[x.id for x in Container.query.filter(Container.name.in_(params['container'])).all()]
        query = query.filter(ZoneEntry.container_id.in_(containers))
    if('zone' in params):
        query = query.filter(ZoneEntry.zone.in_(params['zone']))
    if('permanence' in params):
        query = query.filter(ZoneEntry.permanence_time>=params['permanence'][0],ZoneEntry.permanence_time<=params['permanence'][1])
    if('in_time' in params):
        query = query.filter(ZoneEntry.in_timestamp>=convert_date(params['in_time'][0]),ZoneEntry.in_timestamp<=convert_date(params['in_time'][1]))
    if('out_time' in params):
        query = query.filter(ZoneEntry.out_timestamp>=convert_date(params['out_time'][0]),ZoneEntry.out_timestamp<=convert_date(params['out_time'][1]))
    return jsonify([x.to_dict() for x in query.all()])

@bp.route('/metrics/association', methods=['GET'])
@token_auth.login_required
def get_associations():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    order_by = request.args.get('order_by', "")
    order = request.args.get('order', "asc")
    query = BinBatchAssociation.query
    if order_by:
        query = generate_order_by(query, BinBatchAssociation, order_by,order,BinBatchAssociation.prop_to_order)
    query = query.paginate(page, per_page, False)
    return jsonify(build_page(query,order_by,order,BinBatchAssociation.to_dict))

@bp.route('/metrics/filtered_association', methods=['POST'])
@token_auth.login_required
def get_filtered_associations():
    params = request.json
    query = BinBatchAssociation.query
    if('batch' in params):
        batchs = [x.id for x in Batch.query.filter(Batch.name.in_(params['batch'])).all()]
        query = query.filter(BinBatchAssociation.batch_id.in_(batchs))
    if('container' in params):
        containers =[x.id for x in Container.query.filter(Container.name.in_(params['container'])).all()]
        query = query.filter(BinBatchAssociation.container_id.in_(containers))
    if('permanence' in params):
        query = query.filter(BinBatchAssociation.permanence_time>=params['permanence'][0],BinBatchAssociation.permanence_time<=params['permanence'][1])
    if('in_time' in params):
        query = query.filter(BinBatchAssociation.in_timestamp>=convert_date(params['in_time'][0]),BinBatchAssociation.in_timestamp<=convert_date(params['in_time'][1]))
    if('out_time' in params):
        query = query.filter(BinBatchAssociation.out_timestamp>=convert_date(params['out_time'][0]),BinBatchAssociation.out_timestamp<=convert_date(params['out_time'][1]))
    return jsonify([x.to_dict() for x in query.all()])


@bp.route('/metrics/alert_history', methods=['GET'])
@token_auth.login_required
def get_alert_history():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    order_by = request.args.get('order_by', "")
    order = request.args.get('order', "asc")
    query = Alert.query
    if order_by:
        query = generate_order_by(query, Alert, order_by,order,Alert.prop_to_order)
    
    query = query.paginate(page, per_page, False)
    return jsonify(build_page(query,order_by,order,alert_history_to_metric))
    # return jsonify(zone_metric+batch_metric+proximity_metric+cleanup_metric+inactivity_metric)


@bp.route('/metrics/filtered_alert_history', methods=['POST'])
@token_auth.login_required
def filteres_alert_history():
    params = request.json
    get_alert_history(params)
    return jsonify(get_alert_history(params))

def get_alert_history(params):
    alerts  = Alert.query.all()
    result = []
    for a in alerts:
        print(a.__dict__)
        if filter_alert(a,params):
            result.append(alert_history_to_metric(a))
    return result

def filter_alert(alert,params):
    if('address' in params and (not hasattr(alert, 'tag') or not (alert.tag in params['address']))):
        return False
    if('bin' in params and (not hasattr(alert, 'container') or not (alert.container in params['bin']))):
        return False
    if('batch' in params and (not hasattr(alert, 'batch') or not (alert.batch in params['batch']))):
        return False
    if('zone' in params and (not hasattr(alert, 'zone') or not (alert.zone in params['zone']))):
        return False
    if('type' in params):
        types = [f'{t}_alert' for t in params['type']]
        if(not alert.owner_type in types):
            return False
    if('user' in params and (not alert.user or not alert.user.username in params['user'])):
        return False
    if('start_timestamp' in params):
        if not convert_date(params['start_timestamp'][0]) <= alert.timestamp <= convert_date(params['start_timestamp'][1]):
            return False
    if('end_timestamp' in params):
        if not alert.close_timestamp or not convert_date(params['end_timestamp'][0]) <= alert.close_timestamp <= convert_date(params['end_timestamp'][1]):
            return False
    return True

def convert_date(date):
    return parser.parse(date)
    
def alert_history_to_metric(alert):
    if(alert.owner_type == 'zone_alert'):
        return ZoneAlert.to_metric(alert)
    if(alert.owner_type == 'batch_alert'):
        return BatchAlert.to_metric(alert)
    if(alert.owner_type == 'proximity_alert'):
        return ProximityAlert.to_metric(alert)
    if(alert.owner_type == 'inactivity_alert'):
        return InactivityAlert.to_metric(alert)
    if(alert.owner_type == 'cleanup_alert'):
        return CleanupAlert.to_metric(alert)