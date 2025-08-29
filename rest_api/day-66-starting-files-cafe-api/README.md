Cafe API (Flask)

A simple REST API to manage and discover cafés. Built with Flask and SQLAlchemy using a SQLite database (cafes.db).

Quick Start
- Prerequisites: Python 3.10+ recommended
- Install dependencies (from this project directory):
  - Windows: python -m pip install -r requirements.txt
  - macOS/Linux: pip3 install -r requirements.txt
- Run the server: python main.py
- Default URL: http://127.0.0.1:5000

Authentication
- Mutating endpoints (POST/PATCH/DELETE) require an API key.
- Default API key: TopSecretAPIKey
- How to send the key (any of):
  - HTTP Header: X-API-KEY: TopSecretAPIKey
  - Query parameter: ?api-key=TopSecretAPIKey
  - JSON body: {"api-key": "TopSecretAPIKey"}
  - Form field: api-key=TopSecretAPIKey
- You can change the default key by editing app.config['API_KEY'] in main.py.

Database
- SQLite database file: cafes.db (auto-created on first run)
- Cafe fields:
  - id (int, primary key)
  - name (str, unique, required)
  - map_url (str, required)
  - img_url (str, required)
  - location (str, required)
  - seats (str, required)
  - has_toilet (bool, required)
  - has_wifi (bool, required)
  - has_sockets (bool, required)
  - can_take_calls (bool, required)
  - coffee_price (str, optional)

Endpoints
1) Home
- GET /
- Returns the index page (HTML).

2) Get a random cafe
- GET /random
- Response 200: { "cafe": { ...cafe fields... } }
- Response 404: { "error": { "Not Found": "No cafes found" } }

3) Get all cafes
- GET /all
- Response 200: { "cafes": [ { ... }, { ... } ] }

4) Search cafes by location
- GET /search?loc=<location>
- Query params:
  - loc (required): exact location match (e.g., Shoreditch)
- Response 200: { "cafes": [ ... ] } (empty list if none)
- Response 400 (missing loc): { "error": { "Bad Request": "Please provide 'loc' query parameter, e.g., /search?loc=Shoreditch" } }

5) Add a cafe (requires API key)
- POST /add
- Accepts: application/json or application/x-www-form-urlencoded
- Required fields:
  - name, map_url, img_url, location, seats,
    has_toilet, has_wifi, has_sockets, can_take_calls
- Optional field: coffee_price
- Boolean parsing: accepts true/false, 1/0, yes/no, y/n, on/off (case-insensitive)
- Success 201: { "success": { "message": "Successfully added new cafe.", "cafe": { ... } } }
- Error 400: { "error": { "Bad Request": "Missing or invalid fields", "missing": [...], "invalid_bools": [...] } }
- Error 403: { "error": { "Forbidden": "Invalid or missing API key." } }

Example JSON body:
{
  "name": "Cafe Roma",
  "map_url": "https://maps.example/cafe-roma",
  "img_url": "https://images.example/cafe-roma.jpg",
  "location": "Shoreditch",
  "seats": "20",
  "has_toilet": true,
  "has_wifi": true,
  "has_sockets": false,
  "can_take_calls": true,
  "coffee_price": "£2.80",
  "api-key": "TopSecretAPIKey"
}

6) Update coffee price by id (requires API key)
- PATCH /update-price/<cafe_id>
- Provide new_price via any of: query (?new_price=£2.99), JSON, or form field
- Success 200: { "success": { "message": "Successfully updated the coffee price.", "cafe": { ... } } }
- Error 400 (missing new_price): { "error": { "Bad Request": "Please provide 'new_price' as query parameter, JSON, or form data." } }
- Error 403: { "error": { "Forbidden": "Invalid or missing API key." } }
- Error 404: { "error": { "Not Found": "Cafe with the provided ID was not found." } }

7) Delete a cafe by id (requires API key)
- DELETE /report-closed/<cafe_id>
- Success 200: { "success": { "message": "Successfully deleted the cafe." } }
- Error 403: { "error": { "Forbidden": "Invalid or missing API key." } }
- Error 404: { "error": { "Not Found": "Cafe with the provided ID was not found." } }

Curl Examples
- Get random cafe:
  curl "http://127.0.0.1:5000/random"

- Get all cafes:
  curl "http://127.0.0.1:5000/all"

- Search by location:
  curl "http://127.0.0.1:5000/search?loc=Shoreditch"

- Add a cafe (JSON):
  curl -X POST "http://127.0.0.1:5000/add" ^
       -H "Content-Type: application/json" ^
       -H "X-API-KEY: TopSecretAPIKey" ^
       -d "{\"name\":\"Cafe Roma\",\"map_url\":\"https://maps.example/cafe-roma\",\"img_url\":\"https://images.example/cafe-roma.jpg\",\"location\":\"Shoreditch\",\"seats\":\"20\",\"has_toilet\":true,\"has_wifi\":true,\"has_sockets\":false,\"can_take_calls\":true,\"coffee_price\":\"£2.80\"}"

- Update price:
  curl -X PATCH "http://127.0.0.1:5000/update-price/1?new_price=%C2%A32.99" -H "X-API-KEY: TopSecretAPIKey"

- Delete cafe:
  curl -X DELETE "http://127.0.0.1:5000/report-closed/1" -H "X-API-KEY: TopSecretAPIKey"

Notes
- All responses are JSON except the home route, which returns HTML.
- Ensure your terminal encoding supports the currency symbol (or use plain numbers like 2.99).
- Debug mode is enabled by default (app.run(debug=True)). For production, disable debug and use a WSGI server.
