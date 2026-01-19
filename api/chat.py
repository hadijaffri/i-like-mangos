from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
import urllib.error

# Get Anthropic API key from environment
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

def moderate_with_claude(text):
    """Use Claude to intelligently moderate chat messages"""
    if not ANTHROPIC_API_KEY:
        # Fallback to allowing message if no API key
        return False, text

    try:
        # Prepare the request to Claude API
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01"
        }

        prompt = f"""You are a chat moderator for a children's video game. Analyze this message and determine if it should be filtered.

Filter if the message contains:
- Profanity or swear words (including misspellings, leetspeak like "f4ck", spaced letters like "f u c k")
- Hate speech, slurs, or discriminatory language
- Harassment, bullying, or toxic behavior
- Sexual content or innuendo
- Threats or violence encouragement
- Personal attacks

Message to analyze: "{text}"

Respond with ONLY a JSON object in this exact format:
{{"filter": true/false, "reason": "brief reason if filtered"}}"""

        data = json.dumps({
            "model": "claude-3-haiku-20240307",
            "max_tokens": 100,
            "messages": [{"role": "user", "content": prompt}]
        }).encode('utf-8')

        req = urllib.request.Request(url, data=data, headers=headers, method='POST')

        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))
            content = result.get('content', [{}])[0].get('text', '{}')

            # Parse Claude's response
            try:
                decision = json.loads(content)
                if decision.get('filter', False):
                    return True, '*' * len(text)
            except json.JSONDecodeError:
                # If we can't parse, check for "true" in response
                if '"filter": true' in content.lower() or '"filter":true' in content.lower():
                    return True, '*' * len(text)

        return False, text

    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        # On API error, allow message through (fail open for better UX)
        print(f"Claude API error: {e}")
        return False, text
    except Exception as e:
        print(f"Moderation error: {e}")
        return False, text

def moderate_message(text):
    """Main moderation function using Claude AI"""
    return moderate_with_claude(text)

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
