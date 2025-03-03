from flask import Blueprint, request, jsonify, g
from models.cluster import Cluster, RentalGPU
from models.gpu_listing import GPUListing
from utils.database import db
from middleware.auth import auth_required
from models.user import User
from datetime import datetime, timedelta

bp = Blueprint("cluster", __name__, url_prefix="/api/clusters")


@bp.route("/", methods=["GET"])
@auth_required()
def get_user_clusters():
    """Get all clusters for the current user"""
    try:
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found. Please sync your account."}), 404

        clusters = Cluster.query.filter_by(user_id=user.id).all()
        return jsonify([cluster.to_dict() for cluster in clusters]), 200
    except Exception as e:
        print(f"Error in get_user_clusters: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:cluster_id>", methods=["GET"])
@auth_required()
def get_cluster(cluster_id):
    """Get a cluster"""
    try:
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found. Please sync your account."}), 404

        cluster = Cluster.query.filter_by(id=cluster_id, user_id=user.id).first()
        if not cluster:
            return jsonify({"error": "Cluster not found"}), 404
        return jsonify(cluster.to_dict()), 200
    except Exception as e:
        print(f"Error in get_cluster: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/", methods=["POST"])
@auth_required()
def create_cluster():
    """Create a new cluster"""
    try:
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found. Please sync your account."}), 404

        data = request.json
        if not data.get("name"):
            return jsonify({"error": "Cluster name is required"}), 400
        print("data")
        print(data)
        cluster = Cluster(
            name=data["name"],
            description=data.get("description", ""),
            user_id=user.id,
        )

        db.session.add(cluster)
        db.session.commit()

        return jsonify(cluster.to_dict()), 201
    except Exception as e:
        print(f"Error in create_cluster: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:cluster_id>", methods=["PUT"])
@auth_required()
def update_cluster(cluster_id):
    """Update a cluster"""
    try:
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found. Please sync your account."}), 404

        cluster = Cluster.query.filter_by(id=cluster_id, user_id=user.id).first()
        if not cluster:
            return jsonify({"error": "Cluster not found"}), 404

        data = request.json
        if "name" in data:
            cluster.name = data["name"]
        if "description" in data:
            cluster.description = data["description"]

        db.session.commit()
        return jsonify(cluster.to_dict()), 200
    except Exception as e:
        print(f"Error in update_cluster: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:cluster_id>", methods=["DELETE"])
@auth_required()
def delete_cluster(cluster_id):
    """Delete a cluster"""
    try:
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found. Please sync your account."}), 404

        cluster = Cluster.query.filter_by(id=cluster_id, user_id=user.id).first()
        if not cluster:
            return jsonify({"error": "Cluster not found"}), 404

        db.session.delete(cluster)
        db.session.commit()
        return "", 204
    except Exception as e:
        print(f"Error in delete_cluster: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:cluster_id>/gpu", methods=["POST"])
@auth_required()
def add_gpu_to_cluster(cluster_id):
    """Add a GPU to a cluster as a rental GPU"""
    try:
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found. Please sync your account."}), 404

        cluster = Cluster.query.filter_by(id=cluster_id, user_id=user.id).first()
        if not cluster:
            return jsonify({"error": "Cluster not found"}), 404

        if cluster.rental_gpu:
            return jsonify({"error": "Cluster already has a GPU assigned"}), 400

        data = request.json
        gpu_listing_id = data.get("gpu_listing_id")
        if not gpu_listing_id:
            return jsonify({"error": "GPU listing ID is required"}), 400

        gpu_listing = GPUListing.query.get(gpu_listing_id)
        if not gpu_listing:
            return jsonify({"error": "GPU listing not found"}), 404

        # First create the RentalGPU with only the base GPUListing attributes
        rental_gpu = RentalGPU(
            instance_name=gpu_listing.instance_name,
            configuration_id=gpu_listing.configuration_id,
            current_price=gpu_listing.current_price,
            host_id=gpu_listing.host_id,
        )

        # Then set the RentalGPU-specific attributes
        rental_gpu.cluster_id = cluster.id
        rental_gpu.ssh_keys = data.get("ssh_keys", [])
        rental_gpu.email_enabled = data.get("email_enabled", True)
        rental_gpu.users_with_access.append(user)

        db.session.add(rental_gpu)
        db.session.commit()

        return jsonify(cluster.to_dict()), 200
    except Exception as e:
        print(f"Error in add_gpu_to_cluster: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:cluster_id>/gpu/access", methods=["POST"])
@auth_required()
def manage_gpu_access(cluster_id):
    """Grant or revoke access to a rental GPU for users"""
    try:
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found. Please sync your account."}), 404

        cluster = Cluster.query.filter_by(id=cluster_id, user_id=user.id).first()
        if not cluster or not cluster.rental_gpu:
            return jsonify({"error": "Cluster or rental GPU not found"}), 404

        data = request.json
        user_ids = data.get("user_ids", [])
        action = data.get("action")  # 'grant' or 'revoke'

        if not user_ids or action not in ["grant", "revoke"]:
            return jsonify({"error": "Invalid request parameters"}), 400

        users = User.query.filter(User.id.in_(user_ids)).all()

        if action == "grant":
            for user in users:
                if user not in cluster.rental_gpu.users_with_access:
                    cluster.rental_gpu.users_with_access.append(user)
        else:  # revoke
            for user in users:
                if user in cluster.rental_gpu.users_with_access:
                    cluster.rental_gpu.users_with_access.remove(user)

        db.session.commit()
        return jsonify(cluster.to_dict()), 200
    except Exception as e:
        print(f"Error in manage_gpu_access: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:cluster_id>/gpu/ssh-keys", methods=["PUT"])
@auth_required()
def update_ssh_keys(cluster_id):
    """Update SSH keys for a rental GPU"""
    try:
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found. Please sync your account."}), 404

        cluster = Cluster.query.filter_by(id=cluster_id, user_id=user.id).first()
        if not cluster or not cluster.rental_gpu:
            return jsonify({"error": "Cluster or rental GPU not found"}), 404

        data = request.json
        ssh_keys = data.get("ssh_keys")
        if not isinstance(ssh_keys, list):
            return jsonify({"error": "SSH keys must be provided as a list"}), 400

        cluster.rental_gpu.ssh_keys = ssh_keys
        db.session.commit()

        return jsonify(cluster.to_dict()), 200
    except Exception as e:
        print(f"Error in update_ssh_keys: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
