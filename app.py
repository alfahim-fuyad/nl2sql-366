# app.py

import os
import sys
import tempfile
import re

from flask import Flask, request, jsonify, render_template, send_file


# =========================================================
# PROJECT PATHS
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

CORE_DIR = os.path.join(
    BASE_DIR,
    "core"
)

MODEL_DIR = os.path.join(
    BASE_DIR,
    "models"
)

DATA_DIR = os.path.join(
    BASE_DIR,
    "data"
)

TEMPLATE_DIR = os.path.join(
    BASE_DIR,
    "templates"
)


# =========================================================
# PYTHON PATH
# =========================================================

if CORE_DIR not in sys.path:
    sys.path.insert(
        0,
        CORE_DIR
    )


# =========================================================
# CORE IMPORTS
# =========================================================

try:

    from dataset_loader import load_dataset
    from schema_reader import read_schema
    from intent_detector import (
        load_model,
        predict_intent
    )
    from sql_generator import (
        build_query,
        query_to_sql
    )
    from sql_validator import validate_sql
    from sql_executor import execute_query

except Exception as e:

    print(
        "\n" + "=" * 70
    )
    print(
        "FATAL ERROR: Failed to import core modules"
    )
    print(
        "=" * 70
    )
    print(
        f"{type(e).__name__}: {e}"
    )
    print(
        "=" * 70 + "\n"
    )

    raise


# =========================================================
# FLASK APP
# =========================================================

app = Flask(
    __name__,
    template_folder=TEMPLATE_DIR
)

app.config[
    "MAX_CONTENT_LENGTH"
] = 50 * 1024 * 1024


app.secret_key = os.environ.get(
    "SESSION_SECRET",
    "dev-secret-change-in-prod"
)


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

DATABASE_URL = (
    os.environ.get("DATABASE_URL")
    or
    os.environ.get("NEON_DATABASE_URL")
)

USE_POSTGRES = bool(
    DATABASE_URL
)


TABLE_NAME = "data"

DB_PATH = os.path.join(
    DATA_DIR,
    "database.db"
)


# =========================================================
# SQLITE DIRECTORY
# =========================================================

if not USE_POSTGRES:

    os.makedirs(
        DATA_DIR,
        exist_ok=True
    )


# =========================================================
# APPLICATION STATE
# =========================================================

_state = {
    "df": None,
    "schema": None,
    "model": None,
    "vectorizer": None,
}


# =========================================================
# LOAD AI MODEL
# =========================================================

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "intent_model.pkl"
)

VECTORIZER_PATH = os.path.join(
    MODEL_DIR,
    "vectorizer.pkl"
)


try:

    if (
        os.path.exists(MODEL_PATH)
        and
        os.path.exists(VECTORIZER_PATH)
    ):

        (
            _state["model"],
            _state["vectorizer"]
        ) = load_model(
            MODEL_PATH,
            VECTORIZER_PATH
        )

        print(
            "AI model loaded successfully."
        )

    else:

        print(
            "WARNING: Model files not found."
        )

        print(
            f"Expected model: {MODEL_PATH}"
        )

        print(
            f"Expected vectorizer: {VECTORIZER_PATH}"
        )

except Exception as e:

    print(
        "WARNING: Failed to load AI model."
    )

    print(
        f"{type(e).__name__}: {e}"
    )

    _state["model"] = None
    _state["vectorizer"] = None


# =========================================================
# COLUMN COUNT QUESTION DETECTOR
# =========================================================

COLUMN_COUNT_PATTERN = re.compile(
    r"\bhow\s+many\s+columns?\b"
    r"|\bhow\s+many\s+colums?\b"
    r"|\bnumber\s+of\s+columns?\b"
    r"|\bcount\s+of\s+columns?\b"
    r"|\btotal\s+columns?\b"
    r"|\bcolumns?\s+count\b"
    r"|\bhow\s+many\s+fields?\b"
    r"|\bnumber\s+of\s+fields?\b"
    r"|\bcount\s+of\s+fields?\b"
    r"|\btotal\s+fields?\b",
    re.IGNORECASE
)


# =========================================================
# HOME
# =========================================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# =========================================================
# SIMULATOR
# =========================================================

@app.route("/simulator")
def simulator():

    simulation_file = os.path.join(
        BASE_DIR,
        "simulation.html"
    )

    if not os.path.exists(
        simulation_file
    ):

        return jsonify({
            "error":
                "simulation.html not found."
        }), 404

    return send_file(
        simulation_file
    )


# =========================================================
# UPLOAD DATASET
# =========================================================

@app.route(
    "/upload",
    methods=["POST"]
)
def upload():

    # -----------------------------------------------------
    # CHECK FILE
    # -----------------------------------------------------

    if "file" not in request.files:

        return jsonify({
            "error":
                "No file uploaded."
        }), 400


    f = request.files["file"]


    if not f.filename:

        return jsonify({
            "error":
                "Empty filename."
        }), 400


    filename = f.filename.lower()


    # -----------------------------------------------------
    # FILE TYPE
    # -----------------------------------------------------

    allowed_extensions = (
        ".csv",
        ".xlsx",
        ".xls"
    )


    if not filename.endswith(
        allowed_extensions
    ):

        return jsonify({
            "error":
                "Only CSV and Excel "
                "(.csv, .xlsx, .xls) "
                "files are supported."
        }), 400


    extension = os.path.splitext(
        f.filename
    )[1].lower()


    # -----------------------------------------------------
    # TEMP FILE
    # -----------------------------------------------------

    tmp = tempfile.NamedTemporaryFile(
        suffix=extension,
        delete=False,
        prefix="nl2sql_"
    )


    tmp_path = tmp.name


    try:

        f.save(
            tmp_path
        )

        tmp.close()


        # -------------------------------------------------
        # LOAD DATASET
        # -------------------------------------------------

        try:

            df = load_dataset(
                tmp_path,
                DB_PATH,
                TABLE_NAME
            )

            schema = read_schema(
                df
            )

        except Exception as e:

            print(
                "\nUPLOAD ERROR:"
            )

            print(
                f"{type(e).__name__}: {e}"
            )

            return jsonify({
                "error":
                    "Failed to parse the dataset. "
                    "Ensure the CSV or Excel file "
                    "is valid and contains a "
                    "header row."
            }), 500


    finally:

        try:

            os.unlink(
                tmp_path
            )

        except OSError:

            pass


    # -----------------------------------------------------
    # SAVE APPLICATION STATE
    # -----------------------------------------------------

    _state["df"] = df
    _state["schema"] = schema


    print(
        f"Dataset loaded: "
        f"{f.filename}"
    )

    print(
        f"Rows: {len(df)}"
    )

    print(
        f"Columns: {list(df.columns)}"
    )


    # -----------------------------------------------------
    # RESPONSE
    # -----------------------------------------------------

    return jsonify({

        "success": True,

        "filename":
            f.filename,

        "rows":
            len(df),

        "columns":
            list(df.columns),

        "preview":
            df.head(5)
            .fillna("")
            .values
            .tolist(),

        "backend":
            "postgresql"
            if USE_POSTGRES
            else "sqlite",

    })


# =========================================================
# ASK QUESTION
# =========================================================

@app.route(
    "/ask",
    methods=["POST"]
)
def ask():

    # -----------------------------------------------------
    # CHECK DATASET
    # -----------------------------------------------------

    if _state["df"] is None:

        return jsonify({
            "error":
                "No dataset loaded. "
                "Please upload a CSV or Excel "
                "file first."
        }), 400


    # -----------------------------------------------------
    # GET REQUEST
    # -----------------------------------------------------

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )


    question = (
        data.get("question")
        or ""
    ).strip()


    if not question:

        return jsonify({
            "error":
                "Question is empty."
        }), 400


    # -----------------------------------------------------
    # DATASET STATE
    # -----------------------------------------------------

    df = _state["df"]

    schema = _state["schema"]


    # =====================================================
    # COLUMN COUNT
    # =====================================================

    if COLUMN_COUNT_PATTERN.search(
        question
    ):

        column_names = list(
            schema.keys()
        )

        column_count = len(
            column_names
        )


        return jsonify({

            "sql": None,

            "intent":
                "COLUMN_COUNT",

            "error": None,

            "columns":
                column_names,

            "rows": [],

            "count":
                column_count,

            "column_count":
                column_count,

            "column_names":
                column_names,

            "answer":
                f"There are "
                f"{column_count} columns.",

        })


    # =====================================================
    # MODEL CHECK
    # =====================================================

    if (
        _state["model"] is None
        or
        _state["vectorizer"] is None
    ):

        return jsonify({

            "sql": None,

            "intent": None,

            "error":
                "Model not loaded. "
                "Please ensure "
                "models/intent_model.pkl and "
                "models/vectorizer.pkl "
                "exist.",

            "columns": [],

            "rows": [],

        }), 500


    model = _state["model"]

    vectorizer = _state[
        "vectorizer"
    ]


    # =====================================================
    # INTENT DETECTION
    # =====================================================

    try:

        intent = predict_intent(
            question,
            model,
            vectorizer
        )

    except Exception as e:

        print(
            "\nINTENT ERROR:"
        )

        print(
            f"{type(e).__name__}: {e}"
        )

        return jsonify({

            "sql": None,

            "intent": None,

            "error":
                "Intent detection failed.",

            "columns": [],

            "rows": [],

        }), 500


    # =====================================================
    # BUILD QUERY
    # =====================================================

    try:

        query = build_query(
            question,
            schema,
            intent
        )

    except Exception as e:

        print(
            "\nQUERY BUILD ERROR:"
        )

        print(
            f"{type(e).__name__}: {e}"
        )

        return jsonify({

            "sql": None,

            "intent": intent,

            "error":
                "Failed to build SQL query.",

            "columns": [],

            "rows": [],

        }), 500


    # =====================================================
    # GENERATE SQL
    # =====================================================

    try:

        sql = query_to_sql(
            query,
            TABLE_NAME
        )

    except ValueError as e:

        return jsonify({

            "sql": None,

            "intent": intent,

            "error":
                str(e),

            "columns": [],

            "rows": [],

        })


    except Exception as e:

        print(
            "\nSQL GENERATION ERROR:"
        )

        print(
            f"{type(e).__name__}: {e}"
        )

        return jsonify({

            "sql": None,

            "intent": intent,

            "error":
                "SQL generation failed.",

            "columns": [],

            "rows": [],

        }), 500


    # =====================================================
    # VALIDATE SQL
    # =====================================================

    try:

        is_valid, validation_msg = (
            validate_sql(
                sql,
                schema,
                TABLE_NAME
            )
        )

    except Exception as e:

        print(
            "\nSQL VALIDATION ERROR:"
        )

        print(
            f"{type(e).__name__}: {e}"
        )

        return jsonify({

            "sql": sql,

            "intent": intent,

            "error":
                "SQL validation failed.",

            "columns": [],

            "rows": [],

        }), 500


    if not is_valid:

        return jsonify({

            "sql": sql,

            "intent": intent,

            "error":
                "SQL validation failed: "
                + str(validation_msg),

            "columns": [],

            "rows": [],

        })


    # =====================================================
    # EXECUTE SQL
    # =====================================================

    try:

        columns, rows = execute_query(
            sql,
            DB_PATH
        )

    except Exception as e:

        print(
            "\nQUERY EXECUTION ERROR:"
        )

        print(
            f"{type(e).__name__}: {e}"
        )

        return jsonify({

            "sql": sql,

            "intent": intent,

            "error":
                "Query execution failed. "
                "The generated SQL could not "
                "be executed.",

            "columns": [],

            "rows": [],

        }), 500


    # =====================================================
    # NORMAL RESPONSE
    # =====================================================

    return jsonify({

        "sql": sql,

        "intent": intent,

        "error": None,

        "columns":
            columns,

        "rows":
            [
                list(row)
                for row in rows
            ],

        "count":
            len(rows),

    })


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():

    return jsonify({

        "status":
            "ok",

        "model":
            (
                _state["model"]
                is not None
            ),

        "vectorizer":
            (
                _state["vectorizer"]
                is not None
            ),

        "dataset":
            (
                _state["df"]
                is not None
            ),

        "backend":
            (
                "postgresql"
                if USE_POSTGRES
                else "sqlite"
            ),

    })


# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(413)
def file_too_large(error):

    return jsonify({
        "error":
            "File too large. "
            "Maximum upload size is 50 MB."
    }), 413


@app.errorhandler(404)
def not_found(error):

    return jsonify({
        "error":
            "Endpoint not found."
    }), 404


@app.errorhandler(500)
def internal_error(error):

    print(
        f"Internal server error: {error}"
    )

    return jsonify({
        "error":
            "Internal server error."
    }), 500


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            "5000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )