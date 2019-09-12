from app import celery
from app.models import Market, Page
from app import db
import requests
from app.scraping.rechem_scraping import rget
from time import sleep
import logging


@celery.task(bind=True)
def rechem_single_page(self):

    # create session object with some generic headers
    # TODO: add randomized headers in. This as well as creating the session itself could probably be
    #  done in rechem_scraping
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;'
                  'q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9',
        'referer': 'https://www.rechem.ca/index.php?route=common/home',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/73.0.3683.103 Safari/537.36'
    }
    session = requests.session()
    session.headers = headers
    rechem = Market.query.filter_by(name="rechem_real").first()
    last_updated_listing = rechem.latest_page_for_each_listing()[0].listing
    url = last_updated_listing.url

    self.update_state(state='PROGRESS',
                      meta={'url': url, 'status': "Attempting to scrape {}".format(url)})

    content = rget(url, session)  # note that automatic retries are part of rget
    if content is None:
        self.update_state(state='FAILURE')
        return {'url': url, 'status': "Unable to reach {}".format(url)}
    else:
        db.session.add(Page(listing_id=last_updated_listing.id, html=content.text))
        db.session.commit()

        self.update_state(state='SUCCESS')
        return {'url': url, 'status': "Successfully scraped {} and entered in db".format(url)}


@celery.task(bind=True)
def test_task(self):

    self.update_state(state='PENDING',
                      meta={'status': "Beginning loop"})
    total = 20
    for i in range(total):
        logging.info("on loop {}".format(i+1))
        status = "Working through task {} of {}".format(i + 1, total)
        db.session.add(Page(listing_id=1, html="test"))
        db.session.commit()
        sleeptime = 4
        for remaining in range(sleeptime, 0, -1):
            self.update_state(state='PROGRESS',
                              meta={'current': i + 1, 'total': total, 'successes': i + 1,
                                    'failures': 0, 'sleeptime': remaining, 'status': status})
            sleep(1)

    self.update_state(state='SUCCESS')
    return {'current': total, 'total': total, 'successes': 5, 'failures': 0,
            'status': 'Completed'}
