from flask import Flask, request, jsonify
import tempfile
import os
from main import process_file, classify_lob_from_text, process_df  # make sure this imports successfully
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
@app.route("/")
def home():
    return "✅ Supplier LOB Classifier is running!"

@app.route("/predict", methods=["POST"])
def predict():
    try:
        file = request.files.get("file")
        if file is None:
            return jsonify({"error": "No file uploaded"}), 400

        if not file.filename.lower().endswith(".csv"):
            return jsonify({"error": "Only CSV files are supported"}), 400

        # Save to a temporary location
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        file.save(temp_input.name)

        # Run your model
        df_result = process_file(open(temp_input.name, "rb"))

        if df_result.empty:
            return jsonify({"message": "No valid results"}), 204  # No content

        return jsonify(df_result.to_dict(orient="records"))

    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({"error": str(e)}), 500


# === Summary-based Route for Electron ===
@app.route("/predict_from_summary", methods=["POST"])
def predict_from_summary():
    try:
        data = request.get_json()
        if not data or "companies" not in data:
            return jsonify({"error": "Missing 'companies' in request body"}), 400

        results = process_df(data.get("companies"))

        return jsonify(results)

    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=7860, debug=False, use_reloader=False)
