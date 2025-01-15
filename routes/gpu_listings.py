from flask import Blueprint, jsonify, request
from models.gpu_listing import GPUListing, Host
from utils.database import db

bp = Blueprint("gpu", __name__)


@bp.route("/get_all", methods=["GET"])
def get_all_gpus():
    try:
        listings = GPUListing.query.all()
        print(f"Found {len(listings)} GPU listings")
        result = [listing.to_dict() for listing in listings]
        print(f"Converted {len(result)} listings to dict")
        return jsonify(result)
    except Exception as e:
        print(f"Error fetching GPUs: {str(e)}")
        return jsonify({"error": "Failed to fetch GPUs"}), 500


@bp.route("/search", methods=["GET"])
def search_gpus():
    try:
        query = request.args.get("q", "")
        listings = GPUListing.query.filter(GPUListing.name.ilike(f"%{query}%")).all()
        return jsonify([listing.to_dict() for listing in listings])
    except Exception as e:
        print(f"Error searching GPUs: {str(e)}")
        return jsonify({"error": "Failed to search GPUs"}), 500


@bp.route("/<int:id>", methods=["GET"])
def get_gpu(id):
    try:
        listing = GPUListing.query.get_or_404(id)
        return jsonify(listing.to_dict())
    except Exception as e:
        print(f"Error fetching GPU {id}: {str(e)}")
        return jsonify({"error": f"Failed to fetch GPU {id}"}), 500


@bp.route("/hosts", methods=["GET"])
def get_hosts():
    try:
        hosts = Host.query.all()
        return jsonify([host.to_dict() for host in hosts])
    except Exception as e:
        print(f"Error fetching hosts: {str(e)}")
        return jsonify({"error": "Failed to fetch hosts"}), 500
