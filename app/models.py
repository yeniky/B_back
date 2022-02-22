from app import db
from datetime import datetime, timezone
from app.utils.helpers import Utils
from decimal import Decimal
import json
from sqlalchemy.orm import backref
from werkzeug.security import generate_password_hash, check_password_hash
import base64
import os
import enum
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import func, select
from app.utils.helpers import send_baliza_message
from sqlalchemy.ext.declarative import declared_attr


class DeviceType(enum.Enum):
    Tag = "Tag"
    Connector = "Connector"

    def __str__(self):
        return self.value

class Status(enum.Enum):
    Online = "Online"
    Offline = "Offline"
    
    def __str__(self):
        return self.value

class Role(enum.Enum):
    User = "User"
    Admin = "Admin"
    Supervisor = "Supervisor"

    def __str__(self):
        return self.value

class Container(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True)
    tag_type_id = db.Column(db.Integer, db.ForeignKey('tag_type.id'))
    description = db.Column(db.Text, default='')
    tag = db.relationship('Tag', backref=backref(
        'container'), uselist=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'))

    @staticmethod
    def create_container(name, type, description, batch=False):
        new_container = Container(
            name=name,
            description=description
        )
        if batch:
            batch_elem = Batch.query.filter_by(name=batch).first()
            if batch_elem:
                new_container.batch = batch_elem
        if type:
            type_obj = TagType.query.filter_by(name=type).first()
            if type_obj:
                new_container.tag_type = type_obj
        db.session.add(new_container)
        return new_container

    def set_tag(self, address):
        if self.tag:
            return {'error': 'container already has a tag'}
        tag = Tag.get_tag(address)
        if tag and tag.container:
            return {'error': 'tag already used with another container'}
        self.tag = tag
        if(tag):
            ZoneEntry.create_new_zone_entry(
                self.id, tag.zone.name, datetime.utcnow())
            if(self.tag_type.name == "LIMPIEZA"):
                CleanupAlertRule.create(self)
        return {'status': 'ok'}

    def unset_tag(self):
        self.tag = None
        if(self.tag_type.name == "LIMPIEZA"):
            CleanupAlertRule.remove(self)

        return {'status': 'ok'}

    def edit_container(self, data):
        if 'name' in data and self.name != data['name']:
            self.name = data['name']
        if 'description' in data and self.description != data['description']:
            self.description = data['description']
        if 'type' in data and self.tag_type != data['type']:
            type_obj = TagType.query.filter_by(name=data['type']).first()
            if type_obj:
                if(type_obj.name == "LIMPIEZA" and self.tag):
                    CleanupAlertRule.create(self)
                if(self.tag_type.name == "LIMPIEZA" and self.tag):
                    CleanupAlertRule.remove(self)
                self.tag_type = type_obj
        if 'batch' in data and data['batch']:
            batch_elem = Batch.query.filter_by(name=data['batch']).first()
            if batch_elem and self.batch_id != batch_elem.id:
                if(self.batch):
                    BinBatchAssociation.close_association(
                        self.id, self.batch_id, datetime.utcnow())
                self.batch = batch_elem
                BinBatchAssociation.create_new_association(
                    self.id, self.batch.id, datetime.utcnow())
        else:
            if(self.batch):
                BinBatchAssociation.close_association(
                    self.id, self.batch_id, datetime.utcnow())
            self.batch = None

    def to_dict(self):
        payload = {
            'id': self.id,
            'name': self.name,
            'type': self.tag_type.name if self.tag_type else '',
            'batch': self.batch.name if self.batch else '',
            'tag': self.tag.address if self.tag else '',
            'description': self.description,
        }
        return payload

    def prop_to_order(field):
        prop_order = {
            'name':'name',
            'type': 'tag_type.name',
            'batch': 'batch.name',
            'tag': 'tag.address',
            'description': 'description'
        }
        if(field not in prop_order):
            return ""
        else:
            return prop_order[field]

class Batch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True)
    type = db.Column(db.Enum("in", "out"))  # expects to be "in" or "out"
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    containers = db.relationship('Container', backref='batch')
    active = db.Column(db.Boolean, default=True)

    @hybrid_property
    def quantity(self):
        return len(self.containers)

    @quantity.expression
    def quantity(cls):
        return (select([func.count(Container.id)])
            .where(Container.batch_id == cls.id)) 

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'quantity': self.quantity,
            'type': self.type,
            'order': self.order.to_dict() if self.order else None,
            'containers': [c.to_dict() for c in self.containers],
            'active': self.active
        }
    
    def prop_to_order(field):
        prop_order = {
            'name':'name',
            'quantity': 'quantity',
            'order': 'order.name',
            'material': 'order.material.name',
            'material_description': 'order.material.description',
            'material_group': 'order.material.material_group.name',
            'material_group_description': 'order.material.material_group.description',
            'material_pricing': 'order.material.material_pricing_group.name',
            'material_pricing_description': 'order.material.material_pricing_group.description',
            'type': 'type',
            'active': 'active'
        }

        if(field not in prop_order):
            return ""
        else:
            return prop_order[field]


class Zone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), default='Sin Zona')
    min_x = db.Column(db.Integer, default=-1)
    min_y = db.Column(db.Integer, default=-1)
    max_x = db.Column(db.Integer, default=-1)
    max_y = db.Column(db.Integer, default=-1)
    tags = db.relationship('Tag', backref='zone')
    balizas = db.relationship('Baliza', backref='zone')

    def to_dict(self):
        return {
            "name": self.name,
            "area": [
                [self.min_x, self.min_y],
                [self.max_x, self.max_y]
            ]
        }


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(10), unique=True)
    last_x = db.Column(db.Numeric(precision=18, scale=5))
    last_y = db.Column(db.Numeric(precision=18, scale=5))
    last_z = db.Column(db.Numeric(precision=18, scale=5))
    last_timestamp = db.Column(db.DateTime())
    active = db.Column(db.Boolean, default=True)
    signal = db.Column(db.Integer)
    # Time of first entry to last zone
    last_zone_timestamp = db.Column(db.DateTime())
    container_id = db.Column(db.Integer, db.ForeignKey('container.id'))
    positions = db.relationship('Position', backref='tag')
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id'))
    status = db.Column(db.Enum(Status), default=Status.Online)

    def new_position(self, x, y, z, zone, battery=99, signal=99):
        if(not zone):
            zone = Zone.query.filter_by(name='Sin Zona').first()
        new_position = Position(
            timestamp=datetime.utcnow(),
            battery=battery,
            signal=signal,
            x=x,
            y=y,
            z=z,
            zone=zone.name,
            tag=self
        )
        self.status = Status.Online
        self.last_x = x
        self.last_y = y
        self.last_z = z
        self.signal = signal
        if(not self.zone or self.zone.id != zone.id):
            if(self.container_id and self.zone):
                ZoneEntry.change_old_zone_entry(
                    self.container_id, self.zone.name, new_position.timestamp)
                ZoneEntry.create_new_zone_entry(
                    self.container_id, zone.name, new_position.timestamp)

            self.last_zone_timestamp = datetime.utcnow()

        self.zone = zone
        self.last_timestamp = datetime.utcnow()
        db.session.add(new_position)
        return new_position

    def to_dict(self):
        container = self.container if self.container else ''
        batch = container.batch if container else ''
        order = batch.order if batch else ''
        payload = {
            'id': self.id,
            'address': self.address,
            'active': self.active,
            'position': self.last_position,
            'container': container.name if container else '',
            'type': container.tag_type.name if container else '',
            'batch': batch.name if batch else '',
            'order': order.name if order else '',
            'status': str(self.status)
        }
        return payload

    def prop_to_order(field):
        prop_order = {
            'address': 'address',
            'active': 'active',
            'container': 'container.name',
            'batch': 'container.batch.name',
            'order': 'order.name',
            'position.timestamp': 'last_timestamp',
            'position.zone': 'zone.name',
            'position.signal': 'signal',
            'type': 'container.tag_type.name'
        }
        if(field not in prop_order):
            return ""
        else:
            return prop_order[field]


    @ property
    def last_position(self):
        return {
            'timestamp': self.last_timestamp.replace(tzinfo=timezone.utc).isoformat() if self.last_timestamp else '',
            'x': str(self.last_x.quantize(Decimal('.01'))) if type(self.last_x) is Decimal else str(round(self.last_x, 2)),
            'y': str(self.last_y.quantize(Decimal('.01'))) if type(self.last_y) is Decimal else str(round(self.last_y, 2)),
            'z': str(self.last_z.quantize(Decimal('.01'))) if type(self.last_z) is Decimal else str(round(self.last_z, 2)),
            'zone': self.zone.name,
            'signal': self.signal
        }

    @ staticmethod
    def get_tag(addr):
        return Tag.query.filter_by(address=addr).first()

    def __str__(self):
        return f'<Tag {self.address}>'

    @ staticmethod
    def create_tag(address, container=None):
        new_tag = Tag(
            address=address,
            state="active",
            container=container,
        )
        db.session.add(new_tag)
        return new_tag


class TagType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(10))
    description = db.Column(db.String(50))
    containers = db.relationship('Container', backref='tag_type')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }


class Position(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime())
    battery = db.Column(db.Integer)
    signal = db.Column(db.Integer)
    x = db.Column(db.Numeric(precision=18, scale=5))
    y = db.Column(db.Numeric(precision=18, scale=5))
    z = db.Column(db.Numeric(precision=18, scale=5))
    zone = db.Column(db.String(20))

    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id'))

    def to_dict(self, with_tag=False):
        # Depending on the DB, it could be float or decimal what is stored
        x = str(self.x.quantize(Decimal('.01'))) if type(
            self.x) is Decimal else str(round(self.x, 2))
        y = str(self.y.quantize(Decimal('.01'))) if type(
            self.y) is Decimal else str(round(self.y, 2))
        z = str(self.z.quantize(Decimal('.01'))) if type(
            self.z) is Decimal else str(round(self.z, 2))
        data = {
            'timestamp': self.timestamp.replace(tzinfo=timezone.utc).isoformat(),
            'x': x,
            'y': y,
            'z': z,
            'battery': self.battery,
            'signal': self.signal,
            'tag': self.tag.address,
            'zone': self.zone
        }
        if with_tag:
            data['tag'] = self.tag.address
        return data

    @ staticmethod
    def create(message):

        zones = Zone.query.all()
        data = Utils.parse_message(message)
        if data == "invalid message":
            return

        tag = Tag.query.filter_by(address=data['addr']).first()

        # proteccion (activar para evitar DDoS a partir de mensajes)
        last_pos_time = Position.query.filter_by(
            tag=tag).order_by(Position.id.desc()).first()
        if tag:
            time_elapsed = datetime.utcnow() - last_pos_time.timestamp
            if time_elapsed.seconds < 5:
                return
        else:
            tag = Tag(address=data['addr'])
            db.session.add(tag)
            db.session.commit()

        del data['addr']
        data['zone'] = Utils.check_zones([data['x'], data['y']], zones)
        # new_position = tag.new_position(data['x'], data['y'], data['z'], signal=data['signal'])
        new_position = tag.new_position(**data)
        # LOGICA DE ALARMAS

        return tag


class MaterialGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text)
    name = db.Column(db.String(20))
    materials = db.relationship('Material', backref='material_group')

    def to_dict(self):
        return {
            'id': self.id,
            'description': self.description,
            'name': self.name
        }

    def prop_to_order(field):
        prop_order = {
            'description': 'description',
            'name': 'name',
        }
        if(field not in prop_order):
            return ""
        else:
            return prop_order[field]


class MaterialPricingGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text)
    name = db.Column(db.String(20))
    materials = db.relationship('Material', backref='material_pricing_group')

    def to_dict(self):
        return {
            'id': self.id,
            'description': self.description,
            'name': self.name
        }

    def prop_to_order(field):
        prop_order = {
            'description': 'description',
            'name': 'name',
        }
        if(field not in prop_order):
            return ""
        else:
            return prop_order[field]


class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True)
    material_description = db.Column(db.Text)
    material_group_id = db.Column(
        db.Integer, db.ForeignKey('material_group.id'))
    material_pricing_group_id = db.Column(
        db.Integer, db.ForeignKey('material_pricing_group.id'))
    reproduction_type = db.Column(db.String(20))
    phase = db.Column(db.String(20))
    package_type = db.Column(db.String(20))
    variety_name = db.Column(db.String(20))
    orders = db.relationship('Order', backref='material')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.material_description,
            'material_group': self.material_group.name if self.material_group else '',
            'material_pricing_group': self.material_pricing_group.name if self.material_pricing_group else '',
            'reproduction_type': self.reproduction_type,
            'phase': self.phase,
            'package_type': self.package_type,
            'variety_name': self.variety_name,
            'material_group_description':self.material_group.description if self.material_group else '',
            'material_pricing_group_description':self.material_pricing_group.description if self.material_pricing_group else '',
        }

    def prop_to_order(field):
        prop_order = {
            'name': 'name',
            'description': 'material_description',
            'material_group': 'material_group.name',
            'material_pricing_group': 'material_pricing_group.name',
            'material_group_description': 'material_group.description',
            'material_pricing_group_description': 'material_pricing_group.description',
            'reproduction_type': 'reproduction_type',
            'phase': 'phase',
            'package_type':'package_type',
            'variety_name': 'variety_name'
        }
        if(field not in prop_order):
            return ""
        else:
            return prop_order[field]


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True)
    order_type_id = db.Column(db.Integer, db.ForeignKey('order_type.id'))
    material_id = db.Column(db.Integer, db.ForeignKey('material.id'))
    date_start = db.Column(db.DateTime)
    date_finish = db.Column(db.DateTime)
    agreement = db.Column(db.String(20))
    purch_doc = db.Column(db.String(20))
    active = db.Column(db.Boolean, default=True)
    crop_year = db.Column(db.Integer)
    batchs = db.relationship('Batch', backref='order')

    @hybrid_property
    def in_batches(self):
        return sum(map(lambda i: i.type == 'in', self.batchs))

    @hybrid_property
    def out_batches(self):
        return sum(map(lambda i: i.type == 'out', self.batchs))

    @out_batches.expression
    def out_batches(cls):
        return (select([func.count(Batch.id)])
            .where(Batch.order_id == cls.id).where(Batch.type=="out")) 

    @in_batches.expression
    def in_batches(cls):
        return (select([func.count(Batch.id)])
            .where(Batch.order_id == cls.id).where(Batch.type=="in"))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'active': self.active,
            'crop_year': self.crop_year,
            'start_date': self.date_start.replace(tzinfo=timezone.utc).isoformat() if self.date_start else '',
            'end_date': self.date_finish.replace(tzinfo=timezone.utc).isoformat() if self.date_finish else '',
            'agreement': self.agreement,
            'purch_doc': self.purch_doc,
            'batchs': [b.name for b in self.batchs],
            'order_type': self.order_type.name if self.order_type else '',
            'material': self.material.name if self.material else '',
            'material_description': self.material.material_description if self.material else '',
            'material_group': self.material.material_group.name if self.material and self.material.material_group else '',
            'material_group_description': self.material.material_group.description if self.material and self.material.material_group else '',
            'material_pricing': self.material.material_pricing_group.name if self.material and self.material.material_pricing_group else '',
            'material_pricing_description': self.material.material_pricing_group.description if self.material and self.material.material_pricing_group else '',
            'in_batches': self.in_batches,
            'out_batches': self.out_batches,
        }

    def prop_to_order(field):
        prop_order = {
            'name': 'name',
            'active': 'active',
            'crop_year': 'crop_year',
            'start_date': 'date_start',
            'end_date': 'date_finish',
            'agreement': 'agreement',
            'purch_doc': 'purch_doc',
            'order_type': 'order_type.name',
            'material': 'material.name',
            'material_description': 'material.material_description',
            'material_group': 'material.material_group.name',
            'material_group_description': 'material.material_group.description',
            'material_pricing': 'material.material_pricing_group.name',
            'material_pricing_description': 'material.material_pricing_group.description',
            'in_batches': 'in_batches',
            'out_batches': 'out_batches',
        }
        if(field not in prop_order):
            return ""
        else:
            return prop_order[field]

class OrderType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(10))
    description = db.Column(db.String(50))
    orders = db.relationship('Order', backref='order_type')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }

class Alert(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime)
    active = db.Column(db.Boolean, default=True)
    close_timestamp = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    rule_id = db.Column(db.Integer, db.ForeignKey('alertRule.id'))
    rule = db.relationship('AlertRule', uselist=False)

    balizas = db.relationship(
        'Baliza',secondary='activation', back_populates='alerts')

    owner_type = db.Column(db.String(20))

    __mapper_args__ = {
        'polymorphic_on': owner_type,
        'polymorphic_identity': 'alert',
        'with_polymorphic': '*'
    }

    def prop_to_order(field):
        prop_order = {
            'id': 'id',
            'type': 'owner_type',
            'start_timestamp': 'timestamp',
            'end_timestamp': 'close_timestamp',
            'user': 'user.username',
            'address':'tag',
            'batch': 'batch',
            'bin': 'container',
            'zone': 'zone',
        }
        if(field not in prop_order):
            return ""
        else:
            return prop_order[field]  

class ZoneAlert(Alert):
    zone = db.Column(db.String(20))
    container = db.Column(db.String(20))
    batch = db.Column(db.String(20),default='')
    tag = db.Column(db.String(20),default='')

    __mapper_args__ = {
        'polymorphic_identity': 'zone_alert'
    }

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp':  self.timestamp.replace(tzinfo=timezone.utc).isoformat(),
            'alert_type': 'zone',
            'active': self.active,
            'data': {
                'zone': self.zone,
                'container': self.container,
            }
        }

    def to_metric(self):
        return {
            'id': self.id,
            'tag': self.tag,
            'container': self.container,
            'batch': self.batch,
            'zone': self.zone,
            'alert_type': 'zone',
            'time': self.rule.time if self.rule else '',
            'activation_timestamp': self.timestamp.replace(tzinfo=timezone.utc).isoformat(),
            'close_timestamp': self.close_timestamp.replace(tzinfo=timezone.utc).isoformat() if self.close_timestamp else '',
            'user': self.user.username if self.user else ''
        }

    def to_mail(self):
        return f'Alerta de permanencia activa!!!\n Zona:{self.zone}\n Bin: {self.container.name}\n Tiempo: {self.rule.time} minuto(s) '

class InactivityAlert(Alert):
    device_type = db.Column(db.String(40))

    @declared_attr
    def tag(cls):
        return Alert.__table__.c.get('tag',db.Column(db.String(20)))

    @declared_attr
    def time(cls):
        return Alert.__table__.c.get('time',db.Column(db.Integer))
   
    __mapper_args__ = {
        'polymorphic_identity': 'inactivity_alert'
    }

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.replace(tzinfo=timezone.utc).isoformat(),
            'alert_type': 'inactivity',
            'active': self.active,
            'data': {
                'device_type': str(self.device_type),
                'device_mac': self.tag,
                'time': self.time
            }
        }

    def to_metric(self):
        return {
            'id': self.id,
            'device_type': str(self.device_type),
            'device_mac': self.tag,
            'time': self.time ,
            'alert_type': 'inactivity',
            'activation_timestamp': self.timestamp.replace(tzinfo=timezone.utc).isoformat(),
            'close_timestamp': self.close_timestamp.replace(tzinfo=timezone.utc).isoformat() if self.close_timestamp else '',
            'user': self.user.username if self.user else ''
        }

class BatchAlert(Alert):
    first_timestamp = db.Column(db.DateTime)
    triggered = db.Column(db.Boolean, default=False)

    @declared_attr
    def distance(cls):
        return Alert.__table__.c.get('distance',db.Column(db.Integer))

    @declared_attr
    def time(cls):
        return Alert.__table__.c.get('time',db.Column(db.Integer))

    @declared_attr
    def container(cls):
        return Alert.__table__.c.get('container',db.Column(db.String(20)))
    
    @declared_attr
    def zone(cls):
        return Alert.__table__.c.get('zone',db.Column(db.String(20)))
    
    @declared_attr
    def tag(cls):
        return Alert.__table__.c.get('tag',db.Column(db.String(20)))
    
    @declared_attr
    def batch(cls):
        return Alert.__table__.c.get('batch',db.Column(db.String(20)))
   
    __mapper_args__ = {
        'polymorphic_identity': 'batch_alert'
    }

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.replace(tzinfo=timezone.utc).isoformat(),
            'alert_type': 'batch',
            'active': self.active,
            'data': {
                'batch': self.batch,
                'container': self.container
            }
        }

    def to_metric(self):
        return {
            'id': self.id,
            'container': self.container,
            'tag': self.tag,
            'batch': self.batch,
            'zone': self.zone,
            'alert_type': 'batch',
            'distance': round(self.distance),
            'time': round(self.time),
            'activation_timestamp': self.timestamp.replace(tzinfo=timezone.utc).isoformat(),
            'close_timestamp': self.close_timestamp.replace(tzinfo=timezone.utc).isoformat() if self.close_timestamp else '',
            'user': self.user.username if self.user else ''
        }

    
    def to_mail(self):
        return f'Alerta de separación activa!!!\n  Bin: {self.container.name}\n Batch:{self.container.batch.name}\n Distancia:{self.rule.distance}\n Tiempo:{self.rule.time} minuto(s)'

class ProximityAlert(Alert):
    container1 = db.Column(db.String(40)) 
    zone1 = db.Column(db.String(40))

    @declared_attr
    def distance(cls):
        return Alert.__table__.c.get('distance',db.Column(db.Integer))

    @declared_attr
    def zone(cls):
        return Alert.__table__.c.get('zone',db.Column(db.String(20)))

    @declared_attr
    def tag(cls):
        return Alert.__table__.c.get('tag',db.Column(db.String(20)))
    
    @declared_attr
    def batch(cls):
        return Alert.__table__.c.get('batch',db.Column(db.String(20)))
   
    @declared_attr
    def container(cls):
        return Alert.__table__.c.get('container',db.Column(db.String(20)))

    __mapper_args__ = {
        'polymorphic_identity': 'proximity_alert'
    }

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.replace(tzinfo=timezone.utc).isoformat(),
            'alert_type': 'proximity',
            'active': self.active,
            'data': {
                'container1': self.container,
                'container2': self.container1,
                'zone1': self.zone,
                'zone2': self.zone1,
            }
        }

    def to_metric(self):
        return {
            'id': self.id,
            'container': self.container,
            'batch': self.batch,
            'zone': self.zone,
            'tag': self.tag,
            'alert_type': 'proximity',
            'distance': round(self.distance),
            'activation_timestamp': self.timestamp.replace(tzinfo=timezone.utc).isoformat(),
            'close_timestamp': self.close_timestamp.replace(tzinfo=timezone.utc).isoformat() if self.close_timestamp else '',
            'user': self.user.username if self.user else ''
        }
         

    def to_mail(self):
        return f'Alerta de proximidad activa!!!\n  Bins: {self.container1.name} y {self.container2.name}\n Distancia:{self.rule.distance} metro(s)'

class CleanupAlert(Alert):
    containerCleanup = db.Column(db.String(20))

    @declared_attr
    def container(cls):
        return Alert.__table__.c.get('container',db.Column(db.String(20)))
    
    @declared_attr
    def tag(cls):
        return Alert.__table__.c.get('tag',db.Column(db.String(20)))
    
    @declared_attr
    def batch(cls):
        return Alert.__table__.c.get('batch',db.Column(db.String(20)))

    @declared_attr
    def zone(cls):
        return Alert.__table__.c.get('zone', db.Column(db.String(20)))

    __mapper_args__ = {
        'polymorphic_identity': 'cleanup_alert'
    }

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.replace(tzinfo=timezone.utc).isoformat(),
            'alert_type': 'cleanup',
            'active': self.active,
            'data': {
                'container': self.container,
                'containerCleanup': self.containerCleanup,
                'zone': self.zone,
            }
        }

    def to_metric(self):
        return {
            'id': self.id,
            'tag': self.tag,
            'batch': self.batch,
            'container': self.container,
            'containerCleanup': self.containerCleanup,
            'zone': self.zone,
            'alert_type': 'cleanup',
            'activation_timestamp': self.timestamp.replace(tzinfo=timezone.utc).isoformat(),
            'close_timestamp': self.close_timestamp.replace(tzinfo=timezone.utc).isoformat() if self.close_timestamp else '',
            'user': self.user.username if self.user else ''
        }

    def to_mail(self):
          return f'Alerta de limpieza activa!!!\n  Bin de limpieza: {self.containerCleanup.name} \n Bin de alerta: {self.container.name}\n Zona:{self.zone}'

class AlertRule(db.Model):
    __tablename__ = 'alertRule'
    id = db.Column(db.Integer, primary_key=True)
    owner_type = db.Column(db.String(20))
    active = db.Column(db.Boolean, default=True)
    users = db.relationship(
        'User',secondary='subscription', back_populates='alert_rules')

    __mapper_args__ = {
        'polymorphic_on': owner_type,
        'polymorphic_identity': 'alert_rule',
    }

class CleanupAlertRule(AlertRule):
    __tablename__ = 'cleanupAlertRule'
    zone_name = db.Column(db.String(40))
    container_id = db.Column(db.Integer, db.ForeignKey('container.id'))
    container = db.relationship('Container', uselist=False)
    
    __mapper_args__ = {
        'polymorphic_identity': 'cleanup_alert_rule'
    }

    def create(container):
        new_rule = CleanupAlertRule(
        container_id=container.id, zone_name=container.tag.zone.name)
        db.session.add(new_rule)

    def remove(container):
        CleanupAlertRule.query.filter_by(container_id=container.id).delete()
    
    def to_dict(self):
        return {
            'id': self.id,
            'zone': self.zone_name,
            'container': self.container.name if self.container else ""
        }


class ZoneAlertRule(AlertRule):
    __tablename__ = 'zoneAlertRule'
    zones = db.Column(db.String)
    time = db.Column(db.Integer)
    
    __mapper_args__ = {
        'polymorphic_identity': 'zone_alert_rule'
    }
    def to_dict(self):
        return {
            'id': self.id,
            'zones': self.zones.split(','),
            'time': self.time
        }


class ProximityAlertRule(AlertRule):
    __tablename__ = 'proximityAlertRule'

    @declared_attr
    def distance(cls):
        return AlertRule.__table__.c.get('distance', db.Column(db.Integer))

    @declared_attr
    def zones(cls):
        return AlertRule.__table__.c.get('zones', db.Column(db.String))

    __mapper_args__ = {
        'polymorphic_identity': 'proximity_alert_rule'
    }

    def to_dict(self):
        return {
            'id': self.id,
            'distance': round(self.distance),
            'zones': self.zones.split(',')
        }

class InactivityAlertRule(AlertRule):
    __tablename__ = 'inactivityAlertRule'
    device_type = db.Column(db.Enum(DeviceType))

    @declared_attr
    def time(cls):
        return AlertRule.__table__.c.get('time', db.Column(db.Integer))


    __mapper_args__ = {
        'polymorphic_identity': 'inactivity_alert_rule'
    }
    

class BatchAlertRule(AlertRule):
    __tablename__ = 'batchAlertRule'
    @declared_attr
    def distance(cls):
        return AlertRule.__table__.c.get('distance', db.Column(db.Integer))

    @declared_attr  
    def time(cls):
        return AlertRule.__table__.c.get('time', db.Column(db.Integer))

    __mapper_args__ = {
        'polymorphic_identity': 'batch_alert_rule'
    }

    def to_dict(self):
        return {
            'id': self.id,
            'distance': self.distance,
            'time': self.time,
        }
    

class ZoneEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    zone = db.Column(db.String(20))
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'))
    batch = db.relationship('Batch', uselist=False)
    container_id = db.Column(db.Integer, db.ForeignKey('container.id'))
    container = db.relationship('Container', uselist=False)
    in_timestamp = db.Column(db.DateTime)
    out_timestamp = db.Column(db.DateTime, nullable=True)
    permanence_time = db.Column(db.Numeric)

    @ staticmethod
    def change_old_zone_entry(container_id, zone, date):
        old_entry = ZoneEntry.query.filter_by(
            container_id=container_id, zone=zone, out_timestamp=None).first()
        if(old_entry):
            old_entry.out_timestamp = date
            old_entry.permanence_time = round(
                (old_entry.out_timestamp - old_entry.in_timestamp).seconds/60, 1)
            db.session.commit()

    @ staticmethod
    def create_new_zone_entry(container_id, zone, date):
        container = Container.query.filter_by(id=container_id).first()
        batch_id = container.batch_id if container else None
        new_entry = ZoneEntry(container_id=container_id,
                              zone=zone, in_timestamp=date, batch_id=batch_id)
        db.session.add(new_entry)
        db.session.commit()

    def to_dict(self):
        return {
            'id': self.id,
            'batch': self.batch.name if self.batch_id else '',
            'container': self.container.name,
            'tag': self.container.tag.address,
            'zone': self.zone,
            'in_time': self.in_timestamp.replace(tzinfo=timezone.utc).isoformat(),
            'out_time': self.out_timestamp.replace(tzinfo=timezone.utc).isoformat() if self.out_timestamp else '',
            'permanence': round(self.permanence_time) if self.permanence_time else ''
        }
    
    def prop_to_order(field):
        prop_order = {
            'batch': 'batch.name',
            'container': 'container.name',
            'zone': 'zone',
            'in_time': 'in_timestamp',
            'out_time': 'out_timestamp',
            'permanence': 'permanence_time'
        }
        if(field not in prop_order):
            return ""
        else:
            return prop_order[field]


class BinBatchAssociation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'))
    batch = db.relationship('Batch', uselist=False)
    container_id = db.Column(db.Integer, db.ForeignKey('container.id'))
    container = db.relationship('Container', uselist=False)
    in_timestamp = db.Column(db.DateTime)
    out_timestamp = db.Column(db.DateTime, nullable=True)
    permanence_time = db.Column(db.Numeric)

    def to_dict(self):
        return {
            'id': self.id,
            'batch': self.batch.name if self.batch_id else '',
            'container': self.container.name,
            'tag': self.container.tag.address,
            'in_time': self.in_timestamp.replace(tzinfo=timezone.utc).isoformat(),
            'out_time': self.out_timestamp.replace(tzinfo=timezone.utc).isoformat() if self.out_timestamp else '',
            'permanence': round(self.permanence_time) if self.permanence_time else ''
        }

    def prop_to_order(field):
        prop_order = {
            'batch': 'batch.name',
            'container': 'container.name',
            'in_time': 'in_timestamp',
            'out_time': 'out_timestamp',
            'permanence': 'permanence_time'
        }
        if(field not in prop_order):
            return ""
        else:
            return prop_order[field]

    @ staticmethod
    def close_association(container_id, batch_id, date):
        association = BinBatchAssociation.query.filter_by(
            container_id=container_id, batch_id=batch_id, out_timestamp=None).first()
        if(association):
            association.out_timestamp = date
            association.permanence_time = round(
                (association.out_timestamp - association.in_timestamp).seconds/60, 1)
            db.session.commit()

    @ staticmethod
    def create_new_association(container_id, batch_id, date):
        association = BinBatchAssociation(
            container_id=container_id, in_timestamp=date, batch_id=batch_id)
        db.session.add(association)
        db.session.commit()




class MapInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    zoom = db.Column(db.Integer, default=0)
    rotation = db.Column(db.Integer, default=0)
    center_x = db.Column(db.Numeric(precision=18, scale=5), default=0)
    center_y = db.Column(db.Numeric(precision=18, scale=5), default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def to_dict(self):
        return {
            'zoom': self.zoom,
            'rotation': self.rotation,
            'center_x': str(self.center_x.quantize(Decimal('.01'))) if type(self.center_x) is Decimal else str(round(self.center_x, 2)),
            'center_y': str(self.center_y.quantize(Decimal('.01'))) if type(self.center_y) is Decimal else str(round(self.center_y, 2)),
        }
    

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True, unique=True)
    username = db.Column(db.String(64), index=True)
    password_hash = db.Column(db.String(128))
    token = db.Column(db.String(32), index=True, unique=True)
    role = db.Column(db.Enum(Role), default=Role.User)
    active = db.Column(db.Boolean, default=False)
    alerts = db.relationship('Alert', backref='user')
    map_info = db.relationship('MapInfo', backref=backref(
        'user'), uselist=False)
    alert_rules = db.relationship(
        'AlertRule', secondary='subscription', back_populates="users")
   

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': str(self.role),
            'active': self.active,
            'subscriptions': self.subscriptions(),
            'map_info': self.map_info.to_dict() if self.map_info else ''
        }
    
    def prop_to_order(field):
        prop_order = {
            'username': 'username',
            'email': 'email',
            'role': 'role',
            'active': 'active',
        }
        if(field not in prop_order):
            return ""
        else:
            return prop_order[field]

    def subscriptions(self):
        return {
            'zone_rules': [a.id for a in self.alert_rules if a.owner_type=='zone_alert_rule' ],
            'batch_rules': [a.id for a in self.alert_rules if a.owner_type=='batch_alert_rule'],
            'proximity_rules': [a.id for a in self.alert_rules if a.owner_type=='proximity_alert_rule'],
            'cleanup_rules': [a.id for a in self.alert_rules if a.owner_type=='cleanup_alert_rule']
        }

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        db.session.commit()

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_token(self, expires_in=36000):
        if not self.token:
            self.token = base64.b64encode(os.urandom(24)).decode('utf-8')
        return self.token

    @ staticmethod
    def check_token(token):
        user = User.query.filter_by(token=token).first()
        if user is None:
            return None
        return user


class Baliza(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id'))
    connector_id = db.Column(db.Integer, db.ForeignKey('connector.id'))
    name = db.Column(db.String(20), unique=True)
    number = db.Column(db.Integer)
    active = db.Column(db.Boolean)
    alerts = db.relationship(
        'Alert',secondary='activation', back_populates="balizas")

    @hybrid_property
    def active(self):
        return len(self.alerts) > 0

    def to_dict(self):
        return {
            'id': self.id,
            'zone': self.zone.name if self.zone else '',
            'name': self.name,
            'active': self.active,
            'connector_active': self.connector.active,
            'ip': self.connector.ip if self.connector else '',
            'status': str(self.connector.status) if self.connector else ''
        }

    @ staticmethod
    def create(connector,count):
        for i in range(count):
            name = connector.mac + '_'+('0'+str(i) if i <10 else str(i) )
            new_b = Baliza(number=i+1,name=name,connector_id=connector.id)
            db.session.add(new_b)
        db.session.commit()
    
    def activate(self,alert):
        if self.connector.active:
            alert.balizas.append(self)
            db.session.commit()
            send_baliza_message(self.number, self.connector.ip,'1')
    
    def check_deactive(self):
        if(not self.active and self.connector.active):
            send_baliza_message(self.number, self.connector.ip,'0')


class Activation(db.Model):
    __tablename__ = 'activation'
    alert_id = db.Column(db.Integer, db.ForeignKey(
        'alert.id'), primary_key=True)
    baliza_id = db.Column(db.Integer, db.ForeignKey('baliza.id'), primary_key=True)

class Subscription(db.Model):
    __tablename__ = 'subscription'
    alert_rule_id = db.Column(db.Integer, db.ForeignKey(
        'alertRule.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)

class Connector(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mac = db.Column(db.String(20), unique=True)
    ip = db.Column(db.String(20))
    balizas = db.relationship('Baliza', backref='connector')
    creation_timestamp = db.Column(db.DateTime)
    last_timestamp = db.Column(db.DateTime)
    fw_version = db.Column(db.String(20)) 
    hw_version = db.Column(db.String(20))
    hw_name = db.Column(db.String(20))
    status = db.Column(db.Enum(Status), default=Status.Online)
    active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'mac': self.mac,
            'ip': self.ip,
            'fw_version': self.fw_version,
            'hw_version': self.hw_version,
            'hw_name': self.hw_name,
            'balizas': [b.name for b in self.balizas],
            'creation_time': self.creation_timestamp.replace(tzinfo=timezone.utc).isoformat(),
            'last_time': self.last_timestamp.replace(tzinfo=timezone.utc).isoformat(),
            'status': str(self.status),
            'active': self.active
        }
    @ staticmethod
    def create(data):
        data = Utils.parse_connector(data)
        if data == "invalid message":
            return
        connector = Connector.query.filter_by(mac=data['mac']).first()
        if (not connector):
            ios = data['ios']
            new_c = Connector(mac=data['mac'],ip=data['ip'], fw_version=data['fw_version'],
            hw_version=data['hw_version'], hw_name=data['hw_name'],creation_timestamp=datetime.utcnow(),last_timestamp=datetime.utcnow())
            db.session.add(new_c)
            db.session.commit()
            Baliza.create(new_c,ios)
            return new_c
        else:
            connector.last_timestamp = datetime.utcnow()
            connector.status = Status.Online
            db.session.commit()
            return connector
