from flask import Flask, jsonify, redirect, render_template, request, url_for
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

# Database config
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "12345",  # Change if needed
    "database": "organ_donation",
}


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/add_donor", methods=["POST"])
def add_donor():
    name = request.form.get("name", "").strip()
    age = to_int(request.form.get("age"))
    blood = request.form.get("blood", "").strip()
    organ = request.form.get("organ", "").strip()
    city = request.form.get("city", "").strip()
    contact = request.form.get("contact", "").strip()

    if not all([name, blood, organ, city]):
        return jsonify({"status": "error", "message": "Missing required donor fields"}), 400

    query = (
        "INSERT INTO donors (name, age, blood_group, organ, city, contact) "
        "VALUES (%s, %s, %s, %s, %s, %s)"
    )

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(query, (name, age, blood, organ, city, contact))
        connection.commit()
        return redirect(url_for("home", msg="Donor added successfully"))
    except Error as err:
        return render_template("index.html", error=f"Database error: {err}")
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@app.route("/add_recipient", methods=["POST"])
def add_recipient():
    name = request.form.get("name", "").strip()
    age = to_int(request.form.get("age"))
    blood = request.form.get("blood", "").strip()
    organ_needed = request.form.get("organ_needed", "").strip()
    city = request.form.get("city", "").strip()
    urgency_level = to_int(request.form.get("urgency_level"), default=1)

    if not all([name, blood, organ_needed, city]):
        return jsonify({"status": "error", "message": "Missing required recipient fields"}), 400

    query = (
        "INSERT INTO recipients (name, age, blood_group, organ_needed, city, urgency_level) "
        "VALUES (%s, %s, %s, %s, %s, %s)"
    )

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(query, (name, age, blood, organ_needed, city, urgency_level))
        connection.commit()
        return redirect(url_for("home", msg="Recipient added successfully"))
    except Error as err:
        return render_template("index.html", error=f"Database error: {err}")
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@app.route("/view_matches", methods=["GET"])
def view_matches():
    """
    Live matching query:
    - blood compatibility
    - same organ
    - same city
    - score includes urgency
    """
    city = request.args.get("city", "").strip()
    organ = request.args.get("organ", "").strip()
    recipient_blood = request.args.get("recipient_blood", "").strip()
    sort_by = request.args.get("sort_by", "urgency")
    sort_field = "urgency_level DESC, match_score DESC"
    if sort_by == "score":
        sort_field = "match_score DESC, urgency_level DESC"
    recipient_limit = 80
    top_donors_per_recipient = 3

    query = f"""
    WITH filtered_recipients AS (
        SELECT
            r.recipient_id,
            r.name,
            r.blood_group,
            r.organ_needed,
            r.city,
            r.urgency_level
        FROM recipients r
        WHERE (%s = '' OR r.city = %s)
          AND (%s = '' OR r.organ_needed = %s)
          AND (%s = '' OR r.blood_group = %s)
        ORDER BY r.urgency_level DESC, r.recipient_id DESC
        LIMIT %s
    ),
    ranked AS (
        SELECT
            fr.recipient_id,
            fr.name AS recipient_name,
            fr.blood_group AS recipient_blood_group,
            fr.organ_needed,
            fr.city,
            fr.urgency_level,
            d.donor_id,
            d.name AS donor_name,
            d.blood_group AS donor_blood_group,
            (
                50
                + 30
                + 20
                + CASE WHEN d.blood_group = fr.blood_group THEN 10 ELSE 0 END
                + (fr.urgency_level * 10)
            ) AS match_score,
            ROW_NUMBER() OVER (
                PARTITION BY fr.recipient_id
                ORDER BY
                    (
                        50
                        + 30
                        + 20
                        + CASE WHEN d.blood_group = fr.blood_group THEN 10 ELSE 0 END
                        + (fr.urgency_level * 10)
                    ) DESC,
                    d.donor_id
            ) AS rn
        FROM filtered_recipients fr
        JOIN donors d
            ON d.organ = fr.organ_needed
           AND d.city = fr.city
        JOIN blood_compatibility bc
            ON bc.donor_blood_group = d.blood_group
           AND bc.recipient_blood_group = fr.blood_group
    )
    SELECT
        recipient_id,
        recipient_name,
        recipient_blood_group,
        organ_needed,
        city,
        urgency_level,
        donor_id,
        donor_name,
        donor_blood_group,
        match_score,
        CASE WHEN rn = 1 THEN 1 ELSE 0 END AS is_best_match
    FROM ranked
    WHERE rn <= %s
    ORDER BY {sort_field}, recipient_id, donor_id
    """

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            query,
            (
                city,
                city,
                organ,
                organ,
                recipient_blood,
                recipient_blood,
                recipient_limit,
                top_donors_per_recipient,
            ),
        )
        matches = cursor.fetchall()
        return jsonify(
            {
                "status": "success",
                "count": len(matches),
                "filters": {
                    "city": city,
                    "organ": organ,
                    "recipient_blood": recipient_blood,
                    "sort_by": sort_by,
                },
                "matches": matches,
            }
        )
    except Error as err:
        return jsonify({"status": "error", "message": str(err)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@app.route("/matches", methods=["GET"])
def matches_page():
    city = request.args.get("city", "").strip()
    organ = request.args.get("organ", "").strip()
    recipient_blood = request.args.get("recipient_blood", "").strip()
    sort_by = request.args.get("sort_by", "urgency")
    sort_field = "urgency_level DESC, match_score DESC"
    if sort_by == "score":
        sort_field = "match_score DESC, urgency_level DESC"
    recipient_limit = 80
    top_donors_per_recipient = 3

    query = f"""
    WITH filtered_recipients AS (
        SELECT
            r.recipient_id,
            r.name,
            r.blood_group,
            r.organ_needed,
            r.city,
            r.urgency_level
        FROM recipients r
        WHERE (%s = '' OR r.city = %s)
          AND (%s = '' OR r.organ_needed = %s)
          AND (%s = '' OR r.blood_group = %s)
        ORDER BY r.urgency_level DESC, r.recipient_id DESC
        LIMIT %s
    ),
    ranked AS (
        SELECT
            fr.recipient_id,
            fr.name AS recipient_name,
            fr.blood_group AS recipient_blood_group,
            fr.organ_needed,
            fr.city,
            fr.urgency_level,
            d.donor_id,
            d.name AS donor_name,
            d.blood_group AS donor_blood_group,
            (
                50
                + 30
                + 20
                + CASE WHEN d.blood_group = fr.blood_group THEN 10 ELSE 0 END
                + (fr.urgency_level * 10)
            ) AS match_score,
            ROW_NUMBER() OVER (
                PARTITION BY fr.recipient_id
                ORDER BY
                    (
                        50
                        + 30
                        + 20
                        + CASE WHEN d.blood_group = fr.blood_group THEN 10 ELSE 0 END
                        + (fr.urgency_level * 10)
                    ) DESC,
                    d.donor_id
            ) AS rn
        FROM filtered_recipients fr
        JOIN donors d
            ON d.organ = fr.organ_needed
           AND d.city = fr.city
        JOIN blood_compatibility bc
            ON bc.donor_blood_group = d.blood_group
           AND bc.recipient_blood_group = fr.blood_group
    )
    SELECT
        recipient_id,
        recipient_name,
        recipient_blood_group,
        organ_needed,
        city,
        urgency_level,
        donor_id,
        donor_name,
        donor_blood_group,
        match_score,
        CASE WHEN rn = 1 THEN 1 ELSE 0 END AS is_best_match
    FROM ranked
    WHERE rn <= %s
    ORDER BY {sort_field}, recipient_id, donor_id
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            query,
            (
                city,
                city,
                organ,
                organ,
                recipient_blood,
                recipient_blood,
                recipient_limit,
                top_donors_per_recipient,
            ),
        )
        matches = cursor.fetchall()
        filters = {
            "city": city,
            "organ": organ,
            "recipient_blood": recipient_blood,
            "sort_by": sort_by,
        }
        return render_template("matches.html", matches=matches, filters=filters)
    except Error as err:
        return render_template("matches.html", matches=[], filters={}, error=f"Database error: {err}")
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# Run server
if __name__ == "__main__":
    app.run(debug=True)
