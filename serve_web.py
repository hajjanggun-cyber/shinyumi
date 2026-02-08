import http.server
import socketserver
import os
import webbrowser

PORT = 8000
DIRECTORY = "web"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

if __name__ == "__main__":
    # Ensure web directory exists
    if not os.path.exists(DIRECTORY):
        print(f"Error: '{DIRECTORY}' directory not found. Please run 'run_all.py' first.")
        exit(1)

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        print("Opening browser...")
        webbrowser.open(f"http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
