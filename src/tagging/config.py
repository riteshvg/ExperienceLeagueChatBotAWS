"""
Configuration file for the Smart Tagger system
"""

# Enhanced keyword patterns for better classification
ENHANCED_KEYWORDS = {
    "question_types": {
        "implementation": [
            "implement", "setup", "install", "configure", "deploy", "tracking",
            "code", "javascript", "sdk", "api", "integration", "connect", "link",
            "add", "create", "build", "develop", "programming", "coding"
        ],
        "troubleshooting": [
            "error", "issue", "problem", "not working", "broken", "fix", "debug",
            "troubleshoot", "why", "how to fix", "not showing", "missing", "incorrect",
            "failing", "fails", "doesn't work", "won't work", "help", "support"
        ],
        "configuration": [
            "config", "settings", "options", "preferences", "customize", "modify",
            "change", "update", "admin", "permissions", "access", "setup", "configure",
            "custom", "personalize", "adjust", "tune", "optimize"
        ],
        "reporting": [
            "report", "dashboard", "visualization", "chart", "metric", "kpi",
            "analysis", "insights", "data", "export", "schedule", "create report",
            "build report", "generate report", "view data", "analytics"
        ],
        "api": [
            "api", "rest", "endpoint", "request", "response", "authentication",
            "token", "key", "credentials", "webhook", "integration", "programmatic",
            "developer", "sdk", "library", "code"
        ],
        "integration": [
            "integrate", "connect", "sync", "import", "export", "third party",
            "partner", "connector", "bridge", "link", "merge", "combine"
        ],
        "privacy": [
            "privacy", "gdpr", "ccpa", "consent", "opt-out", "data protection",
            "personal data", "pii", "compliance", "regulatory", "legal"
        ],
        "mobile": [
            "mobile", "ios", "android", "app", "sdk", "push notification",
            "deep link", "attribution", "mobile app", "smartphone", "tablet"
        ]
    }
}

# Confidence thresholds
CONFIDENCE_THRESHOLDS = {
    "high": 0.8,
    "medium": 0.6,
    "low": 0.4,
    "bedrock_enhancement": 0.5
}

# Product detection patterns
PRODUCT_PATTERNS = {
    "adobe_analytics": [
        r'\b(?:adobe analytics|aa|analytics)\b',
        r'\b(?:omniture|sitecatalyst)\b',
        r'\b(?:appmeasurement|s_code)\b',
        r'\b(?:visitor api|visitor id)\b',
        r'\b(?:segments?|reports?|dashboards?)\b'
    ],
    "customer_journey_analytics": [
        r'\b(?:customer journey analytics|cja)\b',
        r'\b(?:cross-device|cross device)\b',
        r'\b(?:person id|personid)\b',
        r'\b(?:data view|dataview)\b'
    ],
    "adobe_experience_platform": [
        r'\b(?:adobe experience platform|aep|experience platform)\b',
        r'\b(?:real-time cdp|rtcdp)\b',
        r'\b(?:profile service|identity service)\b',
        r'\b(?:data lake|datalake)\b'
    ],
    "adobe_launch": [
        r'\b(?:adobe launch|launch|dynamic tag manager|dtm)\b',
        r'\b(?:data collection|data collection ui)\b',
        r'\b(?:property|environment|rule)\b'
    ],
    "adobe_tags": [
        r'\b(?:adobe tags|tags)\b',
        r'\b(?:tag management|tagmanager)\b'
    ],
    "data_collection": [
        r'\b(?:data collection|data collection ui)\b',
        r'\b(?:web sdk|websdk|alloy)\b',
        r'\b(?:edge network|edge)\b'
    ],
    "appmeasurement": [
        r'\b(?:appmeasurement|s_code|s_code\.js)\b',
        r'\b(?:analytics\.js|analytics\.min\.js)\b'
    ],
    "aep_web_sdk": [
        r'\b(?:aep web sdk|web sdk|alloy)\b',
        r'\b(?:adobe alloy|alloy\.js)\b'
    ]
}
