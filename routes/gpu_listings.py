from flask import Blueprint, jsonify, request
from sqlalchemy import or_, and_
import logging
from models.gpu_listing import (
    GPUListing,
    Host,
    GPUPriceHistory,
    GPUPricePoint,
    GPUConfiguration,
)
from utils.database import db
from datetime import datetime
from sqlalchemy import func
from utils.cache import memory_cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('gpu_listings.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

bp = Blueprint("gpu", __name__, url_prefix="/api/gpu")


@bp.route("/get_all", methods=["GET"])
@memory_cache(expiration=60)  # Cache for 1 minute
def get_all_gpus():
    try:
        logger.info("Starting get_all_gpus request")
        listings = GPUListing.query.join(GPUConfiguration).all()
        logger.info(f"Found {len(listings)} GPU listings")
        result = [listing.to_dict() for listing in listings]
        logger.info(f"Converted {len(result)} listings to dict")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_all_gpus: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@bp.route("/search", methods=["GET"])
def search_gpus():
    try:
        logger.info("Starting search_gpus request")
        query = request.args.get("q", "").strip()
        logger.info(f"Search query: {query}")
        
        if not query:
            logger.info("Empty query, returning empty result")
            return jsonify([])

        # Try to extract numeric value from query
        numeric_value = None
        try:
            import re

            match = re.search(r"\d+", query)
            if match:
                numeric_value = float(match.group())
                logger.info(f"Extracted numeric value: {numeric_value}")
        except Exception as e:
            logger.warning(f"Failed to extract numeric value: {str(e)}")
            

        # Search across configuration and listing fields
        search_fields = [
            GPUConfiguration.gpu_name,
            GPUListing.instance_name,
            GPUConfiguration.gpu_vendor,
        ]

        # Create search conditions for each field
        conditions = []
        for field in search_fields:
            conditions.append(field.ilike(f"%{query}%"))

        # Add numeric field conditions if numeric value found
        if numeric_value is not None:
            conditions.extend(
                [
                    GPUConfiguration.gpu_memory == numeric_value,
                    GPUListing.current_price == numeric_value,
                    GPUConfiguration.cpu == numeric_value,
                    GPUConfiguration.memory == numeric_value,
                ]
            )

        # Calculate similarity scores for each field
        gpu_name_sim = func.similarity(GPUConfiguration.gpu_name, query)
        instance_name_sim = func.similarity(GPUListing.instance_name, query)
        gpu_vendor_sim = func.similarity(GPUConfiguration.gpu_vendor, query)

        # Calculate numeric field similarities
        gpu_memory_sim = (
            func.abs(GPUConfiguration.gpu_memory - numeric_value)
            if numeric_value is not None
            else 0
        )
        price_sim = (
            func.abs(GPUListing.current_price - numeric_value)
            if numeric_value is not None
            else 0
        )

        # Get results ordered by best match
        # Get results with basic ordering
        listings = GPUListing.query.join(GPUConfiguration).filter(
            db.or_(*conditions)
        ).order_by(
            GPUConfiguration.gpu_score.desc()  # Order by GPU score instead of similarity
        ).limit(50).all()
        
        logger.info(f"Found {len(listings)} matching GPU listings")
        
        return jsonify([listing.to_dict() for listing in listings])
    except Exception as e:
        logger.error(f"Error in search_gpus: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:id>", methods=["GET"])
def get_gpu(id):
    try:
        logger.info(f"Starting get_gpu request for id {id}")
        listing = GPUListing.query.join(GPUConfiguration).get_or_404(id)
        logger.info(f"Found GPU listing with id {id}")
        return jsonify(listing.to_dict())
    except Exception as e:
        logger.error(f"Error in get_gpu: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@bp.route("/hosts", methods=["GET"])
def get_hosts():
    try:
        logger.info("Starting get_hosts request")
        hosts = Host.query.with_entities(Host.name).distinct().all()
        logger.info(f"Found {len(hosts)} unique hosts")
        return jsonify([host[0] for host in hosts])
    except Exception as e:
        logger.error(f"Error in get_hosts: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@bp.route("/get_gpus/<int:page_number>", methods=["GET"])
def get_paginated_gpus(page_number):
    try:
        logger.info(f"Starting get_paginated_gpus request for page {page_number}")
        per_page = 200

        paginated_listings = (
            GPUListing.query.join(GPUConfiguration)
            .order_by(GPUListing.id)
            .paginate(page=page_number, per_page=per_page, error_out=False)
        )

        if not paginated_listings.items and page_number > 1:
            logger.info(f"No GPU listings found for page {page_number}")
            return jsonify({"error": "Page number exceeds available pages"}), 404

        total_gpus = GPUListing.query.count()
        total_pages = (total_gpus + per_page - 1) // per_page
        
        logger.info(f"Found {len(paginated_listings.items)} GPU listings for page {page_number}")
        return jsonify({
            "gpus": [listing.to_dict() for listing in paginated_listings.items],
            "current_page": page_number,
            "total_pages": total_pages,
            "total_gpus": total_gpus,
            "gpus_per_page": per_page
        })

    except Exception as e:
        logger.error(f"Error in get_paginated_gpus: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@bp.route("/filtered", methods=["GET"])
def get_filtered_gpus():
    try:
        logger.info("Starting get_filtered_gpus request")
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

        logger.info(
            "Parsed filter values: %s",
            {
                "min_vram": min_vram,
                "max_vram": max_vram,
                "min_cpu": min_cpu,
                "max_cpu": max_cpu,
                "min_memory": min_memory,
                "max_memory": max_memory,
                "min_price": min_price,
                "max_price": max_price,
                "gpu_types": gpu_types,
                "providers": providers,
                "vendors": vendors,
                "gpu_count": gpu_count,
                "search": search,
            },
        )

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
                Host.name.ilike(f"%{search}%"),
            ]
            query = query.filter(or_(*search_conditions))

        # Get total count before pagination
        total_count = query.count()

        # Apply pagination
        paginated_query = query.paginate(page=page, per_page=per_page, error_out=False)
        
        logger.info(f"Found {len(paginated_query.items)} filtered GPU listings")
        return jsonify({
            'gpus': [gpu.to_dict() for gpu in paginated_query.items],
            'total': total_count,
            'page': page,
            'pages': (total_count + per_page - 1) // per_page
        })
        
    except Exception as e:
        logger.error(f"Error in get_filtered_gpus: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@bp.route("/vendors", methods=["GET"])
def get_gpu_vendors():
    try:
        logger.info("Starting get_gpu_vendors request")
        vendors = db.session.query(GPUConfiguration.gpu_vendor).distinct().all()
        logger.info(f"Found {len(vendors)} unique GPU vendors")
        return jsonify([vendor[0] for vendor in vendors if vendor[0]])
    except Exception as e:
        logger.error(f"Error in get_gpu_vendors: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@bp.route("/gpu_types", methods=["GET"])
def get_gpu_types():
    try:
        logger.info("Starting get_gpu_types request")
        types = db.session.query(GPUConfiguration.gpu_name).distinct().all()
        logger.info(f"Found {len(types)} unique GPU types")
        return jsonify([type[0] for type in types if type[0]])
    except Exception as e:
        logger.error(f"Error in get_gpu_types: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:gpu_id>/price_history", methods=["GET"])
def get_gpu_price_history(gpu_id):
    try:
        logger.info(f"Starting get_gpu_price_history request for GPU {gpu_id}")
        # Get the GPU listing and its configuration
        listing = GPUListing.query.get_or_404(gpu_id)
        config_id = listing.configuration_id

        # Get price history for all listings with the same configuration
        history = (
            GPUPriceHistory.query.filter_by(configuration_id=config_id)
            .order_by(GPUPriceHistory.date.desc())
            .all()
        )

        # Group price history by date for the chart
        price_by_date = {}
        for record in history:
            date_str = record.date.strftime("%Y-%m-%d")
            if date_str not in price_by_date:
                price_by_date[date_str] = []
            price_by_date[date_str].append(
                {
                    "price": record.price,
                    "location": record.location,
                    "spot": record.spot,
                }
            )

        # Calculate average price for each date
        chart_data = []
        for date_str, prices in price_by_date.items():
            avg_price = sum(p["price"] for p in prices) / len(prices)
            chart_data.append({"date": date_str, "price": avg_price, "details": prices})

        # Sort by date
        chart_data.sort(key=lambda x: x['date'])
        
        logger.info(f"Found {len(chart_data)} price history records for GPU {gpu_id}")
        return jsonify(chart_data)
    except Exception as e:
        logger.error(f"Error in get_gpu_price_history: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500



@bp.route("/<int:gpu_id>/price_points", methods=["GET"])
def get_gpu_price_points(gpu_id):
    try:
        logger.info(f"Starting get_gpu_price_points request for GPU {gpu_id}")
        points = GPUPricePoint.query.filter_by(gpu_listing_id=gpu_id).all()
        logger.info(f"Found {len(points)} price points for GPU {gpu_id}")
        return jsonify([point.to_dict() for point in points])
    except Exception as e:
        logger.error(f"Error in get_gpu_price_points: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500
