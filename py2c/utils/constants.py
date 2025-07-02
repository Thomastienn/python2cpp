PROD = True
TAB = " " * 4
HEADER = \
"""#include <bits/stdc++.h>
using namespace std;"""

# Security Configuration
SECURITY_CONFIG = {
    # Input validation limits
    'MAX_INPUT_SIZE': 30 * 1024,  # 30KB max Python code input
    'MAX_AST_NODES': 1000,        # Maximum AST nodes to prevent resource exhaustion
    'MAX_FILE_SIZE': 50 * 1024,   # 50KB max file upload size
    'MAX_UPLOAD_FILES': 1,        # Maximum number of files in upload
    
    # Rate limiting
    'API_RATE_LIMIT': '30/minute',  # 30 requests per minute
    'RATE_LIMIT_ABUSE_THRESHOLD': 5,  # Strikes before longer ban
    'RATE_LIMIT_BAN_DURATION': 300,   # 5 minutes ban for abuse
    
    # Timeouts
    'CONVERSION_TIMEOUT': 30,     # 30 seconds max for conversion
    'FILE_READ_TIMEOUT': 10,      # 10 seconds max for file reading
    
    # CORS configuration
    'ALLOWED_ORIGINS': ['*'],  # Allow all origins for public API
    
    # Content Security Policy
    'CSP_HEADER': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'",
    
    # File validation
    'ALLOWED_EXTENSIONS': ['.py'],
    'SECURE_FILENAME_PATTERN': r'^[a-zA-Z0-9._-]+$'
}
