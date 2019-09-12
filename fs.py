from app import create_app, db, celery
from app.models import User, Country, Drug, Listing, Market, Page

app = create_app()
app.app_context().push()  # I believe this was necessary for celery to access app context (i.e. access models)?

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db, 'User': User, 'Country': Country, 'Drug': Drug, 'Listing': Listing, 'Market': Market, 'Page': Page
    }
