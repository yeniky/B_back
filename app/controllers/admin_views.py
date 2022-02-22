from app import admin, db
from flask_admin.contrib.sqla import ModelView
from app.models import Tag, Container, \
    Position, Batch, TagType, \
    Material, MaterialGroup, MaterialPricingGroup, Order, \
    OrderType, ZoneAlert, BatchAlert, ProximityAlert, ZoneAlertRule,\
    BatchAlertRule, ProximityAlertRule, ZoneEntry, BinBatchAssociation,\
    Zone, CleanupAlert, CleanupAlertRule, User, Baliza, Connector, MapInfo, InactivityAlertRule, InactivityAlert, Alert, AlertRule

admin.add_view(ModelView(Zone, db.session))
admin.add_view(ModelView(ZoneEntry, db.session))
admin.add_view(ModelView(Position, db.session))
admin.add_view(ModelView(TagType, db.session))
admin.add_view(ModelView(Tag, db.session))
admin.add_view(ModelView(Container, db.session))
admin.add_view(ModelView(Batch, db.session))
admin.add_view(ModelView(BinBatchAssociation, db.session))
admin.add_view(ModelView(Order, db.session))
admin.add_view(ModelView(OrderType, db.session))
admin.add_view(ModelView(Material, db.session))
admin.add_view(ModelView(MaterialPricingGroup, db.session))
admin.add_view(ModelView(MaterialGroup, db.session))
admin.add_view(ModelView(Connector, db.session))
admin.add_view(ModelView(Baliza, db.session))

admin.add_view(ModelView(Alert, db.session))
admin.add_view(ModelView(ZoneAlert, db.session))
admin.add_view(ModelView(BatchAlert, db.session))
admin.add_view(ModelView(ProximityAlert, db.session))
admin.add_view(ModelView(CleanupAlert, db.session))
admin.add_view(ModelView(InactivityAlert, db.session))

admin.add_view(ModelView(AlertRule, db.session))
admin.add_view(ModelView(ZoneAlertRule, db.session))
admin.add_view(ModelView(BatchAlertRule, db.session))
admin.add_view(ModelView(ProximityAlertRule, db.session))
admin.add_view(ModelView(CleanupAlertRule, db.session))
admin.add_view(ModelView(InactivityAlertRule, db.session))

admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(MapInfo, db.session))


