from app.models import Position, Container, Tag, ZoneAlertRule, ZoneAlert, Baliza, Zone
from datetime import datetime


def zone_alert(tag):
    # Assuming that there is only one permanence rule by zone
    activated_alert = None
    if(not tag.container_id or not tag.active):
        return activated_alert

    rules = ZoneAlertRule.query.filter_by(active=True).all()
    rule_list = [a for a in rules if tag.zone.name in a.zones.split(',')]
    rule = rule_list[0] if len(rule_list) == 1 else None

    if rule and (tag.last_timestamp - tag.last_zone_timestamp).seconds/60 >= rule.time:
        batch_name = tag.container.batch.name if tag.container.batch else ''
        activated_alert = ZoneAlert(
            zone=tag.zone.name,tag=tag.address, batch=batch_name,container=tag.container.name, timestamp=datetime.utcnow(), rule_id=rule.id)
    return activated_alert


def check_zone_alert(alert):
    return ZoneAlert.query.filter_by(container=alert.container, rule_id=alert.rule_id, active=True).count() == 0

def check_baliza_zone(alert):
    zone = Zone.query.filter_by(name=alert.zone).first()
    active_baliza = Baliza.query.filter_by(zone_id=zone.id).first()
    if(active_baliza):
        active_baliza.activate(alert)
   