# app.py

import os
import sys
import tempfile

from flask import Flask, request, jsonify, render_template, send_file

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "core"))

from dataset_loader import load_dataset
from schema_reader import read_schema
from intent_detector import load_model, predict_intent
from sql_generator import build_query, query_to_sql
from sql_validator import validate_sql
from sql_executor import execute_query

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-change-in-prod")

USE_POSTGRES = bool(
    os.environ.get("DATABASE_URL") or os.environ.get("NEON_DATABASE_URL")
)

DB_PATH = "data/database.db"
TABLE_NAME = "data"

if not USE_POSTGRES:
    os.makedirs("data", exist_ok=True)

_state = {
    "df":         None,
    "schema":     None,
    "model":      None,
    "vectorizer": None,
}

try:
    _state["model"], _state["vectorizer"] = load_model(
        "models/intent_model.pkl", "models/vectorizer.pkl"
    )
except FileNotFoundError:
    print("WARNING: Model files not found. Run: python3 models/train_intent.py")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/simulator")
def simulator():
    return send_file(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "simulation.html")
    )


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400

    filename = f.filename.lower()

    if not (
        filename.endswith(".csv") or
        filename.endswith(".xlsx") or
        filename.endswith(".xls")
    ):
        return jsonify({
            "error": "Only CSV and Excel (.csv, .xlsx, .xls) files are supported."
        }), 400

    extension = os.path.splitext(f.filename)[1].lower()

    tmp = tempfile.NamedTemporaryFile(
        suffix=extension,
        delete=False,
        prefix="nl2sql_"
    )
    try:
        f.save(tmp.name)
        tmp.close()

        try:
            df = load_dataset(tmp.name, DB_PATH, TABLE_NAME)
            schema = read_schema(df)
        except Exception as e:
            print(f"Upload error: {e}")
            return jsonify({
                "error": "Failed to parse the dataset. Ensure the CSV or Excel file is valid and contains a header row."
            }), 500
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    _state["df"] = df
    _state["schema"] = schema

    return jsonify({
        "success":  True,
        "filename": f.filename,
        "rows":     len(df),
        "columns":  list(df.columns),
        "preview":  df.head(5).fillna("").values.tolist(),
        "backend":  "postgresql" if USE_POSTGRES else "sqlite",
    })


@app.route("/ask", methods=["POST"])
def ask():
    if _state["df"] is None:
        return jsonify({"error": "No dataset loaded. Please upload a CSV or Excel file first."}), 400

    if _state["model"] is None:
        return jsonify({"error": "Model not loaded. Run: python3 models/train_intent.py"}), 500

    data     = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "Question is empty"}), 400

    df         = _state["df"]
    schema     = _state["schema"]
    model      = _state["model"]
    vectorizer = _state["vectorizer"]

    intent = predict_intent(question, model, vectorizer)
    query  = build_query(question, schema, intent)

    try:
        sql = query_to_sql(query, TABLE_NAME)
    except ValueError as e:
        return jsonify({
            "sql":     None,
            "intent":  intent,
            "error":   str(e),
            "columns": [],
            "rows":    [],
        })

    is_valid, validation_msg = validate_sql(sql, schema, TABLE_NAME)
    if not is_valid:
        return jsonify({
            "sql":     sql,
            "intent":  intent,
            "error":   f"SQL validation failed: {validation_msg}",
            "columns": [],
            "rows":    [],
        })

    try:
        columns, rows = execute_query(sql, DB_PATH)
    except Exception as e:
        print(f"Query execution error: {e}")
        return jsonify({
            "sql":     sql,
            "intent":  intent,
            "error":   "Query execution failed. The generated SQL could not be run.",
            "columns": [],
            "rows":    [],
        })

    return jsonify({
        "sql":     sql,
        "intent":  intent,
        "error":   None,
        "columns": columns,
        "rows":    [list(r) for r in rows],
        "count":   len(rows),
    })


@app.route("/health")
def health():
    return jsonify({
        "status":  "ok",
        "model":   _state["model"] is not None,
        "backend": "postgresql" if USE_POSTGRES else "sqlite",
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
