
from app.models import ProximityAlert, ProximityAlertRule, Tag, Container, Batch, Baliza,Zone
from app import db
from datetime import datetime
from app.utils.helpers import Utils


def proximity_alerts(tag):
    activated_alerts = []

    if(not tag.container_id or not tag.container.batch or not tag.active):
        return activated_alerts

    rule = ProximityAlertRule.query.filter_by(active=True).first()

    if(rule):
        rule_zones = rule.zones.split(',')
        if(tag.zone.name in rule_zones):
            return activated_alerts
        containers = get_containers(
            tag.container.batch_id, rule_zones)
        near_containers = get_near_containers(tag, containers, rule.distance)
        for nc in near_containers:
            batch_name = tag.container.batch.name if tag.container.batch else ''
            batch_name1 = nc.batch.name if nc.batch else ''
            alert1 = ProximityAlert(container=tag.container.name,tag=tag.address,batch=batch_name, rule_id=rule.id,
                                    timestamp=datetime.utcnow(), container1=nc.name, zone=tag.zone.name,zone1=nc.tag.zone.name,distance=int(rule.distance))
            alert2 = ProximityAlert(container1=tag.container.name, rule_id=rule.id,
                                    timestamp=datetime.utcnow(), container=nc.name,tag=nc.tag.address,batch=batch_name1, zone1=tag.zone.name,zone=nc.tag.zone.name,distance=int(rule.distance))
            activated_alerts.append(alert1)
            activated_alerts.append(alert2)
    return activated_alerts


def check_proximity_alert(alert):
    return ProximityAlert.query.filter(ProximityAlert.container == alert.container,ProximityAlert.container1 == alert.container1,
                                       ProximityAlert.rule_id == alert.rule_id,
                                       ProximityAlert.active == True).count() == 0


def get_containers(batch_id, zones):

    query = db.session.query(
        Tag, Container
    ).filter(
        Tag.container_id == Container.id
    ).filter(
        Container.batch_id != batch_id
    ).all()
    return [x[1] for x in query if not x[0].zone.name in zones]


def get_near_containers(tag, containers, distance):
    return [c for c in containers if Utils.get_distance(tag.last_x, tag.last_y, c.tag.last_x, c.tag.last_y) <= distance]

def check_baliza_proximity(alert):
    zone = Zone.query.filter_by(name=alert.zone).first()
    active_baliza = Baliza.query.filter_by(zone_id=zone.id).first()
    if(active_baliza):
        active_baliza.activate(alert)
   
  