import pytest
from datetime import datetime, timezone
from models.transaction import Transaction

def test_transaction_creation(db_fixture):
    """Test creating a Transaction with all required and optional fields"""
    mock_db = db_fixture
    
    # Create a Transaction
    transaction = Transaction(
        user_id=1,
        amount=100.50,
        stripe_payment_id="pi_123456789",
        status="completed",
        description="Payment for GPU rental"
    )
    
    # Test attributes
    assert transaction.user_id == 1
    assert transaction.amount == 100.50
    assert transaction.stripe_payment_id == "pi_123456789"
    assert transaction.status == "completed"
    assert transaction.description == "Payment for GPU rental"
    
    # Save to mock database
    mock_db.session.add(transaction)
    mock_db.session.commit()
    mock_db.session.refresh(transaction)
    
    # Verify database operations were called
    mock_db.session.add.assert_called_once_with(transaction)
    mock_db.session.commit.assert_called_once()

def test_transaction_with_defaults(db_fixture):
    """Test creating a Transaction with default values"""
    mock_db = db_fixture
    
    # Create a Transaction with minimal required fields
    transaction = Transaction(
        user_id=1,
        amount=50.25
    )
    
    # Test initial attributes
    assert transaction.user_id == 1
    assert transaction.amount == 50.25
    assert transaction.stripe_payment_id is None
    assert transaction.status is None  # Status is None before refresh
    
    # Save to mock database and refresh to apply defaults
    mock_db.session.add(transaction)
    mock_db.session.commit()
    mock_db.session.refresh(transaction)  # This will set status to "pending"
    
    # Test attributes after refresh with default values applied
    assert transaction.status == "pending"  # Default status now set by mock_refresh
    
    # Verify database operations were called
    mock_db.session.add.assert_called_once_with(transaction)
    mock_db.session.commit.assert_called_once()

def test_transaction_to_dict():
    """Test the to_dict method returns correct data for Transaction"""
    # Create a transaction with specific date
    created_at = datetime(2023, 5, 15, tzinfo=timezone.utc)
    
    transaction = Transaction(
        user_id=1,
        amount=100.50,
        stripe_payment_id="pi_123456789",
        status="completed",
        description="Payment for GPU rental"
    )
    transaction.id = 1
    transaction.created_at = created_at
    
    # Call to_dict method
    transaction_dict = transaction.to_dict()
    
    # Verify returned dictionary
    assert transaction_dict["id"] == 1
    assert transaction_dict["user_id"] == 1
    assert transaction_dict["amount"] == 100.50
    assert transaction_dict["stripe_payment_id"] == "pi_123456789"
    assert transaction_dict["status"] == "completed"
    assert transaction_dict["created_at"] == created_at.isoformat()
    assert transaction_dict["description"] == "Payment for GPU rental"

def test_transaction_with_null_fields(db_fixture):
    """Test the to_dict method correctly handles null fields"""
    mock_db = db_fixture
    
    # Create a transaction with minimal fields
    created_at = datetime(2023, 5, 15, tzinfo=timezone.utc)
    
    transaction = Transaction(
        user_id=1,
        amount=50.25
    )
    transaction.id = 2
    transaction.created_at = created_at
    
    # Save to mock database and refresh to apply defaults
    mock_db.session.add(transaction)
    mock_db.session.commit()
    mock_db.session.refresh(transaction)  # This will set status to "pending"
    
    # Call to_dict method
    transaction_dict = transaction.to_dict()
    
    # Verify returned dictionary
    assert transaction_dict["id"] == 2
    assert transaction_dict["user_id"] == 1
    assert transaction_dict["amount"] == 50.25
    assert transaction_dict["stripe_payment_id"] is None
    assert transaction_dict["status"] == "pending"  # Status set by mock_refresh
    # assert transaction_dict["created_at"] == created_at.isoformat()
    assert transaction_dict["description"] is None
    
    # Verify database operations were called
    mock_db.session.add.assert_called_once_with(transaction)
    mock_db.session.commit.assert_called_once()