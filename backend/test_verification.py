#!/usr/bin/env python3
"""
Test script for Verification Agent endpoints.
Run with: python test_verification.py
Requires: httpx, a running backend server, and a valid JWT token.
"""

import asyncio
import json
import uuid
from pathlib import Path

import httpx

# Configuration
BASE_URL = "http://localhost:8000"
# You need to replace this with a valid JWT token from your auth system
JWT_TOKEN = "YOUR_JWT_TOKEN_HERE"

# Test files (create these in backend/test_data/ directory)
TEST_CERT_PDF = "test_data/sample_certificate.pdf"
TEST_PROFILE_JSON = "test_data/sample_profile.json"

async def register_and_login():
    """Register a test user and get JWT token (if your auth allows)."""
    async with httpx.AsyncClient() as client:
        # Try to register (may fail if user exists)
        register_resp = await client.post(f"{BASE_URL}/auth/register", json={
            "email": "test@example.com",
            "password": "testpass123",
            "full_name": "Test User"
        })
        
        # Login to get token
        login_resp = await client.post(f"{BASE_URL}/auth/login", json={
            "email": "test@example.com",
            "password": "testpass123"
        })
        
        if login_resp.status_code == 200:
            data = login_resp.json()
            return data.get("access_token") or data.get("token")
        else:
            print(f"Login failed: {login_resp.text}")
            return None

async def test_certificate_verification():
    """Test certificate verification with file upload."""
    print("\n=== Testing Certificate Verification ===")
    
    # Ensure test file exists
    if not Path(TEST_CERT_PDF).exists():
        print(f"Test certificate file not found: {TEST_CERT_PDF}")
        print("Create a test PDF certificate or update the path.")
        return
    
    headers = {"Authorization": f"Bearer {JWT_TOKEN}"}
    
    async with httpx.AsyncClient() as client:
        with open(TEST_CERT_PDF, "rb") as f:
            files = {"file": ("certificate.pdf", f, "application/pdf")}
            data = {
                "link": None,
                "profile_data": json.dumps({
                    "name": "John Doe",
                    "email": "john@example.com",
                    "expected_issuer": "Test University"
                })
            }
            
            resp = await client.post(
                f"{BASE_URL}/verify",
                headers=headers,
                files=files,
                data=data
            )
            
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                result = resp.json()
                print(f"Run ID: {result.get('run_id')}")
                print(f"Input Type: {result.get('input_type')}")
                print(f"Confidence Score: {result.get('confidence_score')}")
                print(f"Status: {result.get('status')}")
                print(f"Explanation: {json.dumps(result.get('explanation'), indent=2)}")
                return result.get('run_id')
            else:
                print(f"Error: {resp.text}")
                return None

async def test_project_verification():
    """Test GitHub project verification."""
    print("\n=== Testing Project Verification ===")
    
    headers = {"Authorization": f"Bearer {JWT_TOKEN}"}
    
    async with httpx.AsyncClient() as client:
        data = {
            "file": None,
            "link": "https://github.com/microsoft/vscode",
            "profile_data": json.dumps({
                "name": "John Doe",
                "github_username": "johndoe"
            })
        }
        
        resp = await client.post(
            f"{BASE_URL}/verify",
            headers=headers,
            data=data
        )
        
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            result = resp.json()
            print(f"Run ID: {result.get('run_id')}")
            print(f"Input Type: {result.get('input_type')}")
            print(f"Confidence Score: {result.get('confidence_score')}")
            print(f"Status: {result.get('status')}")
            print(f"Explanation: {json.dumps(result.get('explanation'), indent=2)}")
            return result.get('run_id')
        else:
            print(f"Error: {resp.text}")
            return None

async def test_profile_verification():
    """Test profile data verification."""
    print("\n=== Testing Profile Verification ===")
    
    headers = {"Authorization": f"Bearer {JWT_TOKEN}"}
    
    profile_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+1-555-0123",
        "address": "123 Test St, Test City, TC 12345",
        "education": [
            {
                "institution": "Test University",
                "degree": "Bachelor of Science",
                "field": "Computer Science",
                "start_date": "2020-09-01",
                "end_date": "2024-05-01"
            }
        ],
        "work_experience": [
            {
                "company": "Test Corp",
                "position": "Software Engineer",
                "start_date": "2024-06-01",
                "end_date": None,
                "description": "Developing software solutions"
            }
        ]
    }
    
    async with httpx.AsyncClient() as client:
        data = {
            "file": None,
            "link": None,
            "profile_data": json.dumps(profile_data)
        }
        
        resp = await client.post(
            f"{BASE_URL}/verify",
            headers=headers,
            data=data
        )
        
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            result = resp.json()
            print(f"Run ID: {result.get('run_id')}")
            print(f"Input Type: {result.get('input_type')}")
            print(f"Confidence Score: {result.get('confidence_score')}")
            print(f"Status: {result.get('status')}")
            print(f"Explanation: {json.dumps(result.get('explanation'), indent=2)}")
            return result.get('run_id')
        else:
            print(f"Error: {resp.text}")
            return None

async def test_feedback(run_id: str):
    """Test feedback submission."""
    print(f"\n=== Testing Feedback for Run {run_id} ===")
    
    headers = {"Authorization": f"Bearer {JWT_TOKEN}"}
    
    feedback_data = {
        "is_correct": True,
        "notes": "Verification looks accurate and helpful."
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/verify/{run_id}/feedback",
            headers=headers,
            json=feedback_data
        )
        
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print("Feedback submitted successfully!")
            print(f"Response: {resp.json()}")
        else:
            print(f"Error: {resp.text}")

async def main():
    """Run all verification tests."""
    print("Starting Verification Agent Tests")
    print(f"Base URL: {BASE_URL}")
    
    # Get JWT token if not provided
    global JWT_TOKEN
    if JWT_TOKEN == "YOUR_JWT_TOKEN_HERE":
        print("No JWT token provided. Attempting to register/login...")
        JWT_TOKEN = await register_and_login()
        if not JWT_TOKEN:
            print("Failed to get JWT token. Please update JWT_TOKEN in the script.")
            return
    
    # Test different verification types
    cert_run_id = await test_certificate_verification()
    project_run_id = await test_project_verification()
    profile_run_id = await test_profile_verification()
    
    # Test feedback on one of the runs
    if cert_run_id:
        await test_feedback(cert_run_id)
    
    print("\n=== Test Summary ===")
    print(f"Certificate verification run ID: {cert_run_id}")
    print(f"Project verification run ID: {project_run_id}")
    print(f"Profile verification run ID: {profile_run_id}")
    print("\nAll tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
