from app.models import InactivityAlert, InactivityAlertRule, DeviceType, Connector, Tag, Status
from app.utils.alert import save_and_emit
from datetime import datetime
from app import scheduler
from app import db

@scheduler.task('interval', id='inactivity_job', seconds=30, misfire_grace_time=900)
def inactivity_alert():
    print("task_running")
    app = scheduler.app
    with app.app_context():
        connector_alerts = check_connector()
        tag_alerts = check_tag()
        save_and_emit(connector_alerts+tag_alerts,check_inactivity_alert,mail=False)

def check_connector():
    alerts = []
    rule = InactivityAlertRule.query.filter_by(device_type=DeviceType.Connector,active=True).first()
    if not rule:
        return []
    for connector in Connector.query.all():
        if not connector.active:
            continue
        if(datetime.utcnow() - connector.last_timestamp).seconds/60 >= rule.time:
            new_alert = InactivityAlert(rule=rule,time=rule.time,device_type = str(rule.device_type), tag=connector.mac, timestamp=datetime.utcnow())
            alerts.append(new_alert)
            connector.status = Status.Offline
            db.session.commit()
    return alerts

def check_tag():
    alerts = []
    rule = InactivityAlertRule.query.filter_by(device_type=DeviceType.Tag,active=True).first()
    if not rule:
        return []
    for tag in Tag.query.all():
        if not tag.active:
            continue
        if(datetime.utcnow() - tag.last_timestamp).seconds/60 >= rule.time:
            new_alert = InactivityAlert(rule=rule,time=rule.time,device_type = str(rule.device_type), tag=tag.address, timestamp=datetime.utcnow())
            alerts.append(new_alert)
            tag.status = Status.Offline
            db.session.commit()
    return alerts


def check_inactivity_alert(alert):
    return InactivityAlert.query.filter_by(tag=alert.tag,rule=alert.rule, active=True).count() == 0