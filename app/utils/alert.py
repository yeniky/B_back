import requests
from app import db
from app.utils.zone_alert import zone_alert, check_zone_alert, check_baliza_zone
from app.utils.batch_alert import batch_alert, check_batch_alert,check_baliza_batch
from app.utils.proximity_alert import proximity_alerts, check_proximity_alert, check_baliza_proximity
from app.utils.cleanup_alert import cleanup_alerts, check_cleanup_alert, check_baliza_cleanup
from app.utils.user_auth import send_alert_email


def check_alerts(tags):
    save_and_emit([zone_alert(t) for t in tags], check_zone_alert,check_baliza_zone)
    save_and_emit([batch_alert(t) for t in tags], check_batch_alert,check_baliza_batch, False)
    for proximity_alert in [proximity_alerts(t) for t in tags]:
        save_and_emit(proximity_alert, check_proximity_alert,check_baliza_proximity)
    for cleanup_alert in [cleanup_alerts(t) for t in tags]:
        save_and_emit(cleanup_alert, check_cleanup_alert,check_baliza_cleanup)


def save_and_emit(alerts, check,baliza=None, save=True, mail = True):
    payload = []
    for alert in alerts:
        if(alert and (not save or check(alert))):
            if(save):
                db.session.add(alert)
                db.session.commit()
            payload.append(alert.to_dict())
            if baliza:
                baliza(alert)
            if(mail and len(alert.rule.users)>0):
                send_alert_email([u.email for u in alert.rule.users], alert.to_mail())

    if(len(payload) > 0):
        try:
            requests.post('http://127.0.0.1:5001/data_alert',
                          json={'data': payload})
        except requests.exceptions.ConnectionError:
            pass
