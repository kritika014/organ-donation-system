from flask import Flask, render_template, request
import mysql.connector

app = Flask(__name__)

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="12345",
    database="organ_donation"
)
@app.route('/add_donor', methods=['POST'])
@app.route('/')
def home():
    return render_template('index.html')

def add_donor():
    cursor = db.cursor()

    name = request.form['name']
    age = request.form['age']
    blood = request.form['blood']
    organ = request.form['organ']
    city = request.form['city']
    contact = request.form['contact']

    query = "INSERT INTO donors (name, age, blood_group, organ, city, contact) VALUES (%s,%s,%s,%s,%s,%s)"
    values = (name, age, blood, organ, city, contact)

    cursor.execute(query, values)
    db.commit()

    return "Donor Added Successfully!"
