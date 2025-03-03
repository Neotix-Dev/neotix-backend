import sys
import os
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch, call

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.database import init_db

class TestDatabaseInitialization:
    """Test the init_db function"""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock Flask app"""
        app = MagicMock()
        app.config = {"SQLALCHEMY_DATABASE_URI": "postgresql://user:pass@localhost/testdb"}
        
        # Mock the app_context context manager
        context_manager = MagicMock()
        app.app_context.return_value = context_manager
        
        return app
    
    @pytest.fixture
    def mock_sqlalchemy_utils(self):
        """Mock sqlalchemy_utils functions"""
        with patch('utils.database.database_exists') as mock_exists, \
             patch('utils.database.create_database') as mock_create:
            yield {
                'exists': mock_exists,
                'create': mock_create
            }
    
    @pytest.fixture
    def mock_engine(self):
        """Mock SQLAlchemy engine"""
        with patch('utils.database.create_engine') as mock_create_engine:
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine
            mock_engine.url = "postgresql://user:pass@localhost/testdb"
            yield mock_engine
    
    @pytest.fixture
    def mock_db(self):
        """Mock the SQLAlchemy db object"""
        with patch('utils.database.db') as mock_db:
            yield mock_db
    
    def test_init_db_creates_database_when_not_exists(
            self, mock_app, mock_sqlalchemy_utils, mock_engine, mock_db):
        """Test that init_db creates a database if it doesn't exist"""
        # Set up mocks to indicate database doesn't exist
        mock_sqlalchemy_utils['exists'].return_value = False
        
        # Call the function
        init_db(mock_app)
        
        # Verify database creation was attempted
        mock_sqlalchemy_utils['exists'].assert_called_once_with(mock_engine.url)
        mock_sqlalchemy_utils['create'].assert_called_once_with(mock_engine.url)
        mock_db.create_all.assert_called_once()
    
    def test_init_db_skips_creation_when_database_exists(
            self, mock_app, mock_sqlalchemy_utils, mock_engine, mock_db):
        """Test that init_db doesn't try to create the database if it already exists"""
        # Set up mocks to indicate database exists
        mock_sqlalchemy_utils['exists'].return_value = True
        
        # Call the function
        init_db(mock_app)
        
        # Verify behavior
        mock_sqlalchemy_utils['exists'].assert_called_once_with(mock_engine.url)
        mock_sqlalchemy_utils['create'].assert_not_called()
        mock_db.create_all.assert_called_once()
    
    def test_init_db_creates_tables(self, mock_app, mock_sqlalchemy_utils, mock_engine, mock_db):
        """Test that init_db creates tables"""
        # Set up mocks
        mock_sqlalchemy_utils['exists'].return_value = True
        
        # Call the function
        init_db(mock_app)
        
        # Verify tables were created
        mock_db.create_all.assert_called_once()
    
    def test_init_db_uses_app_context(self, mock_app, mock_sqlalchemy_utils, mock_engine, mock_db):
        """Test that init_db uses the Flask app context"""
        # Call the function
        init_db(mock_app)
        
        # Verify app context was entered
        mock_app.app_context.assert_called_once()
        # Also verify the app context was used by checking that db.create_all was called
        mock_db.create_all.assert_called_once()
    
    def test_init_db_handles_errors(self, mock_app, mock_sqlalchemy_utils, mock_engine, mock_db):
        """Test that init_db handles errors properly"""
        # Set up mock to raise an exception
        mock_db.create_all.side_effect = Exception("Test database error")
        
        # Call the function - should re-raise the exception
        with pytest.raises(Exception) as excinfo:
            init_db(mock_app)
            
        # Verify the exception message
        assert "Test database error" in str(excinfo.value)
    
    def test_init_db_logs_information(self, mock_app, mock_sqlalchemy_utils, mock_engine, mock_db):
        """Test that init_db logs information properly"""
        with patch('utils.database.logger') as mock_logger:
            # Set up mocks
            mock_sqlalchemy_utils['exists'].return_value = False
            
            # Call the function
            init_db(mock_app)
            
            # Verify logging calls
            assert mock_logger.info.call_count >= 3
            # Check some specific log messages
            mock_logger.info.assert_any_call(f"Using database at: {mock_app.config['SQLALCHEMY_DATABASE_URI']}")
            mock_logger.info.assert_any_call(f"Created database at: {mock_app.config['SQLALCHEMY_DATABASE_URI']}")
            mock_logger.info.assert_any_call("Creating tables...")
            mock_logger.info.assert_any_call("Database initialization complete")
    
    def test_init_db_logs_errors(self, mock_app, mock_sqlalchemy_utils, mock_engine, mock_db):
        """Test that init_db logs errors properly"""
        with patch('utils.database.logger') as mock_logger:
            # Set up mock to raise an exception
            mock_db.create_all.side_effect = Exception("Test database error")
            
            # Call the function - should re-raise the exception
            with pytest.raises(Exception):
                init_db(mock_app)
                
            # Verify error was logged
            mock_logger.error.assert_called_once()
            assert "Test database error" in mock_logger.error.call_args[0][0]