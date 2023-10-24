from hack import app, create_db, db
from flask import render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from hack.forms import LoginForm, RegForm, CreateOrgForm, AddMemberForm
import stripe
from hack.models import User, MasterOrganisation, SubOrganisation, Resource, ResourceAllocation, Member
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_

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
    print(sess_id)
    if sess_id:
        try:
                current_user.subPlan = 'Pro'
                db.session.add(current_user)
                db.session.commit()
                print(current_user.subPlan)
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
    
    # Impose limits for free users
    if current_user.subPlan == 'Free':
        max_master_orgs = 2
        if MasterOrganisation.query.filter_by(leader_id=current_user.id).count() >= max_master_orgs:
            flash('Free users are limited to creating up to 2 master organizations.', 'error')
    if form.validate_on_submit():
        new_master_organisation = MasterOrganisation(name=form.name.data, leader_id=current_user.id)
        db.session.add(new_master_organisation)
        db.session.commit()
        flash('Organization created successfully.', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('create_org.html', form=form)

@app.route('/dashboard/org/<int:id>')
@login_required
def org_page(id):
    org = MasterOrganisation.query.filter_by(id=id).first()
    return render_template('org_page.html', org=org, orgs=org.sub_orgs)

@app.route('/dashboard/org/<int:id>/sub-org/<int:so_id>', methods=['GET', 'POST'])
@login_required
def sub_org_page(id, so_id):
    org = MasterOrganisation.query.filter_by(id=id).first()
    sub_org = SubOrganisation.query.filter_by(id=so_id).first()
    return render_template('sub_org_page.html', org=org, sub_org=sub_org, members=sub_org.members)

@app.route('/dashboard/org/<int:id>/create-sub-org', methods=['GET', 'POST'])
@login_required
def create_sub_org(id):
    org = MasterOrganisation.query.filter_by(id=id).first()
    form = CreateOrgForm()
    if current_user.subPlan == 'Free':
        max_sub_orgs = 10
        if SubOrganisation.query.filter_by(leader_id=current_user.id).count() >= max_sub_orgs:
            flash('Free users are limited to creating up to 10 sub-organizations in a master organization.', 'error')
    if form.validate_on_submit():
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

@app.route('/dashboard/delete-org/<int:id>')
@login_required
def delete_org(id):
    org = MasterOrganisation.query.filter_by(id=id).first()
    for sub_org in org.sub_orgs:
        db.session.delete(sub_org)
    db.session.delete(org)
    db.session.commit()
    flash('Organization deleted successfully.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/dashboard/delete-sub-org/<int:id>')
@login_required
def delete_sub_org(id):
    org = SubOrganisation.query.filter_by(id=id).first()
    db.session.delete(org)
    db.session.commit()
    flash('Sub-organization deleted successfully.', 'success')
    return redirect('/dashboard/org/' + str(org.parent_organization_id))

@app.route('/dashboard/org/<int:id>/sub-org/<int:so_id>/add-member', methods=['GET', 'POST'])
@login_required
def add_member(id, so_id):
    form = AddMemberForm()
    org = MasterOrganisation.query.filter_by(id=id).first()
    sub_org = SubOrganisation.query.filter_by(id=so_id).first()
    if current_user.subPlan == 'Free':
        max_members_per_sub_org = 25
        if Member.query.filter_by(sub_organization_id=so_id).count() >= max_members_per_sub_org:
            flash('Free users are limited to a maximum of 25 members per sub-organization.', 'error')
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

@app.route('/dashboard/org/<int:id>/sub-org/<int:so_id>/add-resources', methods=['GET', 'POST'])
@login_required
def add_resources(id, so_id):
    if request.method == 'POST':
        resource_names = request.form.getlist('resource-name[]')
        resource_quantities = request.form.getlist('resource-quantity[]')

        # Process the submitted data and add resources to the database
        for name, quantity in zip(resource_names, resource_quantities):
            if name and quantity:
                resource = Resource(name=name, quantity=int(quantity), sub_org=so_id)
                db.session.add(resource)
                db.session.commit()
        flash('Resources added successfully.', 'success')

        return redirect(f'/dashboard/org/{id}/sub-org/{so_id}')

    return render_template('add_resource.html', id=id, so_id=so_id)

@app.route('/billing', methods=['GET', 'POST'])
@login_required
def billing():
    if request.args.get('cancelled'):
        flash('Payment cancelled.', 'error')
    if request.method == 'POST':
        # Create a Stripe Checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price': 'price_1O4bQhSDZFni4Xk6rNyI3Xlt',  # Replace with your price ID
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url='http://localhost:6969/dashboard?success=True',
            cancel_url='http://localhost:6969/billing?cancelled=True',
        )
        return redirect(session.url, code=303)

    return render_template('pro_plan_checkout.html', user=current_user)

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
