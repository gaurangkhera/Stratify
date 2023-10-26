from hack import db,login_manager
from flask_login import UserMixin
from datetime import datetime
from uuid import uuid4

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

def get_uuid():
    return uuid4().hex

class User(db.Model, UserMixin):
    id = db.Column(db.String(32), primary_key=True, unique=True, default=get_uuid)
    username = db.Column(db.String(), nullable=False)
    email = db.Column(db.String(64), index=True, unique=True)
    password = db.Column(db.Text())
    created_at = db.Column(db.DateTime, default=datetime.now())
    organisations = db.relationship('MasterOrganisation', backref='leader', lazy='dynamic')
    subOrgs = db.relationship('SubOrganisation', backref='subLeader', lazy='dynamic')
    subPlan = db.Column(db.String, default='Free')
    stripe_customer_id = db.Column(db.String(255), unique=True)
    stripe_subscription_id = db.Column(db.String(255), unique=True)


class MasterOrganisation(db.Model):
    id = db.Column(db.String(32), primary_key=True, unique=True, default=get_uuid)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now())
    leader_id = db.Column(db.String, db.ForeignKey('user.id'))
    sub_orgs = db.relationship('SubOrganisation')

class SubOrganisation(db.Model):
    id = db.Column(db.String(32), primary_key=True, unique=True, default=get_uuid)
    name = db.Column(db.String(100), nullable=False)
    parent_organization_id = db.Column(db.String, db.ForeignKey('master_organisation.id'))
    created_at = db.Column(db.DateTime, default=datetime.now())
    leader = db.Column(db.String, db.ForeignKey('user.id'))
    members = db.relationship('Member', backref='sub_organisation', lazy='dynamic')
    resources = db.relationship('Resource', backref='sub_organisation', lazy='dynamic')

class Resource(db.Model):
    id = db.Column(db.String(32), primary_key=True, unique=True, default=get_uuid)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    sub_org = db.Column(db.String, db.ForeignKey('sub_organisation.id'))

    def serialize(self):
        return {
            'resource_id': self.id,
            'resource_name': self.name,
            'resource_quantity': self.quantity
        }

class ResourceAllocation(db.Model):
    id = db.Column(db.String(32), primary_key=True, unique=True, default=get_uuid)
    resource_id = db.Column(db.String, db.ForeignKey('resource.id'))
    member_id = db.Column(db.String, db.ForeignKey('member.id'))
    resource_name = db.Column(db.String)
    sub_org_id = db.Column(db.Integer)
    allocation_quantity = db.Column(db.Integer, default=0)

    def serialize(self):
        return {
            'alloc_id': self.id,
            'resource_id': self.resource_id,
            'alloc_quantity': self.allocation_quantity,
            'alloc_member_id': self.member_id
        }

class Member(db.Model):
    id = db.Column(db.String(32), primary_key=True, unique=True, default=get_uuid)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    sub_organization_id = db.Column(db.String, db.ForeignKey('sub_organisation.id'))
    user_id = db.Column(db.String, db.ForeignKey('user.id'))
    resources = db.relationship('ResourceAllocation', backref='member', lazy='dynamic')