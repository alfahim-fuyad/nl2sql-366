"""
Flask web server for the NL2SQL AI application.

Handles CSV upload, schema extraction, and natural language query execution.
Uses PostgreSQL in production (DATABASE_URL or NEON_DATABASE_URL env var)
and SQLite as a local development fallback.
"""

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
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-change-in-prod")

USE_POSTGRES = bool(
    os.environ.get("DATABASE_URL") or os.environ.get("NEON_DATABASE_URL")
)

DB_PATH = "data/database.db"
TABLE_NAME = "data"

if not USE_POSTGRES:
    os.makedirs("data", exist_ok=True)

# In-memory application state (single-user; extend to sessions for multi-user)
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


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/simulator")
def simulator():
    """Serve the standalone interactive pipeline simulation page."""
    return send_file(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "simulation.html")
    )


@app.route("/upload", methods=["POST"])
def upload():
    """Accept a CSV file upload and return the schema and a row preview."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400

    if not f.filename.lower().endswith(".csv"):
        return jsonify({"error": "Only CSV files are supported"}), 400

    tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False, prefix="nl2sql_")
    try:
        f.save(tmp.name)
        tmp.close()

        try:
            df = load_dataset(tmp.name, DB_PATH, TABLE_NAME)
            schema = read_schema(df)
        except Exception as e:
            print(f"Upload error: {e}")
            return jsonify({
                "error": "Failed to parse CSV. Ensure the file is valid with a header row."
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
    """Translate a natural language question to SQL, execute it, and return results."""
    if _state["df"] is None:
        return jsonify({"error": "No dataset loaded. Please upload a CSV first."}), 400

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
    """Health check endpoint for deployment monitoring."""
    return jsonify({
        "status":  "ok",
        "model":   _state["model"] is not None,
        "backend": "postgresql" if USE_POSTGRES else "sqlite",
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
