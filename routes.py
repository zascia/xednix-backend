from flask import jsonify
from app import app, db

@app.route('/')
def hello_world():
    return jsonify({"message": "Hello, Xednix!"})