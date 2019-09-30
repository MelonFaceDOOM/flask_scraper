from hashlib import md5
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from app import db, login
from sqlalchemy.orm import validates
import datetime
from sqlalchemy.event import listens_for
import re
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import func
from lxml import html


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
            digest, size)

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Country(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    c2 = db.Column(db.String(128), index=True)
    listings = db.relationship('Listing', backref='country', lazy='dynamic')
    __table_args__ = (db.UniqueConstraint('name'),
                      )

    @validates('c2')
    def validate_c2(self, key, c2) -> str:
        if len(c2) != 2:
            raise ValueError('c2 must be two characters')
        return c2


class Drug(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    listings = db.relationship('Listing', backref='drug', lazy='dynamic')
    __table_args__ = (db.UniqueConstraint('name'),
                      )

    def price(self, market_id):
        q = Listing.query.filter_by(drug=self,
                                    market_id=market_id).first()  # TODO: This won't account for multiple listings for
                                                                  # TODO: the same drug
        if q is None:
            return None
        return q.latest_price()


class Market(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    listings = db.relationship('Listing', backref='market', lazy='dynamic')
    __table_args__ = (db.UniqueConstraint('name'),
                      )

    def has_drug(self, drug_id):
        q = Listing.query.filter_by(market=self, drug_id=drug_id).first()
        if q is None:
            return False
        return True

    def pages(self):
        return Page.query.filter(Page.listing_id.in_([listing.id for listing in self.listings]))

    def latest_page_for_each_listing(self):
        """creates a list with the latest page for each listing
        orders this list so the oldest is first
        returns this ordered list"""

        # TODO: this may need to be updated. if a listing does not have any pages associated with it, it won't be
        #  returned here. There shouldn't be any listings that don't have pages, so I don't think it will matter
        #  but we will have to see how things actually end up being used once data collection starts
        latest_page_for_each_listing = [listing.newest_page() for listing in self.listings if listing.newest_page()]

        # sort so oldest is first:
        ordered_pages = sorted(latest_page_for_each_listing, key=lambda x: x.timestamp, reverse=False)
        return ordered_pages

    def latest_pages(self):
        return self.pages().order_by(Page.timestamp.desc())


class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(128))
    market_id = db.Column(db.Integer, db.ForeignKey('market.id'))
    drug_id = db.Column(db.Integer, db.ForeignKey('drug.id'))
    seller = db.Column(db.String(128), index=True)
    origin_id = db.Column(db.Integer, db.ForeignKey('country.id'))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.datetime.utcnow)
    pages = db.relationship('Page', backref='listing', lazy='dynamic')

    # Currently unsure how to define a listing
    # What if a url changes but the listing remains the same?
    # What if origin country changes?
    # What if the name changes?
    # For now I will keep it at url=listing

    def latest_price(self):
        if self.pages.count() > 0:
            return self.pages.order_by(Page.timestamp.desc()).first().price
        else:
            return None

    def newest_page(self):
        return Page.query.filter_by(listing_id=self.id).order_by(Page.timestamp.desc()).first()


class Page(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    price = db.Column(db.Float)
    html = db.Column(db.TEXT(collation='utf8mb4_unicode_ci'))
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id'))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.datetime.utcnow)


@listens_for(Page, 'before_insert')
def rechem_parse(mapper, configuration, target):
    tree = html.fromstring(target.html)
    name = tree.xpath('//h1')
    if name:
        name = name[0].text
    price = tree.xpath('//h2')
    if price:
        price = price[0].text
        if price:
            price = re.sub(r"[^\d\.]", "", price)
            price = float(price)
    else:
        price=None
    target.name = name
    target.price = price

