from flask import Blueprint, jsonify, request
from models.gpu_listing import GPUListing, Host, GPUPriceHistory, GPUPricePoint
from utils.database import db
from datetime import datetime
from sqlalchemy import func, or_

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
        query = request.args.get("q", "").strip()
        if not query:
            return jsonify([])
            
        # Try to extract numeric value from query
        numeric_value = None
        try:
            # Extract first number from query string
            import re
            match = re.search(r'\d+', query)
            if match:
                numeric_value = float(match.group())
        except:
            pass
            
        # Search across multiple fields with ranking
        search_fields = [
            GPUListing.gpu_name,
            GPUListing.instance_name,
            GPUListing.gpu_vendor
        ]
        
        # Create search conditions for each field
        conditions = []
        for field in search_fields:
            conditions.append(field.ilike(f"%{query}%"))
            
        # Add numeric field conditions if numeric value found
        if numeric_value is not None:
            conditions.extend([
                GPUListing.gpu_memory == numeric_value,
                GPUListing.current_price == numeric_value,
                GPUListing.cpu == numeric_value,
                GPUListing.memory == numeric_value
            ])
            
        # Enable fuzzy search using pg_trgm similarity
        from sqlalchemy import func
        
        # Calculate similarity scores for each field
        gpu_name_sim = func.similarity(GPUListing.gpu_name, query)
        instance_name_sim = func.similarity(GPUListing.instance_name, query)
        gpu_vendor_sim = func.similarity(GPUListing.gpu_vendor, query)
        
        # Calculate numeric field similarities
        gpu_memory_sim = func.abs(GPUListing.gpu_memory - numeric_value) if numeric_value is not None else 0
        price_sim = func.abs(GPUListing.current_price - numeric_value) if numeric_value is not None else 0
        
        # Get results ordered by best match
        listings = GPUListing.query.filter(
            db.or_(*conditions)
        ).order_by(
            db.desc(gpu_name_sim),
            db.desc(instance_name_sim),
            db.desc(gpu_vendor_sim),
            *(
                [db.desc(-gpu_memory_sim), db.desc(-price_sim)]
                if numeric_value is not None
                else []
            )
        ).limit(50).all()
        
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
        hosts = Host.query.with_entities(Host.name).distinct().all()
        return jsonify([host[0] for host in hosts])
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


@bp.route("/filtered", methods=["GET"])
def get_filtered_gpus():
    try:
        # Get query parameters
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        
        # Get filter parameters
        gpu_types = request.args.getlist("gpuTypes[]")
        providers = request.args.getlist("providers[]")
        vendors = request.args.getlist("vendors[]")
        min_price = request.args.get("price.min", type=float)
        max_price = request.args.get("price.max", type=float)
        min_cpu = request.args.get("cpu.min", type=float)
        max_cpu = request.args.get("cpu.max", type=float)
        min_memory = request.args.get("memory.min", type=float)
        max_memory = request.args.get("memory.max", type=float)
        min_gpu_memory = request.args.get("gpu_memory.min", type=float)
        max_gpu_memory = request.args.get("gpu_memory.max", type=float)
        search = request.args.get("search", "").strip()

        # Start with base query
        query = GPUListing.query.join(Host)

        # Apply filters
        if gpu_types:
            query = query.filter(GPUListing.gpu_name.in_(gpu_types))
        
        if providers:
            query = query.filter(Host.name.in_(providers))
            
        if vendors:
            query = query.filter(GPUListing.gpu_vendor.in_(vendors))
            
        if min_price is not None:
            query = query.filter(GPUListing.current_price >= min_price)
            
        if max_price is not None:
            query = query.filter(GPUListing.current_price <= max_price)

        # Apply CPU cores filter
        if min_cpu is not None:
            query = query.filter(GPUListing.cpu >= min_cpu)
            
        if max_cpu is not None:
            query = query.filter(GPUListing.cpu <= max_cpu)

        # Apply memory filter
        if min_memory is not None:
            query = query.filter(GPUListing.memory >= min_memory)
            
        if max_memory is not None:
            query = query.filter(GPUListing.memory <= max_memory)

        # Apply GPU memory filter
        if min_gpu_memory is not None:
            query = query.filter(GPUListing.gpu_memory >= min_gpu_memory)
            
        if max_gpu_memory is not None:
            query = query.filter(GPUListing.gpu_memory <= max_gpu_memory)
            
        if search:
            search_filter = or_(
                GPUListing.gpu_name.ilike(f"%{search}%"),
                Host.name.ilike(f"%{search}%"),
                GPUListing.gpu_vendor.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)

        # Get total count for pagination
        total_count = query.count()
        total_pages = (total_count + per_page - 1) // per_page

        # Apply pagination
        query = query.order_by(GPUListing.current_price.asc())
        query = query.offset((page - 1) * per_page).limit(per_page)

        # Execute query and format results
        gpus = query.all()
        results = []
        for gpu in gpus:
            gpu_dict = gpu.to_dict()
            gpu_dict['provider'] = gpu.host.name if gpu.host else None
            gpu_dict['provider_url'] = gpu.host.url if gpu.host else None
            results.append(gpu_dict)

        return jsonify({
            "gpus": results,
            "total_pages": total_pages,
            "current_page": page,
            "total_gpus": total_count,
            "gpus_per_page": per_page
        })

    except Exception as e:
        print(f"Error in filtered GPUs: {str(e)}")
        return jsonify({"error": "Failed to fetch filtered GPUs"}), 500


@bp.route("/vendors", methods=["GET"])
def get_gpu_vendors():
    try:
        vendors = GPUListing.query.with_entities(GPUListing.gpu_vendor).distinct().all()
        return jsonify([vendor[0] for vendor in vendors if vendor[0]])
    except Exception as e:
        print(f"Error fetching GPU vendors: {str(e)}")
        return jsonify({"error": "Failed to fetch GPU vendors"}), 500


@bp.route("/gpu_types", methods=["GET"])
def get_gpu_types():
    try:
        gpu_types = GPUListing.query.with_entities(GPUListing.gpu_name).distinct().all()
        return jsonify([gpu_type[0] for gpu_type in gpu_types if gpu_type[0]])
    except Exception as e:
        print(f"Error fetching GPU types: {str(e)}")
        return jsonify({"error": "Failed to fetch GPU types"}), 500


@bp.route("/<int:gpu_id>/price-history", methods=["GET"])
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


@bp.route("/<int:gpu_id>/price-points", methods=["GET"])
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
