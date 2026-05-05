"""
Flask Application Factory
Initializes and configures the Flask app with AGT API
"""

from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime
import logging
import os

from billing_app.db_config import db, init_db
from billing_app.agt_api import agt_api
from billing_app.agt_dashboard import agt_dashboard

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app(config_name: str = 'development') -> Flask:
    """
    Application factory for Flask app
    
    Args:
        config_name: 'development', 'testing', or 'production'
    
    Returns:
        Flask application instance
    """
    
    # Get the billing_app directory path
    basedir = os.path.dirname(os.path.abspath(__file__))
    
    app = Flask(__name__, 
                template_folder=os.path.join(basedir, 'templates'),
                static_folder=os.path.join(basedir, 'static'))
    
    # Configuration
    if config_name == 'development':
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
            'DATABASE_URL',
            'sqlite:///billing_app.db'
        )
        app.config['SQLALCHEMY_ECHO'] = True
        app.config['DEBUG'] = True
    
    elif config_name == 'testing':
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_ECHO'] = False
    
    elif config_name == 'production':
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
        app.config['SQLALCHEMY_ECHO'] = False
        app.config['DEBUG'] = False
    
    # Database
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    # CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": os.getenv('CORS_ORIGINS', '*'),
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Initialize database tables
    with app.app_context():
        init_db()
        logger.info("Database initialized")
    
    # Register blueprints
    app.register_blueprint(agt_api)
    app.register_blueprint(agt_dashboard)
    
    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            "error": "Bad Request",
            "message": str(error),
            "timestamp": datetime.utcnow().isoformat()
        }), 400
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "error": "Not Found",
            "message": str(error),
            "timestamp": datetime.utcnow().isoformat()
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            "error": "Internal Server Error",
            "message": str(error),
            "timestamp": datetime.utcnow().isoformat()
        }), 500
    
    # Root endpoint
    @app.route('/')
    def index():
        return {
            "service": "AGT Conformidade Fiscal - Angola",
            "version": "1.0",
            "status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "api_docs": "/api/docs",
            "health": "/api/health"
        }, 200
    
    logger.info(f"Flask app created (mode: {config_name})")
    
    return app


if __name__ == '__main__':
    app = create_app('development')
    app.run(host='0.0.0.0', port=5000, debug=True)
