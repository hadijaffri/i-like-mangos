from http.server import BaseHTTPRequestHandler
import json
import re

# Chat moderation - bad words and patterns
BAD_WORDS = [
    'fuck', 'shit', 'ass', 'bitch', 'damn', 'crap', 'dick', 'cock', 'pussy',
    'bastard', 'slut', 'whore', 'fag', 'nigger', 'retard', 'kys', 'kill yourself',
    'die', 'hate you', 'stupid', 'idiot', 'dumb', 'loser'
]

# Patterns for harassment
BAD_PATTERNS = [
    r'go\s+die', r'kill\s+your', r'you\s+suck', r'ur\s+mom', r'your\s+mom',
    r'u\s+r\s+bad', r'you\s+are\s+bad', r'noob', r'trash'
]

def moderate_message(text):
    """Check if message contains inappropriate content"""
    lower = text.lower()

    # Check bad words
    for word in BAD_WORDS:
        if word in lower:
            return True, '*' * len(text)

    # Check patterns
    for pattern in BAD_PATTERNS:
        if re.search(pattern, lower):
            return True, '*' * len(text)

    return False, text

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())

            message = data.get('message', '')
            player = data.get('player', 'Unknown')

            # Moderate the message
            is_filtered, filtered_text = moderate_message(message)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'filtered': is_filtered,
                'filteredText': filtered_text,
                'player': player
            }).encode())
        except Exception as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
