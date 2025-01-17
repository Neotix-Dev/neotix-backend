from flask import Blueprint, request, jsonify, g
from models.project import Project
from models.gpu_listing import GPUListing
from utils.database import db
from middleware.auth import require_auth
from models.user import User

bp = Blueprint("project", __name__)


@bp.route("/", methods=["GET"])
@require_auth()
def get_user_projects():
    """Get all projects for the current user"""
    try:
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found. Please sync your account."}), 404

        projects = Project.query.filter_by(user_id=user.id).all()
        return jsonify([project.to_dict() for project in projects]), 200
    except Exception as e:
        print(f"Error in get_user_projects: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:project_id>", methods=["GET"])
@require_auth()
def get_project(project_id):
    """Get a project"""
    try:
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found. Please sync your account."}), 404

        project = Project.query.filter_by(id=project_id, user_id=user.id).first()
        if not project:
            return jsonify({"error": "Project not found"}), 404
        return jsonify(project.to_dict()), 200
    except Exception as e:
        print(f"Error in get_project: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/", methods=["POST"])
@require_auth()
def create_project():
    """Create a new project"""
    try:
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found. Please sync your account."}), 404

        data = request.json
        if not data.get("name"):
            return jsonify({"error": "Project name is required"}), 400

        project = Project(
            name=data["name"],
            description=data.get("description", ""),
            user_id=user.id,
        )

        db.session.add(project)
        db.session.commit()

        return jsonify(project.to_dict()), 201
    except Exception as e:
        print(f"Error in create_project: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:project_id>", methods=["PUT"])
@require_auth()
def update_project(project_id):
    """Update a project"""
    try:
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found. Please sync your account."}), 404

        project = Project.query.filter_by(id=project_id, user_id=user.id).first()
        if not project:
            return jsonify({"error": "Project not found"}), 404

        data = request.json
        if "name" in data:
            project.name = data["name"]
        if "description" in data:
            project.description = data["description"]

        db.session.commit()
        return jsonify(project.to_dict()), 200
    except Exception as e:
        print(f"Error in update_project: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:project_id>", methods=["DELETE"])
@require_auth()
def delete_project(project_id):
    """Delete a project"""
    try:
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found. Please sync your account."}), 404

        project = Project.query.filter_by(id=project_id, user_id=user.id).first()
        if not project:
            return jsonify({"error": "Project not found"}), 404

        db.session.delete(project)
        db.session.commit()

        return jsonify({"message": "Project deleted successfully"}), 200
    except Exception as e:
        print(f"Error in delete_project: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:project_id>/gpus", methods=["POST"])
@require_auth()
def add_gpu_to_project(project_id):
    """Add a GPU to a project"""
    try:
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found. Please sync your account."}), 404

        project = Project.query.filter_by(id=project_id, user_id=user.id).first()
        if not project:
            return jsonify({"error": "Project not found"}), 404

        data = request.json
        if not data or not data.get("gpu_id"):
            return jsonify({"error": "GPU ID is required"}), 400

        gpu = GPUListing.query.get(data["gpu_id"])
        if not gpu:
            return jsonify({"error": "GPU not found"}), 404

        if gpu in project.gpus:
            return jsonify({"error": "GPU already in project"}), 400

        project.gpus.append(gpu)
        db.session.commit()

        return jsonify(project.to_dict()), 200
    except Exception as e:
        print(f"Error in add_gpu_to_project: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:project_id>/gpus/<int:gpu_id>", methods=["DELETE"])
@require_auth()
def remove_gpu_from_project(project_id, gpu_id):
    """Remove a GPU from a project"""
    try:
        user = User.query.filter_by(firebase_uid=g.user_id).first()
        if not user:
            return jsonify({"error": "User not found. Please sync your account."}), 404

        project = Project.query.filter_by(id=project_id, user_id=user.id).first()
        if not project:
            return jsonify({"error": "Project not found"}), 404

        gpu = GPUListing.query.get(gpu_id)
        if not gpu:
            return jsonify({"error": "GPU not found"}), 404

        if gpu not in project.gpus:
            return jsonify({"error": "GPU not in project"}), 400

        project.gpus.remove(gpu)
        db.session.commit()

        return jsonify(project.to_dict()), 200
    except Exception as e:
        print(f"Error in remove_gpu_from_project: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
