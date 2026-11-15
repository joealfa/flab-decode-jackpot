"""Domain blueprint registration."""

from app.routes.accuracy import blueprint as accuracy_blueprint
from app.routes.analysis import blueprint as analysis_blueprint
from app.routes.management import blueprint as management_blueprint
from app.routes.pages import blueprint as pages_blueprint
from app.routes.scraping import blueprint as scraping_blueprint

blueprints = (
    pages_blueprint,
    analysis_blueprint,
    scraping_blueprint,
    accuracy_blueprint,
    management_blueprint,
)
