from http.server import BaseHTTPRequestHandler
import json
import os

# Stripe configuration
# Set STRIPE_SECRET_KEY in Vercel environment variables
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')

# Coin pack definitions (must match frontend)
COIN_PACKS = {
    'pack_500': {'coins': 500, 'price': 99, 'name': '500 Coins'},
    'pack_1200': {'coins': 1200, 'price': 199, 'name': '1,200 Coins (+200 bonus)'},
    'pack_3500': {'coins': 3500, 'price': 499, 'name': '3,500 Coins (+700 bonus)'},
    'pack_10000': {'coins': 10000, 'price': 999, 'name': '10,000 Coins (+2,500 bonus)'}
}

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            # Check if Stripe is configured
            if not STRIPE_SECRET_KEY:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': 'Stripe not configured. Please set STRIPE_SECRET_KEY environment variable.'
                }).encode())
                return

            # Import stripe here to avoid import errors if not installed
            import stripe
            stripe.api_key = STRIPE_SECRET_KEY

            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())

            pack_id = data.get('packId')

            if pack_id not in COIN_PACKS:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Invalid pack'}).encode())
                return

            pack = COIN_PACKS[pack_id]

            # Get the host for redirect URLs
            host = self.headers.get('Host', 'localhost:3000')
            protocol = 'https' if 'vercel' in host or 'hadijaffri' in host else 'http'
            base_url = f"{protocol}://{host}"

            # Create Stripe Checkout Session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f"ShatterRealms - {pack['name']}",
                            'description': f"Get {pack['coins']} coins for ShatterRealms game",
                            'images': ['https://i.imgur.com/YourGameLogo.png'],  # Replace with actual logo
                        },
                        'unit_amount': pack['price'],  # Price in cents
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f"{base_url}/?payment_success=true&coins={pack['coins']}",
                cancel_url=f"{base_url}/?payment_cancelled=true",
                metadata={
                    'pack_id': pack_id,
                    'coins': str(pack['coins'])
                }
            )

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'url': checkout_session.url,
                'sessionId': checkout_session.id
            }).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
