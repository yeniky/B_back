from app.models import Tag, Container, CleanupAlertRule, CleanupAlert, Baliza, Zone
from app import db
from datetime import datetime
from app.utils.helpers import Utils


def update_cleanup_rule(tag):
    if(not tag.container_id or not tag.active):
        return 
    if(tag.container.tag_type.name != "LIMPIEZA"):
        return 

    rule = get_cleanup_rule(tag)
    if(rule and rule.zone_name != tag.zone.name):
        rule.zone_name = tag.zone.name
        db.session.commit()

def check_new_alerts(tag):
    zone_id = tag.zone.id
    tags = Tag.query.filter_by(zone_id=zone_id).all()
    alerts = []
    for t in tags:
        if(t.container and t.container.tag_type.name != "LIMPIEZA"):
            t_alerts = cleanup_alerts(t)
            alerts = alerts + t_alerts
    return alerts


def cleanup_alerts(tag):
    if(not tag.container_id or not tag.active or tag.zone.name == "Sin Zona"):
        return []
    if(tag.container.tag_type.name == "LIMPIEZA"):
        return check_new_alerts(tag)
    rules = CleanupAlertRule.query.filter_by(zone_name=tag.zone.name).all()
    alerts = []
    for rule in rules:
        batch_name = tag.container.batch.name if tag.container.batch else ''
        new_alert = CleanupAlert(
            zone=tag.zone.name, containerCleanup=rule.container.name,rule_id=rule.id, container=tag.container.name,tag=tag.address,batch=batch_name,timestamp=datetime.utcnow())
        alerts.append(new_alert)
    return alerts

def get_cleanup_rule(tag):
    return CleanupAlertRule.query.filter_by(container_id=tag.container_id).first()

def check_cleanup_alert(alert):
    result = CleanupAlert.query.filter_by(containerCleanup=alert.containerCleanup,
                                          container=alert.container, zone=alert.zone, active=True).count() == 0
    return result

def check_baliza_cleanup(alert):
    zone = Zone.query.filter_by(name=alert.zone).first()
    active_baliza = Baliza.query.filter_by(zone_id=zone.id).first()
    if(active_baliza):
        active_baliza.activate(alert)
   