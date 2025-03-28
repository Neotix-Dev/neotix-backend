from flask import Blueprint, request, jsonify, g
from models.cluster import Cluster
from models.rental_gpu import RentalGPU
from models.gpu_listing import GPUListing
from models.user import User
from models.transaction import Transaction
from models.deployment_cost import DeploymentCost
from utils.database import db
from middleware.auth import auth_required, require_auth
from datetime import datetime, timedelta
from decimal import Decimal

bp = Blueprint("clusters", __name__)


@bp.route("/", methods=["GET"])
@auth_required()
def get_user_clusters():
    """Get all clusters for the current user"""
    try:
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

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

    except Exception as e:
        print(f"Error in get_clusters: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/", methods=["POST"])
@auth_required
def create_cluster(current_user):
    """Create a new cluster"""
    try:
        print(current_user)
        user = current_user
        print(user)
        if not user:
            return jsonify({"error": "User not found"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        required_fields = ["name"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        cluster = Cluster(
            name=data["name"], description=data.get("description"), user_id=user.id
        )

        db.session.add(cluster)
        db.session.commit()

        return jsonify(cluster.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        print(f"Error in create_cluster: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:cluster_id>", methods=["GET"])
@require_auth()
def get_cluster(cluster_id):
    """Get a specific cluster"""
    try:
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        cluster = Cluster.query.get(cluster_id)
        if not cluster:
            return jsonify({"error": "Cluster not found"}), 404

        if cluster.user_id != user.id:
            return jsonify({"error": "Unauthorized"}), 403

        return jsonify(cluster.to_dict()), 200

    except Exception as e:
        print(f"Error in get_cluster: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:cluster_id>/gpu", methods=["POST"])
@require_auth()
def add_gpu_to_cluster(cluster_id):
    """Add a GPU to a cluster"""
    try:
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        cluster = Cluster.query.get(cluster_id)
        if not cluster:
            return jsonify({"error": "Cluster not found"}), 404

        if cluster.user_id != user.id:
            return jsonify({"error": "Unauthorized"}), 403

        # Check if cluster already has a current GPU or active rental
        if cluster.current_gpu:
            return jsonify({"error": "Cluster already has a GPU assigned"}), 400
        if cluster.active_rental:
            return jsonify({"error": "Cluster already has an active GPU rental"}), 400

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        required_fields = ["gpu_listing_id"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        gpu_listing = GPUListing.query.get(data["gpu_listing_id"])
        if not gpu_listing:
            return jsonify({"error": "GPU listing not found"}), 404

        # If deploy=True in request, directly create a rental
        if data.get("deploy", False):
            rental_gpu = cluster.deploy_current_gpu(
                ssh_keys=data.get("ssh_keys", []),
                email_enabled=data.get("email_enabled", True),
                duration_hours=data.get("duration_hours", 24),
            )
            db.session.add(rental_gpu)
        else:
            # Otherwise just assign the GPU to the cluster
            cluster.current_gpu_id = gpu_listing.id
            print(cluster.to_dict())
        db.session.commit()
        return jsonify(cluster.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error in add_gpu_to_cluster: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:cluster_id>/gpu/deploy", methods=["POST"])
@require_auth()
def deploy_cluster_gpu(cluster_id):
    """Deploy a GPU to a cluster"""
    try:
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        cluster = Cluster.query.get(cluster_id)
        if not cluster:
            return jsonify({"error": "Cluster not found"}), 404

        if cluster.user_id != user.id:
            return jsonify({"error": "Unauthorized"}), 403

        # Check if there's already an active rental
        active_rental = cluster.active_rental
        if active_rental:
            if not active_rental.ssh_keys:
                # No instance was created, so we can safely delete this rental
                db.session.delete(active_rental)
                db.session.commit()
            else:
                return jsonify({"error": "Cluster already has an active GPU"}), 400

        # Get GPU configuration from cluster
        gpu_config = cluster.current_gpu
        if not gpu_config:
            return jsonify({"error": "No GPU configured in cluster"}), 400

        gpu = GPUListing.query.get(gpu_config.id)
        if not gpu:
            return jsonify({"error": "GPU not found"}), 404

        data = request.get_json() or {}
        duration_hours = data.get("duration_hours", 24)

        # Calculate costs
        base_cost = Decimal(str(gpu.current_price)) * Decimal(str(duration_hours))
        tax_rate = Decimal('0.08')  # 8% tax
        platform_fee_rate = Decimal('0.05')  # 5% platform fee
        
        tax_amount = base_cost * tax_rate
        platform_fee_amount = base_cost * platform_fee_rate
        total_cost = float(base_cost + tax_amount + platform_fee_amount)

        # Check if user has sufficient balance
        if user.balance < total_cost:
            return jsonify({
                "error": "Insufficient balance",
                "required_amount": total_cost,
                "current_balance": user.balance,
                "cost_breakdown": {
                    "base_cost": float(base_cost),
                    "tax_rate": float(tax_rate),
                    "tax_amount": float(tax_amount),
                    "platform_fee_rate": float(platform_fee_rate),
                    "platform_fee_amount": float(platform_fee_amount),
                    "total_cost": total_cost
                }
            }), 400

        rental_gpu = None
        try:
            # First, create and flush the rental GPU to get its ID
            rental_gpu = cluster.deploy_current_gpu(
                ssh_keys=[],  # Empty list since we'll add SSH keys after instance creation
                email_enabled=data.get("email_enabled", True),
                duration_hours=duration_hours,
                config=data.get("config", {})  # Store the full config
            )
            db.session.add(rental_gpu)
            db.session.flush()  # This assigns the ID without committing

            # Deploy AWS instance and get instance details
            try:
                instance_details = rental_gpu.deploy_aws_instance()
            except Exception as e:
                # If instance creation fails, delete the rental
                db.session.rollback()
                if rental_gpu.id:
                    db.session.delete(rental_gpu)
                    db.session.commit()
                raise e

            # Create and flush the transaction to get its ID
            transaction = Transaction(
                user_id=user.id,
                amount=-total_cost,  # Negative amount for a debit
                status="completed",
                description=f"GPU Rental: {gpu.configuration.gpu_name} for {duration_hours} hours"
            )
            db.session.add(transaction)
            db.session.flush()  # This assigns the ID without committing

            # Now we can create the deployment cost with valid IDs
            deployment_cost = DeploymentCost(
                rental_gpu_id=rental_gpu.id,  # Now we have this ID
                transaction_id=transaction.id,  # Now we have this ID
                base_cost=float(base_cost),
                tax_rate=float(tax_rate),
                tax_amount=float(tax_amount),
                platform_fee_rate=float(platform_fee_rate),
                platform_fee_amount=float(platform_fee_amount),
                total_cost=total_cost
            )
            db.session.add(deployment_cost)

            # Update user's balance
            user.balance -= total_cost
            
            # Now commit everything
            db.session.commit()

            return jsonify({
                "cluster": cluster.to_dict(),
                "cost_breakdown": deployment_cost.to_dict()
            }), 200

        except Exception as e:
            # If anything fails, make sure to clean up the rental
            db.session.rollback()
            if rental_gpu and rental_gpu.id:
                try:
                    db.session.delete(rental_gpu)
                    db.session.commit()
                except:
                    pass  # Ignore cleanup errors
            raise e

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Error in deploy_cluster_gpu: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:cluster_id>/gpu", methods=["DELETE"])
@require_auth()
def remove_gpu_from_cluster(cluster_id):
    """Remove the GPU from a cluster"""
    try:
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        cluster = Cluster.query.get(cluster_id)
        if not cluster:
            return jsonify({"error": "Cluster not found"}), 404

        if cluster.user_id != user.id:
            return jsonify({"error": "Unauthorized"}), 403

        active_rental = cluster.active_rental
        if not active_rental:
            return jsonify({"error": "No active GPU rental found"}), 404

        active_rental.status = "completed"
        active_rental.end_time = datetime.utcnow()
        db.session.commit()

        return jsonify(cluster.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error in remove_gpu_from_cluster: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:cluster_id>/history", methods=["GET"])
@require_auth()
def get_cluster_history(cluster_id):
    """Get rental history for a specific cluster"""
    try:
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        cluster = Cluster.query.filter_by(id=cluster_id, user_id=user.id).first()
        if not cluster:
            return jsonify({"error": "Cluster not found"}), 404

        rental_history = cluster.rental_history.order_by(
            RentalGPU.start_time.desc()
        ).all()
        return jsonify([rental.to_dict() for rental in rental_history]), 200

    except Exception as e:
        print(f"Error fetching cluster history: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:cluster_id>/gpu/ssh-key", methods=["GET"])
@require_auth()
def get_cluster_gpu_ssh_key(cluster_id):
    """Get SSH key for the cluster's GPU"""
    try:
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        cluster = Cluster.query.get(cluster_id)
        if not cluster:
            return jsonify({"error": "Cluster not found"}), 404

        if cluster.user_id != user.id:
            return jsonify({"error": "Unauthorized"}), 403

        # Check if there's an active rental
        active_rental = cluster.active_rental
        if not active_rental:
            return jsonify({"error": "No active GPU rental found"}), 400

        # Get SSH key and connection details
        try:
            ssh_details = active_rental.get_ssh_key()
            return jsonify({
                "message": "Retrieved SSH key successfully",
                **ssh_details
            }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    except Exception as e:
        print(f"Error in get_cluster_gpu_ssh_key: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:cluster_id>", methods=["DELETE"])
@require_auth()
def delete_cluster(cluster_id):
    """Delete a cluster if it has no active rentals"""
    try:
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        cluster = Cluster.query.get(cluster_id)
        if not cluster:
            return jsonify({"error": "Cluster not found"}), 404

        if cluster.user_id != user.id:
            return jsonify({"error": "Unauthorized"}), 403

        # Check if cluster has active rentals
        active_rental = cluster.active_rental
        if active_rental:
            return jsonify({"error": "Cannot delete cluster with active rentals"}), 400

        # Delete the cluster and its rental history
        db.session.delete(cluster)
        db.session.commit()

        return jsonify({"message": "Cluster deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error in delete_cluster: {str(e)}")
        return jsonify({"error": str(e)}), 500
