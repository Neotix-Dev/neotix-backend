from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from models.gpu_listing import GPUListing, Host, GPUPricePoint, GPUConfiguration
from models.api_key import APIKey, APIKeyPermission
from models.user import User
from models.transaction import Transaction
from models.cluster import Cluster
from models.rental_gpu import RentalGPU
from utils.database import db
from utils.api_auth import require_api_key, require_admin_key, generate_api_key, get_user_from_key
from sqlalchemy import func, desc, and_
from flask_cors import cross_origin
import pytz

bp = Blueprint('api', __name__)

def get_current_est_time():
    est = pytz.timezone('US/Eastern')
    return datetime.now(est)

# Public Routes
@bp.route('/v1/market/overview', methods=['GET'])
@cross_origin()
def get_market_overview():
    """Get a high-level overview of the GPU market."""
    try:
        # Use the actual configuration relationship and column
        total_gpus = db.session.query(
            func.sum(GPUConfiguration.gpu_count)
        ).join(
            GPUListing, GPUListing.configuration_id == GPUConfiguration.id
        ).scalar() or 0
        
        # Query vendor info using configuration relationship
        vendor_prices = db.session.query(
            GPUConfiguration.gpu_vendor,
            func.avg(GPUListing.current_price).label('avg_price'),
            func.count().label('count')
        ).join(
            GPUListing, GPUListing.configuration_id == GPUConfiguration.id
        ).group_by(GPUConfiguration.gpu_vendor).all()
        
        response = {
            'timestamp': get_current_est_time().isoformat(),
            'total_gpus_available': total_gpus,
            'vendor_statistics': [
                {
                    'vendor': vendor,
                    'average_price': float(avg_price),
                    'available_instances': count
                }
                for vendor, avg_price, count in vendor_prices if vendor
            ]
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Protected Routes - Require API Key
@bp.route('/v1/market/gpu-prices', methods=['GET'])
@cross_origin()
@require_api_key
def get_gpu_prices():
    """Get real-time market data for all cloud GPU providers."""
    try:
        vendor = request.args.get('vendor')
        min_memory = request.args.get('min_memory', type=float)
        max_price = request.args.get('max_price', type=float)
        location = request.args.get('location')
        
        query = db.session.query(GPUListing).join(Host)
        
        if vendor:
            query = query.filter(GPUListing.gpu_vendor == vendor)
        if min_memory:
            query = query.filter(GPUListing.gpu_memory >= min_memory)
        if max_price:
            query = query.filter(GPUListing.current_price <= max_price)
            
        if location:
            query = query.join(GPUPricePoint).filter(GPUPricePoint.location.ilike(f'%{location}%'))
        
        listings = query.all()
        
        providers = {}
        for listing in listings:
            if listing.host.name not in providers:
                providers[listing.host.name] = []
                
            price_points = [
                {
                    'price': float(pp.price),
                    'location': pp.location,
                    'type': 'spot' if pp.spot else 'on-demand'
                }
                for pp in listing.price_points
            ]
            
            providers[listing.host.name].append({
                'model': listing.gpu_name,
                'vendor': listing.gpu_vendor,
                'memory': float(listing.gpu_memory) if listing.gpu_memory is not None else None,
                'count': listing.gpu_count,
                'score': float(listing.gpu_score) if listing.gpu_score is not None else None,
                'base_price': float(listing.current_price),
                'price_points': price_points,
                'specs': {
                    'cpu_cores': listing.cpu,
                    'ram_gb': float(listing.memory) if listing.memory is not None else None,
                    'disk_gb': float(listing.disk_size) if listing.disk_size is not None else None
                },
                'last_updated': listing.last_updated.isoformat()
            })
        
        response = {
            'timestamp': get_current_est_time().isoformat(),
            'providers': [
                {
                    'name': provider,
                    'gpus': gpus
                }
                for provider, gpus in providers.items()
            ]
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/v1/market/provider/<provider>/gpu-prices', methods=['GET'])
@cross_origin()
@require_api_key
def get_provider_gpu_prices(provider):
    """Get real-time market data for a specific cloud GPU provider."""
    try:
        host = Host.query.filter(func.lower(Host.name) == func.lower(provider)).first()
        if not host:
            return jsonify({
                'error': f'Provider not found: {provider}'
            }), 404
            
        listings = GPUListing.query.filter_by(host_id=host.id).all()
        
        gpus = []
        for listing in listings:
            gpus.append({
                'model': listing.gpu_name,
                'vendor': listing.gpu_vendor,
                'memory': float(listing.gpu_memory) if listing.gpu_memory is not None else None,
                'count': listing.gpu_count,
                'score': float(listing.gpu_score) if listing.gpu_score is not None else None,
                'base_price': float(listing.current_price),
                'price_points': [
                    {
                        'price': float(pp.price),
                        'location': pp.location,
                        'type': 'spot' if pp.spot else 'on-demand'
                    }
                    for pp in listing.price_points
                ],
                'specs': {
                    'cpu_cores': listing.cpu,
                    'ram_gb': float(listing.memory) if listing.memory is not None else None,
                    'disk_gb': float(listing.disk_size) if listing.disk_size is not None else None
                },
                'last_updated': listing.last_updated.isoformat()
            })
        
        response = {
            'timestamp': get_current_est_time().isoformat(),
            'provider': provider,
            'gpus': gpus
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/v1/market/gpu/<model>/prices', methods=['GET'])
@cross_origin()
@require_api_key
def get_gpu_model_prices(model):
    """Get price comparison for a specific GPU model across providers."""
    try:
        listings = GPUListing.query.filter(
            GPUListing.gpu_name.ilike(f'%{model}%')
        ).join(Host).all()
        
        if not listings:
            return jsonify({
                'error': f'No listings found for GPU model: {model}'
            }), 404
        
        providers = []
        for listing in listings:
            providers.append({
                'provider': listing.host.name,
                'instance_name': listing.instance_name,
                'gpu_count': listing.gpu_count,
                'base_price': float(listing.current_price),
                'price_per_gpu': float(listing.current_price) / listing.gpu_count,
                'price_points': [
                    {
                        'price': float(pp.price),
                        'location': pp.location,
                        'type': 'spot' if pp.spot else 'on-demand'
                    }
                    for pp in listing.price_points
                ],
                'specs': {
                    'cpu_cores': listing.cpu,
                    'ram_gb': float(listing.memory) if listing.memory is not None else None,
                    'disk_gb': float(listing.disk_size) if listing.disk_size is not None else None
                }
            })
        
        response = {
            'timestamp': get_current_est_time().isoformat(),
            'gpu_model': model,
            'providers': sorted(providers, key=lambda x: x['price_per_gpu'])
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# GPU Listing Routes
@bp.route('/gpu/filtered', methods=['GET'])
@cross_origin()
def get_gpu_listings():
    """Get filtered GPU listings."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Build query with optional filters
        query = GPUListing.query.join(GPUConfiguration, GPUListing.configuration_id == GPUConfiguration.id)
        
        # Apply filters
        vendor = request.args.get('vendor')
        if vendor:
            query = query.filter(GPUConfiguration.gpu_vendor == vendor)
            
        min_memory = request.args.get('min_memory', type=float)
        if min_memory:
            query = query.filter(GPUConfiguration.gpu_memory >= min_memory)
            
        max_price = request.args.get('max_price', type=float)
        if max_price:
            query = query.filter(GPUListing.current_price <= max_price)
            
        # Handle pagination
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        result = {
            'gpus': [listing.to_dict() for listing in paginated.items],
            'page': page,
            'pages': paginated.pages,
            'total': paginated.total
        }
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/gpu/<int:gpu_id>', methods=['GET'])
@cross_origin()
def get_gpu_details(gpu_id):
    """Get detailed information about a specific GPU listing."""
    try:
        # Use filter_by().first() instead of get() or get_or_404 to avoid the error with existing criterion
        gpu_listing = GPUListing.query.filter_by(id=gpu_id).first()
        if not gpu_listing:
            return jsonify({'error': f'GPU listing with id {gpu_id} not found'}), 404
            
        result = gpu_listing.to_dict()
        # Add price points if available
        result['price_points'] = [pp.to_dict() for pp in gpu_listing.price_points]
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# # Cluster Routes
# @bp.route('/clusters/', methods=['GET'])
# @cross_origin()
# def get_user_clusters():
#     """Get all clusters belonging to the authenticated user."""
#     try:
#         # Get the authorization header
#         auth_header = request.headers.get('X-API-Key')
#         if not auth_header:
#             return jsonify({'error': 'No authorization header'}), 401
            
#         # Get user from API key
#         user = get_user_from_key(auth_header)
#         if not user:
#             return jsonify({'error': 'Invalid API key'}), 401
            
#         # Get user's clusters
#         clusters = Cluster.query.filter_by(user_id=user.id).all()
#         result = [cluster.to_dict() for cluster in clusters]
        
#         return jsonify(result), 200
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @bp.route('/clusters-status/', methods=['GET'])
# @cross_origin()
# def get_clusters_status():
#     """Get status of all clusters for the authenticated user."""
#     try:
#         # Get the authorization header
#         auth_header = request.headers.get('X-API-Key')
#         if not auth_header:
#             return jsonify({'error': 'No authorization header'}), 401
            
#         # Get user from API key
#         user = get_user_from_key(auth_header)
#         if not user:
#             return jsonify({'error': 'Invalid API key'}), 401
            
#         # Get user's clusters with status
#         clusters = Cluster.query.filter_by(user_id=user.id).all()
#         result = [
#             {
#                 'id': cluster.id,
#                 'name': cluster.name,
#                 'status': cluster.status,
#                 'created_at': cluster.created_at.isoformat() if cluster.created_at else None,
#                 'gpus': [{
#                     'id': gpu.id,
#                     'status': gpu.status,
#                     'start_time': gpu.start_time.isoformat() if gpu.start_time else None,
#                     'is_active': gpu.is_active
#                 } for gpu in cluster.gpus]
#             } for cluster in clusters
#         ]
        
#         return jsonify(result), 200
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# # User Routes
# @bp.route('/user/balance', methods=['GET'])
# @cross_origin()
# def get_user_balance():
#     """Get the current balance for the authenticated user."""
#     try:
#         # Get the authorization header
#         auth_header = request.headers.get('X-API-Key')
#         if not auth_header:
#             return jsonify({'error': 'No authorization header'}), 401
            
#         # Get user from API key
#         user = get_user_from_key(auth_header)
#         if not user:
#             return jsonify({'error': 'Invalid API key'}), 401
            
#         # Get current month's transactions for usage calculation
#         now = datetime.now()
#         start_of_month = datetime(now.year, now.month, 1, tzinfo=now.tzinfo)
        
#         # Calculate total spent this month
#         monthly_transactions = Transaction.query.filter(
#             Transaction.user_id == user.id,
#             Transaction.created_at >= start_of_month,
#             Transaction.amount < 0  # Negative amounts are expenses
#         ).all()
        
#         monthly_usage = sum(abs(t.amount) for t in monthly_transactions)
        
#         result = {
#             'balance': user.balance,
#             'currency': 'USD',
#             'monthly_usage': monthly_usage
#         }
        
#         return jsonify(result), 200
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# API Key Management Routes
@bp.route('/v1/keys', methods=['POST'])
@cross_origin()
@require_admin_key  # Only admin/master can create keys
def create_api_key():
    """Create a new API key."""
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({
                'error': 'Missing required fields',
                'message': 'Please provide a name for the API key'
            }), 400
        
        # Default to READ permission unless specified
        permission = APIKeyPermission.READ
        if data.get('permission') == 'admin':
            permission = APIKeyPermission.ADMIN
            
        key = generate_api_key()
        api_key = APIKey(key=key, name=data['name'], permission=permission)
        db.session.add(api_key)
        db.session.commit()
        
        return jsonify(api_key.to_dict()), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/v1/keys', methods=['GET'])
@cross_origin()
@require_admin_key  # Only admin/master can list keys
def list_api_keys():
    """List all API keys."""
    try:
        keys = APIKey.query.all()
        return jsonify([
            {
                'id': k.id,
                'name': k.name,
                'permission': k.permission,
                'created_at': k.created_at.isoformat(),
                'last_used_at': k.last_used_at.isoformat() if k.last_used_at else None,
                'is_active': k.is_active
            }
            for k in keys
        ]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/v1/keys/<int:key_id>', methods=['DELETE'])
@cross_origin()
@require_admin_key  # Only admin/master can delete keys
def delete_api_key(key_id):
    """Delete (deactivate) an API key."""
    try:
        key = APIKey.query.get(key_id)
        if not key:
            return jsonify({
                'error': 'Key not found',
                'message': f'No API key found with ID {key_id}'
            }), 404
            
        key.is_active = False
        db.session.commit()
        
        return '', 204
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
