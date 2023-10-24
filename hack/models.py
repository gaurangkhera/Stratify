from hack import db,login_manager
from flask_login import UserMixin
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
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
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now())
    leader_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    sub_orgs = db.relationship('SubOrganisation')

class SubOrganisation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    parent_organization_id = db.Column(db.Integer, db.ForeignKey('master_organisation.id'))
    created_at = db.Column(db.DateTime, default=datetime.now())
    leader = db.Column(db.Integer, db.ForeignKey('user.id'))
    members = db.relationship('Member', backref='sub_organisation', lazy='dynamic')
    resources = db.relationship('Resource', backref='sub_organisation', lazy='dynamic')

class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    sub_org = db.Column(db.Integer, db.ForeignKey('sub_organisation.id'))

class ResourceAllocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'))
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'))
    allocation_quantity = db.Column(db.Integer, default=0)

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    sub_organization_id = db.Column(db.Integer, db.ForeignKey('sub_organisation.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    resources = db.relationship('ResourceAllocation', backref='member', lazy='dynamic')