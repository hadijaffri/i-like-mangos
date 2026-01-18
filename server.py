#!/usr/bin/env python3
import http.server
import json
import os
import re

PORT = 8000
DATA_FILE = 'playerdata.json'

# Initialize data file if it doesn't exist
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({'coins': 100, 'ownedItems': ['sword', 'fireball']}, f)

# Chat moderation - bad words and patterns
BAD_WORDS = [
    'fuck', 'shit', 'ass', 'bitch', 'damn', 'crap', 'dick', 'cock', 'pussy',
    'bastard', 'slut', 'whore', 'fag', 'nigger', 'retard', 'kys', 'kill yourself',
    'die', 'hate you', 'stupid', 'idiot', 'dumb', 'loser', 'stfu', 'wtf', 'fck',
    'sht', 'btch', 'fuk', 'fuc', 'azz', 'a$$', 'b1tch', 'sh1t', 'f4ck', 'd1ck'
]

# Patterns for harassment - includes spaced out letters and variations
BAD_PATTERNS = [
    r'go\s+die', r'kill\s+your', r'you\s+suck', r'ur\s+mom', r'your\s+mom',
    r'u\s+r\s+bad', r'you\s+are\s+bad', r'noob', r'trash',
    # Spaced out letters patterns
    r'f\s*u\s*c\s*k', r's\s*h\s*i\s*t', r'b\s*i\s*t\s*c\s*h', r'd\s*i\s*c\s*k',
    r'a\s*s\s*s', r'c\s*o\s*c\s*k', r'p\s*u\s*s\s*s\s*y', r'w\s*h\s*o\s*r\s*e',
    r's\s*l\s*u\s*t', r'f\s*a\s*g', r'c\s*u\s*n\s*t', r'd\s*a\s*m\s*n',
    # Leetspeak patterns
    r'f[u4][c\(k]', r'sh[i1!]t', r'b[i1!]t[c\(]h', r'd[i1!][c\(]k',
    r'[a4@]ss', r'[c\(][o0][c\(]k', r'p[u4]ss', r'wh[o0]r[e3]',
    # Special character replacements
    r'f[\*\.\-\_]+u[\*\.\-\_]+c[\*\.\-\_]+k',
    r's[\*\.\-\_]+h[\*\.\-\_]+i[\*\.\-\_]+t',
    # Common evasions
    r'fvck', r'fcuk', r'phuck', r'phuk', r'sh!t', r'a\$\$', r'b!tch',
]

def normalize_text(text):
    """Normalize text by removing spaces and common substitutions"""
    normalized = text.lower()
    # Remove spaces between single letters
    normalized = re.sub(r'(?<=\b\w)\s+(?=\w\b)', '', normalized)
    # Common leetspeak substitutions
    substitutions = {
        '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '7': 't',
        '@': 'a', '$': 's', '!': 'i', '*': '', '.': '', '-': '', '_': ''
    }
    for old, new in substitutions.items():
        normalized = normalized.replace(old, new)
    return normalized

def moderate_message(text):
    """Check if message contains inappropriate content"""
    lower = text.lower()
    normalized = normalize_text(text)

    # Check bad words in both original and normalized text
    for word in BAD_WORDS:
        if word in lower or word in normalized:
            return True, '*' * len(text)

    # Check patterns
    for pattern in BAD_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            return True, '*' * len(text)
        if re.search(pattern, normalized, re.IGNORECASE):
            return True, '*' * len(text)

    # Check for any word that's mostly consonants followed by vowels matching bad words
    # This catches things like "fuuuck" or "shiiiit"
    stretched_patterns = [
        r'f+u+c+k+', r's+h+i+t+', r'b+i+t+c+h+', r'd+i+c+k+', r'a+s+s+',
        r'c+o+c+k+', r'p+u+s+s+y+', r'd+a+m+n+', r'c+r+a+p+'
    ]
    for pattern in stretched_patterns:
        if re.search(pattern, lower):
            return True, '*' * len(text)

    return False, text

class GameHandler(http.server.SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/save' or self.path == '/api/coins':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            with open(DATA_FILE, 'r') as f:
                self.wfile.write(f.read().encode())
        elif self.path == '/':
            self.path = '/shatterrealms_v5.html'
            super().do_GET()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/save' or self.path == '/api/coins':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode())
                save_data = {
                    'coins': data.get('coins', 100),
                    'ownedItems': data.get('ownedItems', ['sword', 'fireball'])
                }
                with open(DATA_FILE, 'w') as f:
                    json.dump(save_data, f)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'success': True, **save_data}).encode())
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())

        elif self.path == '/api/chat':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
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
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    with http.server.HTTPServer(('', PORT), GameHandler) as httpd:
        print(f'Server running at http://localhost:{PORT}/')
        print(f'Game: http://localhost:{PORT}/shatterrealms_v5.html')
        httpd.serve_forever()
