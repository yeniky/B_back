
from app import db
from app.models import Batch, BatchAlertRule, BatchAlert, Container, Tag, Baliza, Zone
from app.utils.helpers import Utils
from datetime import datetime


def batch_alert(tag):

    if(not tag.container_id or not tag.active):
        return None

    batch = get_batch(tag)
    rule = get_rule()
    if (not batch or not rule):
        return None
    if(not check_active_alert(tag, rule)):
        return None

    inactive_alert = BatchAlert.query.filter_by(
        container=tag.container.name, rule_id=rule.id, triggered=False).first()

    if not is_outlier(tag, batch, rule.distance):
        if(inactive_alert):
            delete_alert(inactive_alert)
        return None

    if inactive_alert:
        if(tag.last_timestamp - inactive_alert.first_timestamp).seconds/60 >= rule.time:
            activate_batch_alert(inactive_alert)

            return inactive_alert
    else:
        create_inactive_batch_alert(tag, rule, batch)
        return None


def activate_batch_alert(inactive_alert):
    inactive_alert.active = True
    inactive_alert.triggered = True
    inactive_alert.timestamp = datetime.utcnow()
    db.session.commit()


def delete_alert(alert):
    db.session.delete(alert)
    db.session.commit()


def create_inactive_batch_alert(tag, rule, batch):
    new_alert = BatchAlert(rule_id=rule.id, container=tag.container.name,tag=tag.address,zone=tag.zone.name,
                           batch=batch.name, first_timestamp=tag.last_timestamp,active=False,time=int(rule.time),distance=int(rule.distance))
    db.session.add(new_alert)
    db.session.commit()


def is_outlier(tag, batch, distance):
    if(len(batch.containers)<=1):
        return False
    for container in batch.containers:
        if(container.tag and tag.id != container.tag.id and Utils.get_distance(tag.last_x, tag.last_y, container.tag.last_x, container.tag.last_y) < distance):
            return False
    return True


def check_active_alert(tag, rule):
    return BatchAlert.query.filter_by(
        container=tag.container.name, rule_id=rule.id, active=True).count() == 0


def check_batch_alert(alert):
    return BatchAlert.query.filter_by(container=alert.container, rule_id=alert.rule_id, active=True).count() == 0


def get_batch(tag):
    query = db.session.query(
        Tag, Container, Batch
    ).filter(
        Tag.container_id == Container.id
    ).filter(
        Container.batch_id == Batch.id
    ).filter(Tag.id == tag.id).first()
    return query[2] if query else None


def get_rule():
    return BatchAlertRule.query.first()

def check_baliza_batch(alert):
    zone = Zone.query.filter_by(name=alert.zone).first()
    active_baliza = Baliza.query.filter_by(zone_id=zone.id).first()
    if(active_baliza):
        active_baliza.activate(alert)