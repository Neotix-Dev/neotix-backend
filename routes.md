# GPU Cluster Rental Feature Changes

## Overview
We've transformed the project-based system into a cluster-based GPU rental system. This change allows users to create clusters, attach rental GPUs to them, and manage access through SSH keys.

## Model Changes

### Removed
- `ProjectGPU` model (association table between projects and GPUs)
- `Project` model (replaced by Cluster)

### Added
- `Cluster` model: Represents a collection of rental GPUs
  - One-to-one relationship with RentalGPU
  - Belongs to a user

- `RentalGPU` model (extends GPUListing):
  - SSH key management
  - Email notifications
  - Rental status tracking
  - User access control
  - Rental period tracking

## API Endpoints

### Cluster Management
```
GET    /api/clusters/                  # List all clusters for current user
GET    /api/clusters/<id>             # Get specific cluster details
POST   /api/clusters/                  # Create a new cluster
PUT    /api/clusters/<id>             # Update cluster details
DELETE /api/clusters/<id>             # Delete a cluster
```

### GPU Rental Management
```
POST   /api/clusters/<id>/gpu         # Add a GPU to cluster as rental
POST   /api/clusters/<id>/gpu/access  # Manage user access to GPU
PUT    /api/clusters/<id>/gpu/ssh-keys # Update SSH keys for rental GPU
```

## Key Features

1. **One GPU Per Cluster**
   - Each cluster can only have one rental GPU
   - Enforced through one-to-one relationship

2. **SSH Key Management**
   - Multiple SSH keys can be stored per rental GPU
   - Keys stored in JSON format for flexibility

3. **Access Control**
   - Multiple users can have access to a rental GPU
   - Access can be granted/revoked through the API

4. **Email Notifications**
   - Optional email notifications for rental events
   - Can be enabled/disabled per rental GPU

5. **Rental Status Tracking**
   - Track whether a GPU is currently rented
   - Track rental start and end times

## Database Changes
- Renamed tables from 'projects' to 'clusters'
- Added 'rental_gpus' table with:
  - Foreign key to clusters
  - Foreign key to gpu_listings
  - SSH keys storage
  - Rental status fields
- Added 'rental_gpu_users' association table for managing access

## Security Considerations
- SSH keys stored securely in database
- Access control enforced at API level
- Authentication required for all endpoints
