from flask import Flask, jsonify, send_file
import boto3
import json
from io import BytesIO

app = Flask(__name__)

BUCKET_NAME = "bluestone-image-labeling-a08324be2c5f"
s3_client = boto3.client("s3")


@app.route("/")
def index():
    return send_file("index.html")


@app.route("/favicon.ico")
def favicon():
    return "", 204


@app.route("/api/images")
def list_images():
    try:
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix="uploads/")
        images = [
            key.replace("uploads/", "")
            for key in [obj["Key"] for obj in response.get("Contents", [])]
            if key != "uploads/" and key.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
        return jsonify(images)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/image/<filename>")
def get_image(filename):
    try:
        obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=f"uploads/{filename}")
        return send_file(
            BytesIO(obj["Body"].read()), mimetype="image/jpeg", as_attachment=False
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 404


@app.route("/api/labels/<filename>")
def get_labels(filename):
    try:
        # Remove file extension and add .json
        label_filename = filename.rsplit(".", 1)[0] + ".json"
        obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=f"labels/{label_filename}")
        labels = json.loads(obj["Body"].read().decode("utf-8"))
        return jsonify(labels)
    except Exception as e:
        return jsonify({"error": str(e)}), 404


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
