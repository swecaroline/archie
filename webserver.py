from http.server import HTTPServer, BaseHTTPRequestHandler

def run_server():
    class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            # Send a 200 OK response status
            self.send_response(200)
            
            # Set the content type header to HTML
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            # The HTML payload containing your simple heading
            html_content = """
            <!DOCTYPE html>
            <html>
            <head><title>Archie Status</title></head>
            <body>
                <h1>Archie is OK</h1>
            </body>
            </html>
            """
            
            # Write the response back to the browser (encoded as bytes)
            self.wfile.write(bytes(html_content, "utf-8"))

    # Define server address and port
    server_address = ('', 8080)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")