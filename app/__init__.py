from flask import Flask, render_template, request
from app.services import db_service

def create_app():
    app = Flask(__name__)
    
    # Initialize DB (ensure tables exist)
    with app.app_context():
        db_service.init_db()
    
    # Register Blueprints
    from app.api import novel_routes, chapter_routes, setting_routes, visualization_routes, search_routes
    app.register_blueprint(novel_routes.bp)
    app.register_blueprint(chapter_routes.bp)
    app.register_blueprint(setting_routes.bp)
    app.register_blueprint(visualization_routes.bp)
    app.register_blueprint(search_routes.bp)
    
    # Frontend Routes (Simple)
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/novel/<int:novel_id>')
    def novel_detail(novel_id):
        return render_template('novel.html', novel_id=novel_id)

    @app.route('/search')
    def search_page():
        novel_id = request.args.get('novel_id')
        return render_template('search.html', novel_id=novel_id)
    
    @app.route('/comparison')
    def comparison_page():
        return render_template('comparison.html')

    return app
