from flask import Blueprint, jsonify, g
from models.cluster import Cluster
from models.user import User
from models.transaction import Transaction
from models.deployment_cost import DeploymentCost
from middleware.auth import require_auth
from utils.database import db
from datetime import datetime
from decimal import Decimal

bp = Blueprint("clusters_status", __name__)


@bp.route("/", methods=["GET"])
@bp.route("", methods=["GET"])
@require_auth()
def get_all_clusters_status():
    """Get detailed real-time status for all clusters of the current user"""
    try:
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Get all clusters for the user
        clusters = Cluster.query.filter_by(user_id=user.id).all()
        
        response = {
            "timestamp": datetime.utcnow().isoformat(),
            "active_clusters_count": 0,
            "total_clusters_count": len(clusters),
            "total_current_cost": 0.0,
            "clusters": []
        }

        # Process each cluster for real-time status
        for cluster in clusters:
            # Calculate real-time metrics for active rentals
            cluster_data = {
                "id": cluster.id,
                "name": cluster.name,
                "description": cluster.description,
                "created_at": cluster.created_at.isoformat(),
                "is_active": False,
                "gpu_type": None,
                "running_time": None,
                "current_cost": None,
                "hourly_rate": None,
                "initial_deposit": None
            }
            
            # Check if the cluster has an active rental
            active_rental = cluster.active_rental
            if active_rental and active_rental.start_time:
                # Get the GPU details
                gpu = active_rental.gpu_listing
                if gpu:
                    cluster_data["gpu_type"] = gpu.configuration.gpu_name if gpu.configuration else "Unknown GPU"
                    cluster_data["gpu_vendor"] = gpu.gpu_vendor
                    cluster_data["hourly_rate"] = float(gpu.current_price)
                
                # Calculate running time in hours
                start_time = active_rental.start_time
                now = datetime.utcnow()
                running_seconds = (now - start_time).total_seconds()
                running_hours = running_seconds / 3600
                
                # Get initial deposit from deployment cost
                deployment_cost = DeploymentCost.query.filter_by(rental_gpu_id=active_rental.id).first()
                initial_deposit = 0.0
                if deployment_cost:
                    initial_deposit = deployment_cost.total_cost
                    transaction = Transaction.query.get(deployment_cost.transaction_id)
                    if transaction:
                        initial_deposit = abs(transaction.amount)
                
                # Calculate current cost based on running time and hourly rate
                hourly_rate = float(gpu.current_price) if gpu else 0.0
                current_cost = running_hours * hourly_rate
                
                # Apply tax and platform fee (same as in deployment)
                tax_rate = Decimal('0.08')  # 8% tax
                platform_fee_rate = Decimal('0.05')  # 5% platform fee
                
                base_cost = Decimal(str(current_cost))
                tax_amount = base_cost * tax_rate
                platform_fee_amount = base_cost * platform_fee_rate
                total_current_cost = float(base_cost + tax_amount + platform_fee_amount)
                
                # Update cluster data
                cluster_data["is_active"] = True
                cluster_data["start_time"] = start_time.isoformat()
                cluster_data["running_time_seconds"] = int(running_seconds)
                cluster_data["running_time_hours"] = round(running_hours, 2)
                cluster_data["current_cost"] = round(total_current_cost, 2)
                cluster_data["initial_deposit"] = round(initial_deposit, 2)
                cluster_data["additional_charges"] = round(max(0, total_current_cost - initial_deposit), 2)
                
                # Update totals
                response["active_clusters_count"] += 1
                response["total_current_cost"] += total_current_cost
            
            response["clusters"].append(cluster_data)
        
        # Sort clusters to show active ones first
        response["clusters"] = sorted(response["clusters"], key=lambda x: (not x["is_active"], x["name"]))
        response["total_current_cost"] = round(response["total_current_cost"], 2)
        
        return jsonify(response), 200

    except Exception as e:
        print(f"Error in get_all_clusters_status: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:cluster_id>", methods=["GET"])
@require_auth()
def get_cluster_status(cluster_id):
    """Get detailed real-time status for a specific cluster"""
    try:
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Get the specific cluster
        cluster = Cluster.query.get(cluster_id)
        if not cluster:
            return jsonify({"error": "Cluster not found"}), 404

        if cluster.user_id != user.id:
            return jsonify({"error": "Unauthorized"}), 403

        # Initialize the response
        response = {
            "timestamp": datetime.utcnow().isoformat(),
            "id": cluster.id,
            "name": cluster.name,
            "description": cluster.description,
            "created_at": cluster.created_at.isoformat(),
            "is_active": False,
            "gpu_type": None,
            "running_time": None,
            "current_cost": None,
            "hourly_rate": None,
            "initial_deposit": None
        }

        # Check if the cluster has an active rental
        active_rental = cluster.active_rental
        if active_rental and active_rental.start_time:
            # Get the GPU details
            gpu = active_rental.gpu_listing
            if gpu:
                response["gpu_type"] = gpu.configuration.gpu_name if gpu.configuration else "Unknown GPU"
                response["gpu_vendor"] = gpu.gpu_vendor
                response["hourly_rate"] = float(gpu.current_price)
            
            # Calculate running time in hours
            start_time = active_rental.start_time
            now = datetime.utcnow()
            running_seconds = (now - start_time).total_seconds()
            running_hours = running_seconds / 3600
            
            # Get initial deposit from deployment cost
            deployment_cost = DeploymentCost.query.filter_by(rental_gpu_id=active_rental.id).first()
            initial_deposit = 0.0
            if deployment_cost:
                initial_deposit = deployment_cost.total_cost
                transaction = Transaction.query.get(deployment_cost.transaction_id)
                if transaction:
                    initial_deposit = abs(transaction.amount)
            
            # Calculate current cost based on running time and hourly rate
            hourly_rate = float(gpu.current_price) if gpu else 0.0
            current_cost = running_hours * hourly_rate
            
            # Apply tax and platform fee (same as in deployment)
            tax_rate = Decimal('0.08')  # 8% tax
            platform_fee_rate = Decimal('0.05')  # 5% platform fee
            
            base_cost = Decimal(str(current_cost))
            tax_amount = base_cost * tax_rate
            platform_fee_amount = base_cost * platform_fee_rate
            total_current_cost = float(base_cost + tax_amount + platform_fee_amount)
            
            # Update cluster data
            response["is_active"] = True
            response["start_time"] = start_time.isoformat()
            response["running_time_seconds"] = int(running_seconds)
            response["running_time_hours"] = round(running_hours, 2)
            response["current_cost"] = round(total_current_cost, 2)
            response["initial_deposit"] = round(initial_deposit, 2)
            response["additional_charges"] = round(max(0, total_current_cost - initial_deposit), 2)
            response["instance_id"] = active_rental.instance_id
            response["rental_id"] = active_rental.id
        
        return jsonify(response), 200

    except Exception as e:
        print(f"Error in get_cluster_status: {str(e)}")
        return jsonify({"error": str(e)}), 500
