from hack import app, create_db, db
from flask import render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from hack.forms import LoginForm, RegForm, CreateOrgForm, AddMemberForm, EditQuantityForm
import stripe
from hack.models import User, MasterOrganisation, SubOrganisation, Resource, ResourceAllocation, Member
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_
import json

stripe.api_key = 'sk_test_51O4bOCSDZFni4Xk6I8la6qDeGwmeqWSY6CAiN7XEm8qdW8mvSsvT8CKL0HvX1JEL1UTMfeCE13iUCbGEWGnAaJCa00dj1B1Y1S'

create_db(app)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/reg', methods=['GET', 'POST'])
def reg():
    form = RegForm()
    mess = ''
    if form.validate_on_submit():
        email = form.email.data
        username = form.username.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()
        if user:
            mess = 'Account already exists'
        else:
            new_user = User(email=email, username=username, password=generate_password_hash(password))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect('/')
    return render_template('reg.html', form=form, mess=mess)

@app.route('/dashboard')
@login_required
def dashboard():
    sess_id = request.args.get('success')
    if sess_id:
        try:
                current_user.subPlan = 'Pro'
                db.session.add(current_user)
                db.session.commit()
                flash('Payment successful. You are now on the Pro plan.', 'success')
        except stripe.error.StripeError as e:
            flash(f'Payment unsuccessful - {e}', 'error')
    orgs_leader = MasterOrganisation.query.filter_by(leader_id=current_user.id).all()
    orgs_member = MasterOrganisation.query.join(SubOrganisation).join(Member).filter(Member.user_id == current_user.id).all()
    orgs = orgs_leader + orgs_member

    return render_template('dashboard.html', orgs=orgs)

@app.route('/dashboard/create-org', methods=['GET', 'POST'])
@login_required
def create_org():
    form = CreateOrgForm()
    if form.validate_on_submit():
        if current_user.subPlan == 'Free' and MasterOrganisation.query.filter_by(leader_id=current_user.id).count() >= 2:
            flash('Free users are limited to creating up to 2 master organizations.', 'error')
            return redirect(url_for('pricing'))
        new_master_organisation = MasterOrganisation(name=form.name.data, leader_id=current_user.id)
        db.session.add(new_master_organisation)
        db.session.commit()
        flash('Organization created successfully.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('create_org.html', form=form)

@app.route('/dashboard/org/<id>')
@login_required
def org_page(id):
    org = MasterOrganisation.query.filter_by(id=id).first()
    return render_template('org_page.html', org=org, orgs=org.sub_orgs)

@app.route('/dashboard/org/<id>/sub-org/<so_id>', methods=['GET', 'POST'])
@login_required
def sub_org_page(id, so_id):
    org = MasterOrganisation.query.filter_by(id=id).first()
    sub_org = SubOrganisation.query.filter_by(id=so_id).first()
    return render_template('sub_org_page.html', org=org, sub_org=sub_org, members=sub_org.members)

@app.route('/dashboard/org/<id>/create-sub-org', methods=['GET', 'POST'])
@login_required
def create_sub_org(id):
    org = MasterOrganisation.query.filter_by(id=id).first()
    form = CreateOrgForm()
    if form.validate_on_submit():
        if current_user.subPlan == 'Free' and SubOrganisation.query.filter_by(leader=current_user.id).count() >= 10:
            flash('Free users are limited to creating up to 10 sub-organizations in a master organization.', 'error')
            return redirect(url_for('pricing'))

        new_sub_organisation = SubOrganisation(name=form.name.data, parent_organization_id=id, leader=current_user.id)
        db.session.add(new_sub_organisation)
        db.session.commit()
        new_member = Member(name=current_user.username, email=current_user.email, sub_organization_id=new_sub_organisation.id, user_id=current_user.id)
        db.session.add(new_member)
        db.session.commit()
        flash('Sub-organisation created successfully.', 'success')
        return redirect(url_for('org_page', id=id))

    return render_template('create_sub_org.html', form=form, org=org)

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/dashboard/delete-org/<id>')
@login_required
def delete_org(id):
    org = MasterOrganisation.query.filter_by(id=id).first()
    for sub_org in org.sub_orgs:
        members = Member.query.filter_by(sub_organization_id=sub_org.id).all()
        for member in members:
            db.session.delete(member)
        resources = Resource.query.filter_by(sub_org=sub_org.id).all()
        for resource in resources:
            db.session.delete(resource)
        resource_allocations = ResourceAllocation.query.filter_by(sub_org_id=sub_org.id).all()
        for allocation in resource_allocations:
            db.session.delete(allocation)
        db.session.delete(sub_org)
    db.session.delete(org)
    db.session.commit()

    flash('Organization deleted successfully.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/dashboard/delete-sub-org/<id>')
@login_required
def delete_sub_org(id):
    org = SubOrganisation.query.filter_by(id=id).first()
    members = Member.query.filter_by(sub_organization_id=org.id).all()
    for i in members:
        db.session.delete(i)
        db.session.commit()
    db.session.delete(org)
    db.session.commit()
    flash('Sub-organization deleted successfully.', 'success')
    return redirect('/dashboard/org/' + str(org.parent_organization_id))

@app.route('/dashboard/org/<id>/sub-org/<so_id>/add-member', methods=['GET', 'POST'])
@login_required
def add_member(id, so_id):
    form = AddMemberForm()
    org = MasterOrganisation.query.filter_by(id=id).first()
    sub_org = SubOrganisation.query.filter_by(id=so_id).first()
    if current_user.subPlan == 'Free' and Member.query.filter_by(sub_organization_id=so_id).count() >= 25:
        flash('Free users are limited to a maximum of 25 members per sub-organization.', 'error')
        return redirect(url_for('pricing'))
    
    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('Email not found.', 'error')
        elif user.email == current_user.email:
            flash("You can't add yourself.", 'error')
        elif Member.query.filter_by(user_id=user.id, sub_organization_id=so_id).first():
            flash('This user is already a member.', 'error')
        else:
            new_member = Member(name=user.username, email=user.email, sub_organization_id=sub_org.id, user_id=user.id)
            db.session.add(new_member)
            db.session.commit()
            flash('Member added successfully.', 'success')
            return redirect(url_for('sub_org_page', id=id, so_id=so_id))
    
    return render_template('add_member.html', form=form, org=org, sub_org=sub_org)

@app.route('/dashboard/org/<id>/sub-org/<so_id>/add-resources', methods=['GET', 'POST'])
@login_required
def add_resources(id, so_id):
    if request.method == 'POST':
        resource_names = request.form.getlist('resource-name[]')
        resource_quantities = request.form.getlist('resource-quantity[]')
        for name, quantity in zip(resource_names, resource_quantities):
            if name and quantity:
                resource = Resource(name=name, quantity=int(quantity), sub_org=so_id)
                db.session.add(resource)
                db.session.commit()
        flash('Resources added successfully.', 'success')

        return redirect(f'/dashboard/org/{id}/sub-org/{so_id}')

    return render_template('add_resource.html', id=id, so_id=so_id)

@app.route('/dashboard/org/<id>/sub-org/<so_id>/delete-member/<m_id>', methods=['GET', 'POST'])
def delete_member(id, so_id, m_id):
    member = Member.query.filter_by(id=m_id).first()
    if member.user_id != current_user.id:
        db.session.delete(member)
        db.session.commit()
        flash('Member deleted successfully.', 'success')
    else:
        flash('You cannot delete yourself.', 'error')
    return redirect(url_for('sub_org_page', id=id, so_id=so_id))

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/dashboard/org/<id>/sub-org/<so_id>/member/<m_id>')
def member_page(id, so_id, m_id):
    org = MasterOrganisation.query.filter_by(id=id).first()
    sub_org = SubOrganisation.query.filter_by(id=so_id).first()
    member = Member.query.filter_by(id=m_id).first()
    alloc_resources = [x for x in member.resources]
    ser_res = [Resource.query.filter_by(id=x.id).first() for x in alloc_resources]
    resources_json = json.dumps([{
    "resource_id": resource.id,
    "resource_name": resource.name,
    "resource_quantity": resource.quantity
} for resource in sub_org.resources.all()])
    return render_template('member.html', org=org, sub_org=sub_org, member=member, resources=resources_json,member_resources=ser_res)

@app.route('/dashboard/org/<id>/sub-org/<so_id>/member/<m_id>/edit-resource/<r_id>', methods=['GET', 'POST'])
@login_required
def edit_res(id, so_id, r_id, m_id):
    org = MasterOrganisation.query.filter_by(id=id).first()
    sub_org = SubOrganisation.query.filter_by(id=so_id).first()
    alloc = ResourceAllocation.query.filter_by(id=r_id).first()
    resource = Resource.query.filter_by(id=alloc.resource_id).first()
    form = EditQuantityForm()
    if form.validate_on_submit():
        new_qty = form.qty.data
        diff = new_qty - alloc.allocation_quantity
        
        if diff > 0:
            resource.quantity -= diff
        elif diff < 0:
            resource.quantity -= diff

        alloc.allocation_quantity = new_qty
        db.session.add(resource)
        db.session.add(alloc)
        db.session.commit()
        flash('Resource quantity updated successfully.', 'success')
        return redirect(url_for('member_page', id=id, so_id=so_id, m_id=m_id))

    return render_template('edit_res.html',org=org, sub_org=sub_org,member=Member.query.filter_by(id=m_id).first(), form=form, alloc=alloc, id=id, so_id=so_id, m_id=m_id)

@app.route('/dashboard/org/<id>/sub-org/<so_id>/member/<m_id>/allocate-resources', methods=['POST'])
def allocate_resources(id, so_id, m_id):
    sub_org = SubOrganisation.query.filter_by(id=so_id).first()
    try:
        data = request.get_json()
        print(data)
        for resource in data:
            resource_name = resource['resource_name']
            resource_id = resource['resource_id']
            resource_quantity = resource['quantity']
            resource = Resource.query.filter_by(id=resource_id).first()
            new_resource_allocation = ResourceAllocation(resource_id=resource.id, member_id=m_id, allocation_quantity=resource_quantity, resource_name=resource_name, sub_org_id=sub_org.id)
            resource.quantity -= int(resource_quantity)
            db.session.add(new_resource_allocation)
            db.session.commit()
            db.session.add(resource)
            db.session.commit()
        response = {'message': 'Resources allocated successfully'}
        return jsonify(response)
    except Exception as e:
        error_message = str(e)
        response = {'error': error_message}
        return jsonify(response), 400
    
@app.route('/dashboard/org/<id>/sub-org/<so_id>/member/<m_id>/deallocate-resource/<r_id>', methods=['GET','POST'])
def dealloc(id, so_id, m_id, r_id):
    org = MasterOrganisation.query.filter_by(id=id).first()
    sub_org = SubOrganisation.query.filter_by(id=id).first()
    member = Member.query.filter_by(id=m_id).first()
    resource_alloc = ResourceAllocation.query.filter_by(id=r_id).first()
    resource = Resource.query.filter_by(id=resource_alloc.resource_id).first()
    resource.quantity += resource_alloc.allocation_quantity
    db.session.add(resource)
    db.session.delete(resource_alloc)
    db.session.commit()
    return redirect(f'/dashboard/org/{org.id}/sub-org/{so_id}/member/{member.id}')

@app.route('/dashboard/org/<id>/sub-org/<so_id>/delete-resource/<r_id>', methods=['GET', 'POST'])
def delete_resource(id, so_id, r_id):
    member = Resource.query.filter_by(id=r_id).first()
    db.session.delete(member)
    db.session.commit()
    return redirect(url_for('sub_org_page', id=id, so_id=so_id))

@app.route('/billing', methods=['GET', 'POST'])
@login_required
def billing():
    if request.args.get('cancelled'):
        flash('Payment cancelled.', 'error')
    if request.method == 'POST':
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price': 'price_1O4bQhSDZFni4Xk6rNyI3Xlt',
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=url_for('dashboard', success=True),
            cancel_url=url_for('dashboard', success=False),
        )
        return redirect(session.url, code=303)

    return render_template('pro_plan_checkout.html', user=current_user)

@app.route('/dashboard/org/<id>/sub-org/<so_id>/member/<m_id>/promote-to-sub-org-leader', methods=['GET', 'POST'])
def promote_suborg(id, so_id, m_id):
    org = MasterOrganisation.query.filter_by(id=id).first()
    sub_org = SubOrganisation.query.filter_by(id=so_id).first()
    member = Member.query.filter_by(id=m_id).first()
    if current_user.id != org.leader_id or current_user.id != sub_org.leader:
        flash('You do not have permission to do that.', 'error')
        return redirect(url_for('sub_org_page', id=id, so_id=so_id))
    if current_user.id == member.user_id:
        flash("You can't promote yourself.", 'error')
        return redirect(url_for('member_page', id=id, so_id=so_id, m_id=m_id))
    sub_org.leader = member.user_id
    db.session.add(sub_org)
    db.session.add(member)
    db.session.add(current_user)
    db.session.commit()
    return redirect(url_for('member_page', id=id, so_id=so_id, m_id=m_id))

@app.route('/dashboard/org/<id>/sub-org/<so_id>/member/<m_id>/promote-to-org-leader', methods=['GET', 'POST'])
def promote_org(id, so_id, m_id):
    org = MasterOrganisation.query.filter_by(id=id).first()
    sub_org = SubOrganisation.query.filter_by(id=so_id).first()
    member = Member.query.filter_by(id=m_id).first()
    if current_user.id != org.leader_id:
        flash('You do not have permission to do that.', 'error')
        return redirect(url_for('sub_org_page', id=id, so_id=so_id))
    if current_user.id == member.user_id:
        flash("You can't promote yourself.", 'error')
        return redirect(url_for('member_page', id=id, so_id=so_id, m_id=m_id))
    org.leader_id = member.user_id
    db.session.add(org)
    db.session.add(member)
    db.session.add(current_user)
    db.session.commit()
    return redirect(url_for('member_page', id=id, so_id=so_id, m_id=m_id))

@app.route('/cancel', methods=['GET', 'POST'])
@login_required
def cancel_subscription():
    if request.method == 'POST':
        current_user.subPlan = 'Free'
        db.session.add(current_user)
        db.session.commit()
        flash('Subscription cancelled successfully.', 'success')
    return redirect(url_for('billing'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    mess=''
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('Email not found.', 'error')
        else:
            if check_password_hash(user.password, password):
                login_user(user, remember=True)
                return redirect(url_for('home'))
            else:
                flash('Incorrect password.', 'error')
    return render_template('login.html', mess=mess, form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, port=6969)
