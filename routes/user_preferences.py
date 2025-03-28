from flask import Blueprint, jsonify, request
from models.user_preferences import RentedGPU, PriceAlert, FavoriteGPU, SelectedGPU
from models.gpu_listing import GPUListing
from utils.database import db
from datetime import datetime
from middleware.auth import auth_required

bp = Blueprint("preferences", __name__)


# Selected GPUs endpoints
@bp.route("/selected-gpus", methods=["GET"])
def get_selected_gpus():
    try:
        selected_gpus = SelectedGPU.query.all()
        return jsonify([gpu.to_dict() for gpu in selected_gpus])
    except Exception as e:
        print(f"Error fetching selected GPUs: {str(e)}")
        return jsonify({"error": "Failed to fetch selected GPUs"}), 500


@bp.route("/selected-gpus", methods=["POST"])
def add_selected_gpu():
    try:
        data = request.json
        gpu_id = data.get("gpuId")

        # Check if GPU exists
        gpu = GPUListing.query.get_or_404(gpu_id)

        # Check if already selected
        existing = SelectedGPU.query.filter_by(gpu_id=gpu_id).first()
        if existing:
            return jsonify({"message": "GPU is already selected"}), 400

        selected = SelectedGPU(gpu_id=gpu_id)
        db.session.add(selected)
        db.session.commit()

        return jsonify(selected.to_dict())
    except Exception as e:
        print(f"Error adding selected GPU: {str(e)}")
        return jsonify({"error": "Failed to add selected GPU"}), 500


@bp.route("/selected-gpus/<int:gpu_id>", methods=["DELETE"])
def remove_selected_gpu(gpu_id):
    try:
        selected = SelectedGPU.query.filter_by(gpu_id=gpu_id).first_or_404()
        db.session.delete(selected)
        db.session.commit()
        return jsonify({"message": "GPU removed from selection"})
    except Exception as e:
        print(f"Error removing selected GPU: {str(e)}")
        return jsonify({"error": "Failed to remove selected GPU"}), 500


# Rented GPUs endpoints
@bp.route("/rented-gpus", methods=["GET"])
def get_rented_gpus():
    try:
        rented_gpus = RentedGPU.query.filter_by(is_active=True).all()
        return jsonify([rental.to_dict() for rental in rented_gpus])
    except Exception as e:
        print(f"Error fetching rented GPUs: {str(e)}")
        return jsonify({"error": "Failed to fetch rented GPUs"}), 500


@bp.route("/rented-gpus", methods=["POST"])
def add_rented_gpu():
    try:
        data = request.json
        gpu_id = data.get("gpuId")

        # Check if GPU exists
        gpu = GPUListing.query.get_or_404(gpu_id)

        # Check if already rented and active
        existing = RentedGPU.query.filter_by(gpu_id=gpu_id, is_active=True).first()
        if existing:
            return jsonify({"message": "GPU is already rented"}), 400

        rental = RentedGPU(gpu_id=gpu_id)
        db.session.add(rental)
        db.session.commit()

        return jsonify(rental.to_dict())
    except Exception as e:
        print(f"Error adding rented GPU: {str(e)}")
        return jsonify({"error": "Failed to add rented GPU"}), 500


@bp.route("/rented-gpus/<int:gpu_id>", methods=["DELETE"])
def remove_rented_gpu(gpu_id):
    try:
        rental = RentedGPU.query.filter_by(gpu_id=gpu_id, is_active=True).first_or_404()
        rental.is_active = False
        rental.rental_end = datetime.utcnow()
        db.session.commit()
        return jsonify(rental.to_dict())
    except Exception as e:
        print(f"Error removing rented GPU: {str(e)}")
        return jsonify({"error": "Failed to remove rented GPU"}), 500


# Price Alerts endpoints
@bp.route("/price-alerts", methods=["GET"])
def get_price_alerts():
    try:
        alerts = PriceAlert.query.all()
        alerts_dict = {}
        for alert in alerts:
            alerts_dict.update(alert.to_dict())
        return jsonify(alerts_dict)
    except Exception as e:
        print(f"Error fetching price alerts: {str(e)}")
        return jsonify({"error": "Failed to fetch price alerts"}), 500


@bp.route("/price-alerts", methods=["POST"])
def add_price_alert():
    try:
        data = request.json
        gpu_id = data.get("gpuId")
        gpu_type = data.get("gpuType")
        target_price = data.get("targetPrice")
        is_type_alert = data.get("isTypeAlert", False)

        # Check if alert already exists
        if is_type_alert:
            existing = PriceAlert.query.filter_by(
                gpu_type=gpu_type, is_type_alert=True
            ).first()
        else:
            existing = PriceAlert.query.filter_by(
                gpu_id=gpu_id, is_type_alert=False
            ).first()

        if existing:
            return jsonify({"message": "Price alert already exists"}), 400

        alert = PriceAlert(
            gpu_id=None if is_type_alert else gpu_id,
            gpu_type=gpu_type if is_type_alert else None,
            target_price=target_price,
            is_type_alert=is_type_alert,
        )
        db.session.add(alert)
        db.session.commit()

        return jsonify(alert.to_dict())
    except Exception as e:
        print(f"Error adding price alert: {str(e)}")
        return jsonify({"error": "Failed to add price alert"}), 500


@bp.route("/price-alerts/<alert_id>", methods=["DELETE"])
def remove_price_alert(alert_id):
    try:
        if alert_id.startswith("type_"):
            gpu_type = alert_id[5:]  # Remove 'type_' prefix
            alert = PriceAlert.query.filter_by(
                gpu_type=gpu_type, is_type_alert=True
            ).first_or_404()
        else:
            alert = PriceAlert.query.filter_by(
                gpu_id=int(alert_id), is_type_alert=False
            ).first_or_404()

        db.session.delete(alert)
        db.session.commit()
        return jsonify({"message": "Price alert removed successfully"})
    except Exception as e:
        print(f"Error removing price alert: {str(e)}")
        return jsonify({"error": "Failed to remove price alert"}), 500


# Favorite GPUs endpoints
@bp.route("/favorite-gpus", methods=["GET"])
def get_favorite_gpus():
    try:
        favorites = FavoriteGPU.query.all()
        return jsonify([favorite.to_dict() for favorite in favorites])
    except Exception as e:
        print(f"Error fetching favorite GPUs: {str(e)}")
        return jsonify({"error": "Failed to fetch favorite GPUs"}), 500


@bp.route("/favorite-gpus", methods=["POST"])
def add_favorite_gpu():
    try:
        data = request.json
        gpu_id = data.get("gpuId")

        # Check if GPU exists
        gpu = GPUListing.query.get_or_404(gpu_id)

        # Check if already favorited
        existing = FavoriteGPU.query.filter_by(gpu_id=gpu_id).first()
        if existing:
            return jsonify({"message": "GPU is already favorited"}), 400

        favorite = FavoriteGPU(gpu_id=gpu_id)
        db.session.add(favorite)
        db.session.commit()

        return jsonify(favorite.to_dict())
    except Exception as e:
        print(f"Error adding favorite GPU: {str(e)}")
        return jsonify({"error": "Failed to add favorite GPU"}), 500


@bp.route("/favorite-gpus/<int:gpu_id>", methods=["DELETE"])
def remove_favorite_gpu(gpu_id):
    try:
        favorite = FavoriteGPU.query.filter_by(gpu_id=gpu_id).first_or_404()
        db.session.delete(favorite)
        db.session.commit()
        return jsonify({"message": "Favorite GPU removed successfully"})
    except Exception as e:
        print(f"Error removing favorite GPU: {str(e)}")
        return jsonify({"error": "Failed to remove favorite GPU"}), 500
