from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Boolean, func

'''
Install the required packages first: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from requirements.txt for this project.
'''

app = Flask(__name__)

# CREATE DB
class Base(DeclarativeBase):
    pass
# Connect to Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cafes.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)

# Simple API key configuration (can be overridden via environment or config management)
app.config.setdefault('API_KEY', 'TopSecretAPIKey')


def require_api_key():
    """Validate API key sent via header, query param, JSON, or form.
    Accepts any of:
    - Header: X-API-KEY
    - Query param: api-key
    - JSON body: {"api-key": "..."}
    - Form field: api-key
    Returns a Flask response (403) if unauthorized; otherwise None.
    """
    # Prefer header, then query, then JSON, then form
    key = (
        request.headers.get("X-API-KEY")
        or request.args.get("api-key")
        or ((request.get_json(silent=True) or {}).get("api-key"))
        or request.form.get("api-key")
    )
    if key != app.config.get('API_KEY'):
        return jsonify(error={"Forbidden": "Invalid or missing API key."}), 403
    return None


# Café TABLE Configuration
class Cafe(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    map_url: Mapped[str] = mapped_column(String(500), nullable=False)
    img_url: Mapped[str] = mapped_column(String(500), nullable=False)
    location: Mapped[str] = mapped_column(String(250), nullable=False)
    seats: Mapped[str] = mapped_column(String(250), nullable=False)
    has_toilet: Mapped[bool] = mapped_column(Boolean, nullable=False)
    has_wifi: Mapped[bool] = mapped_column(Boolean, nullable=False)
    has_sockets: Mapped[bool] = mapped_column(Boolean, nullable=False)
    can_take_calls: Mapped[bool] = mapped_column(Boolean, nullable=False)
    coffee_price: Mapped[str] = mapped_column(String(250), nullable=True)

    def to_dict(self):
        # Convert SQLAlchemy model instance to dictionary for JSON serialization
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


with app.app_context():
    db.create_all()


@app.route("/")
def home():
    return render_template("index.html")


# HTTP GET - Read Record

@app.route("/random", methods=["GET"])
def get_random_cafe():
    random_cafe = db.session.execute(db.select(Cafe).order_by(func.random()).limit(1)).scalars().first()
    if random_cafe:
        return jsonify(cafe=random_cafe.to_dict())
    else:
        return jsonify(error={"Not Found": "No cafes found"}), 404

@app.route("/all", methods=["GET"])
def get_all_cafes():
    all_cafes = db.session.execute(db.select(Cafe)).scalars().all()
    return jsonify(cafes=[cafe.to_dict() for cafe in all_cafes])

@app.route("/search", methods=["GET"])
def search_cafes():
    location = request.args.get("loc")
    if not location:
        return jsonify(error={"Bad Request": "Please provide 'loc' query parameter, e.g., /search?loc=Shoreditch"}), 400
    cafes = db.session.execute(db.select(Cafe).where(Cafe.location == location)).scalars().all()
    return jsonify(cafes=[cafe.to_dict() for cafe in cafes])

# HTTP POST - Create Record
@app.route("/add", methods=["POST"])
def add_cafe():
    # API key required
    auth = require_api_key()
    if auth:
        return auth
    # Accept both JSON and form data
    data = request.get_json(silent=True) or {}
    def g(key, default=None):
        return request.form.get(key, data.get(key, default))

    def parse_bool(val):
        if isinstance(val, bool):
            return val
        if val is None:
            return None
        s = str(val).strip().lower()
        if s in ("1", "true", "yes", "y", "on"): return True
        if s in ("0", "false", "no", "n", "off"): return False
        return None

    required_fields = [
        "name", "map_url", "img_url", "location", "seats",
        "has_toilet", "has_wifi", "has_sockets", "can_take_calls"
    ]

    payload = {field: g(field) for field in required_fields}
    payload["coffee_price"] = g("coffee_price")  # optional

    # Convert booleans
    bool_fields = ["has_toilet", "has_wifi", "has_sockets", "can_take_calls"]
    for bf in bool_fields:
        payload[bf] = parse_bool(payload.get(bf))

    # Validate required
    missing = [k for k in required_fields if payload.get(k) in (None, "")]
    bad_bools = [k for k in bool_fields if payload.get(k) is None]
    if missing or bad_bools:
        return jsonify(error={
            "Bad Request": "Missing or invalid fields",
            "missing": missing,
            "invalid_bools": bad_bools
        }), 400

    new_cafe = Cafe(
        name=payload["name"],
        map_url=payload["map_url"],
        img_url=payload["img_url"],
        location=payload["location"],
        seats=payload["seats"],
        has_toilet=payload["has_toilet"],
        has_wifi=payload["has_wifi"],
        has_sockets=payload["has_sockets"],
        can_take_calls=payload["can_take_calls"],
        coffee_price=payload.get("coffee_price"),
    )

    db.session.add(new_cafe)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify(error={"Database Error": str(e)}), 400

    return jsonify(success={"message": "Successfully added new cafe.", "cafe": new_cafe.to_dict()}), 201

# HTTP PUT/PATCH - Update Record
@app.route("/update-price/<int:cafe_id>", methods=["PATCH"])
def update_price(cafe_id):
    # API key required
    auth = require_api_key()
    if auth:
        return auth
    # Accept new_price via query string, JSON body, or form-encoded body
    new_price = request.args.get("new_price")
    if not new_price:
        data = request.get_json(silent=True) or {}
        new_price = data.get("new_price") if data else None
    if not new_price:
        new_price = request.form.get("new_price")

    cafe = db.session.get(Cafe, cafe_id)
    if not cafe:
        return jsonify(error={"Not Found": "Cafe with the provided ID was not found."}), 404

    if not new_price:
        return jsonify(error={"Bad Request": "Please provide 'new_price' as query parameter, JSON, or form data."}), 400

    cafe.coffee_price = new_price
    db.session.commit()
    return jsonify(success={"message": "Successfully updated the coffee price.", "cafe": cafe.to_dict()}), 200

# HTTP DELETE - Delete Record

@app.route("/report-closed/<int:cafe_id>", methods=["DELETE"])
def delete_cafe(cafe_id):
    # API key required
    auth = require_api_key()
    if auth:
        return auth

    cafe = db.session.get(Cafe, cafe_id)
    if not cafe:
        return jsonify(error={"Not Found": "Cafe with the provided ID was not found."}), 404

    db.session.delete(cafe)
    db.session.commit()
    return jsonify(success={"message": "Successfully deleted the cafe."}), 200


if __name__ == '__main__':
    app.run(debug=True)
