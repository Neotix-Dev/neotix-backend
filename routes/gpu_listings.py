from flask import Blueprint, jsonify, request
from sqlalchemy import or_, and_
import logging
from models.gpu_listing import GPUListing, Host, GPUPriceHistory, GPUPricePoint, GPUConfiguration
from utils.database import db
from datetime import datetime
from sqlalchemy import func

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bp = Blueprint("gpu", __name__, url_prefix="/api/gpu")


@bp.route("/get_all", methods=["GET"])
def get_all_gpus():
    try:
        listings = GPUListing.query.join(GPUConfiguration).all()
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
            import re
            match = re.search(r'\d+', query)
            if match:
                numeric_value = float(match.group())
        except:
            pass
            
        # Search across configuration and listing fields
        search_fields = [
            GPUConfiguration.gpu_name,
            GPUListing.instance_name,
            GPUConfiguration.gpu_vendor
        ]
        
        # Create search conditions for each field
        conditions = []
        for field in search_fields:
            conditions.append(field.ilike(f"%{query}%"))
            
        # Add numeric field conditions if numeric value found
        if numeric_value is not None:
            conditions.extend([
                GPUConfiguration.gpu_memory == numeric_value,
                GPUListing.current_price == numeric_value,
                GPUConfiguration.cpu == numeric_value,
                GPUConfiguration.memory == numeric_value
            ])
            
        # Calculate similarity scores for each field
        gpu_name_sim = func.similarity(GPUConfiguration.gpu_name, query)
        instance_name_sim = func.similarity(GPUListing.instance_name, query)
        gpu_vendor_sim = func.similarity(GPUConfiguration.gpu_vendor, query)
        
        # Calculate numeric field similarities
        gpu_memory_sim = func.abs(GPUConfiguration.gpu_memory - numeric_value) if numeric_value is not None else 0
        price_sim = func.abs(GPUListing.current_price - numeric_value) if numeric_value is not None else 0
        
        # Get results ordered by best match
        listings = GPUListing.query.join(GPUConfiguration).filter(
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
        listing = GPUListing.query.join(GPUConfiguration).get_or_404(id)
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
        per_page = 200
        
        paginated_listings = GPUListing.query.join(GPUConfiguration).order_by(
            GPUListing.id
        ).paginate(page=page_number, per_page=per_page, error_out=False)
        
        if not paginated_listings.items and page_number > 1:
            return jsonify({"error": "Page number exceeds available pages"}), 404
            
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
        logger.info("Received filter request")
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        
        logger.info(f"Request args: {dict(request.args)}")
        
        gpu_types = request.args.getlist("gpuTypes[]")
        providers = request.args.getlist("providers[]")
        vendors = request.args.getlist("vendors[]")
        min_price = request.args.get("price.min", type=float)
        max_price = request.args.get("price.max", type=float)
        min_cpu = request.args.get("cpu.min", type=int)
        max_cpu = request.args.get("cpu.max", type=int)
        min_memory = request.args.get("memory.min", type=float)
        max_memory = request.args.get("memory.max", type=float)
        
        min_vram = request.args.get("vram.min", type=float)
        if min_vram is None:
            min_vram = request.args.get("gpu_memory.min", type=float)
        
        max_vram = request.args.get("vram.max", type=float)
        if max_vram is None:
            max_vram = request.args.get("gpu_memory.max", type=float)
            
        gpu_count = request.args.get("gpuCount", type=int)
        search = request.args.get("search", "").strip()

        logger.info("Parsed filter values: %s", {
            'min_vram': min_vram,
            'max_vram': max_vram,
            'min_cpu': min_cpu,
            'max_cpu': max_cpu,
            'min_memory': min_memory,
            'max_memory': max_memory,
            'min_price': min_price,
            'max_price': max_price,
            'gpu_types': gpu_types,
            'providers': providers,
            'vendors': vendors,
            'gpu_count': gpu_count,
            'search': search
        })

        # Start with base query
        query = GPUListing.query.join(GPUConfiguration).join(Host)

        # Apply filters
        if gpu_types:
            query = query.filter(GPUConfiguration.gpu_name.in_(gpu_types))
            
        if providers:
            query = query.filter(Host.name.in_(providers))
            
        if vendors:
            query = query.filter(GPUConfiguration.gpu_vendor.in_(vendors))
            
        if min_price is not None:
            query = query.filter(GPUListing.current_price >= min_price)
            
        if max_price is not None:
            query = query.filter(GPUListing.current_price <= max_price)
            
        if min_cpu is not None:
            query = query.filter(GPUConfiguration.cpu >= min_cpu)
            
        if max_cpu is not None:
            query = query.filter(GPUConfiguration.cpu <= max_cpu)
            
        if min_memory is not None:
            query = query.filter(GPUConfiguration.memory >= min_memory)
            
        if max_memory is not None:
            query = query.filter(GPUConfiguration.memory <= max_memory)
            
        if min_vram is not None:
            query = query.filter(GPUConfiguration.gpu_memory >= min_vram)
            
        if max_vram is not None:
            query = query.filter(GPUConfiguration.gpu_memory <= max_vram)
            
        if gpu_count is not None:
            query = query.filter(GPUConfiguration.gpu_count == gpu_count)
            
        if search:
            search_conditions = [
                GPUConfiguration.gpu_name.ilike(f"%{search}%"),
                GPUListing.instance_name.ilike(f"%{search}%"),
                GPUConfiguration.gpu_vendor.ilike(f"%{search}%"),
                Host.name.ilike(f"%{search}%")
            ]
            query = query.filter(or_(*search_conditions))

        # Get total count before pagination
        total_count = query.count()
        
        # Apply pagination
        paginated_query = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'gpus': [gpu.to_dict() for gpu in paginated_query.items],
            'total': total_count,
            'page': page,
            'pages': (total_count + per_page - 1) // per_page
        })
        
    except Exception as e:
        logger.error(f"Error in filtered GPUs: {str(e)}")
        return jsonify({"error": "Failed to fetch filtered GPUs"}), 500


@bp.route("/vendors", methods=["GET"])
def get_gpu_vendors():
    try:
        vendors = db.session.query(GPUConfiguration.gpu_vendor).distinct().all()
        return jsonify([vendor[0] for vendor in vendors if vendor[0]])
    except Exception as e:
        print(f"Error fetching GPU vendors: {str(e)}")
        return jsonify({"error": "Failed to fetch GPU vendors"}), 500


@bp.route("/gpu_types", methods=["GET"])
def get_gpu_types():
    try:
        types = db.session.query(GPUConfiguration.gpu_name).distinct().all()
        return jsonify([type[0] for type in types if type[0]])
    except Exception as e:
        print(f"Error fetching GPU types: {str(e)}")
        return jsonify({"error": "Failed to fetch GPU types"}), 500


@bp.route("/<int:gpu_id>/price_history", methods=["GET"])
def get_gpu_price_history(gpu_id):
    try:
        # Get the GPU listing and its configuration
        listing = GPUListing.query.get_or_404(gpu_id)
        config_id = listing.configuration_id
        
        # Get price history for all listings with the same configuration
        history = GPUPriceHistory.query.filter_by(
            configuration_id=config_id
        ).order_by(GPUPriceHistory.date.desc()).all()
        
        # Group price history by date for the chart
        price_by_date = {}
        for record in history:
            date_str = record.date.strftime('%Y-%m-%d')
            if date_str not in price_by_date:
                price_by_date[date_str] = []
            price_by_date[date_str].append({
                'price': record.price,
                'location': record.location,
                'spot': record.spot
            })
        
        # Calculate average price for each date
        chart_data = []
        for date_str, prices in price_by_date.items():
            avg_price = sum(p['price'] for p in prices) / len(prices)
            chart_data.append({
                'date': date_str,
                'price': avg_price,
                'details': prices
            })
        
        # Sort by date
        chart_data.sort(key=lambda x: x['date'])
        
        return jsonify(chart_data)
    except Exception as e:
        print(f"Error fetching price history for GPU {gpu_id}: {str(e)}")
        return jsonify({"error": f"Failed to fetch price history for GPU {gpu_id}"}), 500


@bp.route("/<int:gpu_id>/price_points", methods=["GET"])
def get_gpu_price_points(gpu_id):
    try:
        points = GPUPricePoint.query.filter_by(gpu_listing_id=gpu_id).all()
        return jsonify([point.to_dict() for point in points])
    except Exception as e:
        print(f"Error fetching price points for GPU {gpu_id}: {str(e)}")
        return jsonify({"error": f"Failed to fetch price points for GPU {gpu_id}"}), 500
