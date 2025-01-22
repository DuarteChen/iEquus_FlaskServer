from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

# Initialize the Flask application
app = Flask(__name__)

# Database configuration (Make sure to replace 'localhost' with your container's host or IP)
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:a22203153@iEquus-mysql:3306/iEquusDB"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the database object
db = SQLAlchemy(app)

# Define the Client model
class Client(db.Model):
    __tablename__ = 'Clients'
    
    idClient = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    phoneNumber = db.Column(db.String(20), nullable=True)
    phoneCountryCode = db.Column(db.String(10), nullable=True)

    def __init__(self, name, email=None, phoneNumber=None, phoneCountryCode=None):
        self.name = name
        self.email = email
        self.phoneNumber = phoneNumber
        self.phoneCountryCode = phoneCountryCode

# Define the route to receive Client data
@app.route('/clients', methods=['POST'])
def add_client():
    try:
        data = request.get_json()

        # Ensure required data exists in the request
        if 'name' not in data:
            return jsonify({"error": "Client name is required"}), 400

        # Create a new Client instance
        client = Client(
            name=data['name'],
            email=data.get('email'),
            phoneNumber=data.get('phoneNumber'),
            phoneCountryCode=data.get('phoneCountryCode')
        )

        # Add the client to the session and commit to the database
        db.session.add(client)
        db.session.commit()

        # Return the newly created client data
        return jsonify({
            "idClient": client.idClient,
            "name": client.name,
            "email": client.email,
            "phoneNumber": client.phoneNumber,
            "phoneCountryCode": client.phoneCountryCode
        }), 201

    except Exception as e:
        # In case of error, return an error message
        return jsonify({"error": str(e)}), 500

@app.route("/clients", methods=["GET"])
def get_clients():
    try:
        # Fetch all clients from the database
        clients = Client.query.all()

        # Prepare the response data as a list of dictionaries
        clients_list = [{"idClient": client.idClient, "name": client.name, "email": client.email,
                         "phoneNumber": client.phoneNumber, "phoneCountryCode": client.phoneCountryCode}
                        for client in clients]

        return jsonify(clients_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# Run the application
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9090)