"""
Unit tests for Security utilities
Tests password hashing, token generation, and cryptographic functions
"""

import pytest
from app.core.security import (
    hash_password, 
    verify_password, 
    generate_secure_token,
    generate_salt,
    constant_time_compare
)


@pytest.mark.unit
@pytest.mark.security
class TestSecurityUtils:
    """Test suite for security utility functions."""
    
    def test_hash_password(self):
        """Test password hashing."""
        # Arrange
        password = "TestPassword123!"
        
        # Act
        hashed = hash_password(password)
        
        # Assert
        assert hashed is not None
        assert len(hashed) > 0
        assert hashed != password  # Hash should be different from original
        assert isinstance(hashed, str)
    
    def test_hash_password_different_hashes(self):
        """Test that same password produces different hashes (due to salt)."""
        # Arrange
        password = "SamePassword123!"
        
        # Act
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # Assert
        assert hash1 != hash2  # Should be different due to random salt
    
    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        # Arrange
        password = "CorrectPassword123!"
        hashed = hash_password(password)
        
        # Act
        is_valid = verify_password(password, hashed)
        
        # Assert
        assert is_valid is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        # Arrange
        correct_password = "CorrectPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = hash_password(correct_password)
        
        # Act
        is_valid = verify_password(wrong_password, hashed)
        
        # Assert
        assert is_valid is False
    
    def test_verify_password_empty(self):
        """Test password verification with empty password."""
        # Arrange
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        # Act
        is_valid = verify_password("", hashed)
        
        # Assert
        assert is_valid is False
    
    def test_generate_secure_token_default_length(self):
        """Test secure token generation with default length."""
        # Act
        token = generate_secure_token()
        
        # Assert
        assert token is not None
        assert len(token) == 64  # 32 bytes = 64 hex characters
        assert isinstance(token, str)
        
        # Check it's valid hex
        int(token, 16)  # Should not raise an exception
    
    def test_generate_secure_token_custom_length(self):
        """Test secure token generation with custom length."""
        # Arrange
        length = 16
        
        # Act
        token = generate_secure_token(length)
        
        # Assert
        assert token is not None
        assert len(token) == length * 2  # hex encoding doubles the length
        assert isinstance(token, str)
        
        # Check it's valid hex
        int(token, 16)  # Should not raise an exception
    
    def test_generate_secure_token_uniqueness(self):
        """Test that generated tokens are unique."""
        # Act
        token1 = generate_secure_token()
        token2 = generate_secure_token()
        
        # Assert
        assert token1 != token2
    
    def test_generate_salt(self):
        """Test salt generation."""
        # Act
        salt = generate_salt()
        
        # Assert
        assert salt is not None
        assert len(salt) == 32  # 16 bytes = 32 hex characters
        assert isinstance(salt, str)
        
        # Check it's valid hex
        int(salt, 16)  # Should not raise an exception
    
    def test_generate_salt_uniqueness(self):
        """Test that generated salts are unique."""
        # Act
        salt1 = generate_salt()
        salt2 = generate_salt()
        
        # Assert
        assert salt1 != salt2
    
    def test_constant_time_compare_equal(self):
        """Test constant time comparison with equal strings."""
        # Arrange
        string1 = "SameString123"
        string2 = "SameString123"
        
        # Act
        result = constant_time_compare(string1, string2)
        
        # Assert
        assert result is True
    
    def test_constant_time_compare_different(self):
        """Test constant time comparison with different strings."""
        # Arrange
        string1 = "String1"
        string2 = "String2"
        
        # Act
        result = constant_time_compare(string1, string2)
        
        # Assert
        assert result is False
    
    def test_constant_time_compare_different_lengths(self):
        """Test constant time comparison with different length strings."""
        # Arrange
        string1 = "Short"
        string2 = "LongerString"
        
        # Act
        result = constant_time_compare(string1, string2)
        
        # Assert
        assert result is False
    
    def test_constant_time_compare_empty_strings(self):
        """Test constant time comparison with empty strings."""
        # Act
        result = constant_time_compare("", "")
        
        # Assert
        assert result is True
    
    def test_password_hash_verification_workflow(self):
        """Test complete password hash and verification workflow."""
        # Arrange
        passwords = [
            "SimplePassword",
            "ComplexP@ssw0rd123!",
            "çöğüş",  # Unicode characters
            "a",      # Single character
            "a" * 100 # Long password
        ]
        
        for password in passwords:
            # Act
            hashed = hash_password(password)
            is_valid = verify_password(password, hashed)
            is_invalid = verify_password(password + "wrong", hashed)
            
            # Assert
            assert is_valid is True, f"Failed to verify password: {password}"
            assert is_invalid is False, f"Incorrectly verified wrong password for: {password}"