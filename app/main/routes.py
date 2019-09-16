from flask import render_template, flash, redirect, url_for, request, g, current_app, jsonify, send_from_directory
from flask_login import current_user, login_required
from app import db
from app.models import User, Drug, Listing, Market, Page, Country
from app.main import bp
from app.main.forms import EditProfileForm
from datetime import datetime
import sqlite3
import os


@bp.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(current_app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@bp.route('/')
@bp.route('/index')
@bp.route('/data_summary')
def index():
    markets = Market.query.all()
    return render_template('data_summary.html', markets=markets)


@bp.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('user.html', user=user)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)


@bp.route('/drugs')
def drugs():
    drugs = Drug.query.all()
    markets = Market.query.all()
    return render_template('drugs.html', drugs=drugs, markets=markets, title="Drugs")

    
@bp.route('/rename_market', methods=['GET', 'POST'])
@login_required
def rename_market():
    market = Market.query.filter_by(id=request.form['market_id']).first()
    new_name = request.form['new_name']
    if market:
        market.name = new_name
    return '', 204

    
@bp.route('/delete_market', methods=['GET', 'POST'])
@login_required
def delete_market():
    market = Market.query.filter_by(id=request.form['market_id']).first()
    if market:
        db.session.delete(market)
        db.session.commit()
    markets = Market.query.all()
    # TODO: may be better to return ('', 204) for this. We may want to delete through this route in the future on
    # TODO: a different page and not return the table. Create a separate route to get markets and render table
    return render_template('_data_summary_table.html', markets=markets)

    
@bp.route('/create_market', methods=['GET', 'POST'])
@login_required
def create_market():
    name = request.form['name']
    market = Market.query.filter_by(name=name).first()
    if market:
        flash('{} is already a market. Use a different name.'.format(name))
    else:
        market = Market(name=name)
        db.session.add(market)
        db.session.commit()
    markets = Market.query.all()
    # TODO: may be better to return ('', 204) for this. We may want to delete through this route in the future on
    # TODO: a different page and not return the table. Create a separate route to get markets and render table
    return render_template('_data_summary_table.html', markets=markets)


@bp.route('/import_rechem', methods=['GET'])
@login_required
def import_rechem():
    con = sqlite3.connect('app/rechem_listings.db')
    con.row_factory = sqlite3.Row  # returns sqlite3 query result as dict rather than tuple
    c = con.cursor()
    c.execute("SELECT * FROM country")
    countries = c.fetchall()
    new_countries = []
    for row in countries:
        country = Country(name=row['name'], c2=row['c2'])
        if not Country.query.filter_by(name=country.name).first():
            new_countries.append(country)
    db.session.add_all(new_countries)
    db.session.commit()
    c.execute("SELECT * FROM drug")
    drugs = c.fetchall()
    new_drugs = []
    for row in drugs:
        drug = Drug(name=row['name'])
        if not Drug.query.filter_by(name=drug.name).first():
            new_drugs.append(drug)
    db.session.add_all(new_drugs)
    db.session.commit()
    c.execute("SELECT * FROM market")
    markets = c.fetchall()
    new_markets = []
    for row in markets:
        market = Market(name=row['name'])
        if not Market.query.filter_by(name=market.name).first():
            new_markets.append(market)
    db.session.add_all(new_markets)
    db.session.commit()
    c.execute("SELECT * FROM listing")
    listings = c.fetchall()
    rechem_listings = [listing for listing in listings if listing['market_id'] == '4']
    rechem_ids = [d['id'] for d in rechem_listings]
    new_listings = []
    for row in rechem_listings:
        new_market_id = Market.query.filter_by(name="Rechem").first().id

        drug_name = [d for d in drugs if d['id'] == int(row['drug_id'])][0]['name']
        new_drug_id = Drug.query.filter_by(name=drug_name).first().id

        # TODO: this is required for sqlite, but may or may not work with sqlalchemy
        time_format = "%Y-%m-%d %H:%M:%S.%f"
        timestamp = datetime.strptime(row['timestamp'], time_format)

        listing = Listing(url=row['url' ], seller=None, timestamp=timestamp,
                          market_id=new_market_id, drug_id=new_drug_id, origin_id=None)
        if not Listing.query.filter_by(url=listing.url).first():
            new_listings.append(listing)
    db.session.add_all(new_listings)
    db.session.commit()
    c.execute("SELECT * FROM page")
    pages = c.fetchall()
    rechem_pages = [page for page in pages if page['listing_id'] in rechem_ids]
    new_pages = []
    for row in rechem_pages:
        listing_url = [d for d in listings if d['id'] == int(row['listing_id'])][0]['url']
        new_listing_id = Listing.query.filter_by(url=listing_url).first().id

        # TODO: this is required for sqlite, but may or may not work with sqlalchemy
        time_format = "%Y-%m-%d %H:%M:%S.%f"
        timestamp = datetime.strptime(row['timestamp'], time_format)

        page = Page(name=row['name'], html=row['html'], timestamp=timestamp, listing_id=new_listing_id)
        if not Page.query.filter_by(listing_id=page.listing_id, timestamp=page.timestamp).first():
            new_pages.append(page)
        else:
            print("page already found:")
    db.session.add_all(new_pages)
    db.session.commit()

    return "", 204
