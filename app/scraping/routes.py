from flask import render_template, flash, redirect, url_for, request, current_app
from flask_login import login_required
from app.models import Drug, Listing, Market, Page
from app.scraping import bp
import redis
import re
from app import celery as cel  # imports the object created when app is initialized


def is_redis_available():
    print(current_app.config['BROKER_URL'])
    r = redis.from_url(current_app.config['BROKER_URL'])
    try:
        r.ping()
        return True
    except redis.exceptions.ConnectionError:
        return False


def find_running_scraper(scraper_name):
    """Returns task id as a string if a a task is found with the provided scraper name
    Otherwise, returns None
    Assumes only 1 Redis server is running"""
    insp = cel.control.inspect()
    if insp.stats() is None:
        # this will check if any workers are available.
        # insp.active() will hang if no workers are available
        # so it is important to check this first
        return None

    # if len(insp.active()) > 1:
    #     return "more than 1 redis server detected"

    scaper_func = current_app.scrapers[scraper_name].__name__

    for k, active_tasks in insp.active().items():  # this returns active_tasks as a dict with an item
        # for each redis server. Since there is just one key in the dict, you can return on the first loop
        if len(active_tasks) == 0:
            return None
        for task in active_tasks:
            pattern = r".+[.](.+$)"  # will get task_name out of 'any.text.task_name'
            match = re.match(pattern, task['name'])
            task_name = match.groups()[0]
            if task_name == scaper_func:
                return task['id']
        return None

        # sample response for inspect().active():
        # {'celery@jacob-TM1701': [
        #     {'id': '6b3e88e6-d6f4-4bf9-8831-cb6172027892', 'name': 'app.scraping.tasks.test_task', 'args': '()',
        #      'kwargs': '{}', 'type': 'app.scraping.tasks.test_task', 'hostname': 'celery@jacob-TM1701',
        #      'time_start': 1565626052.126947, 'acknowledged': True,
        #      'delivery_info': {'exchange': '', 'routing_key': 'celery', 'priority': 0, 'redelivered': None},
        #      'worker_pid': 25606}]}


@bp.route('/test_task')
def test_task():
    return render_template('test.html')


@bp.route('/starttask', methods=['POST'])
@login_required
def starttask():

    scraper_name = request.form.get('scraper_name', None)
    try:
        scraper_func = current_app.scrapers[scraper_name]
    except KeyError:
        return "{} was not recognized as a scraper name".format(scraper_name), 500

    if not is_redis_available():
        return "Redis server not found", 500
    if find_running_scraper(scraper_name):
        return "This task is already running", 500
    insp = cel.control.inspect()
    if insp.stats() is None:
        return "No workers are available", 500
    scraper_func.apply_async()
    return "", 204


@bp.route('/raw_results/<page_id>')
def raw_results(page_id):
    page = Page.query.filter_by(id=page_id).first()
    return render_template("raw_results.html", page=page)


@bp.route('/rechem')
def rechem():
    # It might make sense to eventually just have one task page that takes a task_name argument, but I'm not sure
    # How different the templates will be for different tasks. I imagine a crawler for a dark net site might
    # Be significantly different, so I don't think it would run off the same template
    return render_template('rechem.html')


@bp.route('/rechem_results', methods=['GET'])
def rechem_results():
    market = Market.query.filter_by(name="rechem_real").first()  # TODO: replace with "scraper_name"
    page = request.args.get('page', 1, type=int)

    if market:
        pages = market.latest_pages().paginate(page, 50, False)
        next_url = url_for('scraping.rechem', page=pages.next_num) \
            if pages.has_next else None
        prev_url = url_for('scraping.rechem', page=pages.prev_num) \
            if pages.has_prev else None
        pages = pages.items
    else:
        pages = []
        next_url = None
        prev_url = None
    return render_template('_rechem_results.html', pages=pages, prev_url=prev_url, next_url=next_url)