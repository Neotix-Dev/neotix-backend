from flask import Blueprint, jsonify, request
from models.gpu_listing import GPUListing, Host, GPUPriceHistory, GPUPricePoint
from utils.database import db
from datetime import datetime

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


@bp.route("/get_gpus/<int:page_number>", methods=["GET"])
def get_paginated_gpus(page_number):
    try:
        # Calculate pagination parameters
        per_page = 200
        
        # Get paginated results
        paginated_listings = GPUListing.query.order_by(GPUListing.id).paginate(
            page=page_number, per_page=per_page, error_out=False
        )
        
        if not paginated_listings.items and page_number > 1:
            return jsonify({"error": "Page number exceeds available pages"}), 404
            
        # Calculate total pages
        total_gpus = GPUListing.query.count()
        total_pages = (total_gpus + per_page - 1) // per_page
        
        return jsonify({
            "gpus": [listing.to_dict() for listing in paginated_listings.items],
            "current_page": page_number,
            "total_pages": total_pages,
            "total_gpus": total_gpus,
            "gpus_per_page": per_page
        })
    except Exception as e:
        print(f"Error fetching GPUs for page {page_number}: {str(e)}")
        return jsonify({"error": f"Failed to fetch GPUs for page {page_number}"}), 500


@bp.route("/api/gpu/filtered", methods=["GET"])
def get_filtered_gpus():
    try:
        # Get query parameters with defaults
        gpu_name = request.args.get("gpu_name")
        gpu_vendor = request.args.get("gpu_vendor")
        min_gpu_count = request.args.get("min_gpu_count", type=int)
        max_gpu_count = request.args.get("max_gpu_count", type=int)
        min_gpu_memory = request.args.get("min_gpu_memory", type=float)
        max_gpu_memory = request.args.get("max_gpu_memory", type=float)
        min_cpu = request.args.get("min_cpu", type=int)
        max_cpu = request.args.get("max_cpu", type=int)
        min_memory = request.args.get("min_memory", type=float)
        max_memory = request.args.get("max_memory", type=float)
        min_price = request.args.get("min_price", type=float)
        max_price = request.args.get("max_price", type=float)
        provider = request.args.get("provider")
        sort_by = request.args.get("sort_by", "current_price")
        sort_order = request.args.get("sort_order", "asc")
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)

        # Start with base query
        query = GPUListing.query

        # Apply filters
        if gpu_name:
            query = query.filter(GPUListing.gpu_name.ilike(f"%{gpu_name}%"))
        if gpu_vendor:
            query = query.filter(GPUListing.gpu_vendor == gpu_vendor)
        if min_gpu_count is not None:
            query = query.filter(GPUListing.gpu_count >= min_gpu_count)
        if max_gpu_count is not None:
            query = query.filter(GPUListing.gpu_count <= max_gpu_count)
        if min_gpu_memory is not None:
            query = query.filter(GPUListing.gpu_memory >= min_gpu_memory)
        if max_gpu_memory is not None:
            query = query.filter(GPUListing.gpu_memory <= max_gpu_memory)
        if min_cpu is not None:
            query = query.filter(GPUListing.cpu >= min_cpu)
        if max_cpu is not None:
            query = query.filter(GPUListing.cpu <= max_cpu)
        if min_memory is not None:
            query = query.filter(GPUListing.memory >= min_memory)
        if max_memory is not None:
            query = query.filter(GPUListing.memory <= max_memory)
        if min_price is not None:
            query = query.filter(GPUListing.current_price >= min_price)
        if max_price is not None:
            query = query.filter(GPUListing.current_price <= max_price)
        if provider:
            query = query.join(Host).filter(Host.name == provider)

        # Apply sorting
        sort_column = getattr(GPUListing, sort_by, GPUListing.current_price)
        if sort_order == "desc":
            sort_column = sort_column.desc()
        query = query.order_by(sort_column)

        # Apply pagination
        paginated_listings = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            "gpus": [listing.to_dict() for listing in paginated_listings.items],
            "current_page": page,
            "total_pages": paginated_listings.pages,
            "total_items": paginated_listings.total,
            "items_per_page": per_page
        })

    except Exception as e:
        print(f"Error filtering GPUs: {str(e)}")
        return jsonify({"error": "Failed to filter GPUs"}), 500


@bp.route("/api/gpu/vendors", methods=["GET"])
def get_gpu_vendors():
    try:
        vendors = db.session.query(GPUListing.gpu_vendor).distinct().all()
        # Extract vendors from tuples and filter out None values
        vendor_list = [vendor[0] for vendor in vendors if vendor[0] is not None]
        return jsonify(vendor_list)
    except Exception as e:
        print(f"Error fetching GPU vendors: {str(e)}")
        return jsonify({"error": "Failed to fetch GPU vendors"}), 500


@bp.route("/api/gpu/<int:gpu_id>/price-history", methods=["GET"])
def get_gpu_price_history(gpu_id):
    try:
        # Get query parameters
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        # Start with base query
        query = GPUPriceHistory.query.filter(GPUPriceHistory.gpu_listing_id == gpu_id)

        # Apply date filters if provided
        if start_date:
            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(GPUPriceHistory.date >= start_datetime)
        if end_date:
            end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(GPUPriceHistory.date <= end_datetime)

        # Order by date
        query = query.order_by(GPUPriceHistory.date)

        # Execute query and convert to dict
        price_history = query.all()
        return jsonify([price.to_dict() for price in price_history])

    except ValueError as e:
        print(f"Invalid date format: {str(e)}")
        return jsonify({"error": "Invalid date format. Please use ISO format (YYYY-MM-DD)"}), 400
    except Exception as e:
        print(f"Error fetching price history for GPU {gpu_id}: {str(e)}")
        return jsonify({"error": f"Failed to fetch price history for GPU {gpu_id}"}), 500


@bp.route("/api/gpu/<int:gpu_id>/price-points", methods=["GET"])
def get_gpu_price_points(gpu_id):
    try:
        # Get all current price points for the GPU
        price_points = GPUPricePoint.query.filter(
            GPUPricePoint.gpu_listing_id == gpu_id
        ).order_by(
            GPUPricePoint.price
        ).all()

        return jsonify([price_point.to_dict() for price_point in price_points])

    except Exception as e:
        print(f"Error fetching price points for GPU {gpu_id}: {str(e)}")
        return jsonify({"error": f"Failed to fetch price points for GPU {gpu_id}"}), 500
