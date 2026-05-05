"""
Main Flask Application Entry Point
AGT (Autoridade Geral Tributária) Compliance System - Angola
"""

import os
from billing_app.app_factory import create_app

# Create Flask application
app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == '__main__':
    # Run development server
    app.run(
        host=os.getenv('HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('DEBUG', 'True') == 'True'
    )

