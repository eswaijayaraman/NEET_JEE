#!/usr/bin/env python3
"""
Test script to verify app functionality locally
"""
import requests
import json
from bs4 import BeautifulSoup

BASE_URL = "http://127.0.0.1:5000"

def test_main_portal():
    """Test main portal page loads"""
    print("\n=== TEST 1: Main Portal Load ===")
    try:
        resp = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"✓ Status: {resp.status_code}")
        if "Weekly Examination Portal" in resp.text:
            print("✓ Portal title found")
            return True
        else:
            print("✗ Portal title NOT found")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_exam_board_load():
    """Test exam board loads with NEET stream"""
    print("\n=== TEST 2: Exam Board Load (NEET) ===")
    try:
        data = {"student_name": "TestStudent_NEET", "stream": "NEET"}
        resp = requests.post(f"{BASE_URL}/unified-test-board", data=data, timeout=10)
        print(f"✓ Status: {resp.status_code}")
        
        if "Weekly Examination Workspace" in resp.text:
            print("✓ Exam board page loaded")
        else:
            print("✗ Exam board page not properly rendered")
            
        if "Biology Section" in resp.text:
            print("✓ Biology section found (NEET stream)")
        else:
            print("✗ Biology section NOT found")
            
        if "Physics Section" in resp.text and "Chemistry Section" in resp.text:
            print("✓ Physics and Chemistry sections found")
        else:
            print("✗ Missing subject sections")
            
        # Check for questions
        if "Assessment Pool" in resp.text:
            print("✓ Question sections present")
            # Count questions
            soup = BeautifulSoup(resp.text, 'html.parser')
            questions = soup.find_all(class_='question-block')
            print(f"  Found {len(questions)} question blocks")
        else:
            print("✗ No assessment pool sections found")
            
        return resp.status_code == 200
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_jee_exam_board():
    """Test exam board loads with JEE stream"""
    print("\n=== TEST 3: Exam Board Load (JEE) ===")
    try:
        data = {"student_name": "TestStudent_JEE", "stream": "JEE"}
        resp = requests.post(f"{BASE_URL}/unified-test-board", data=data, timeout=10)
        print(f"✓ Status: {resp.status_code}")
        
        if "Mathematics Section" in resp.text:
            print("✓ Mathematics section found (JEE stream)")
        else:
            print("✗ Mathematics section NOT found (should be for JEE)")
            
        if "Biology Section" not in resp.text:
            print("✓ Biology section correctly absent (JEE stream)")
        else:
            print("✗ Biology section incorrectly present (should be absent for JEE)")
            
        return resp.status_code == 200
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_static_files():
    """Test static file serving"""
    print("\n=== TEST 4: Static Files ===")
    try:
        import os
        static_dir = "/workspaces/NEET_JEE/static"
        if os.path.exists(static_dir):
            files = os.listdir(static_dir)
            if files:
                print(f"✓ Static directory exists with {len(files)} files")
                # Try to access one
                first_file = files[0]
                try:
                    resp = requests.get(f"{BASE_URL}/static/{first_file}", timeout=5)
                    if resp.status_code == 200:
                        print(f"✓ Static file ({first_file}) served successfully")
                    else:
                        print(f"✗ Static file returned {resp.status_code}")
                except Exception as e:
                    print(f"✗ Cannot access static file: {e}")
            else:
                print("⚠ Static directory exists but empty")
        else:
            print("✗ Static directory not found")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_submit_exam():
    """Test exam submission"""
    print("\n=== TEST 5: Exam Submission (NEET) ===")
    try:
        # First load exam board to get question IDs
        data = {"student_name": "TestStudent_Submit", "stream": "NEET"}
        resp = requests.post(f"{BASE_URL}/unified-test-board", data=data, timeout=10)
        
        # Now submit answers
        submit_data = {
            "student_name": "TestStudent_Submit",
            "stream": "NEET",
            # Add some sample answers
            "Physics_q_1": "A",
            "Chemistry_q_1": "B",
            "Biology_q_1": "C",
        }
        
        resp = requests.post(f"{BASE_URL}/submit-unified-exam", data=submit_data, timeout=10)
        print(f"✓ Status: {resp.status_code}")
        
        if "Performance Evaluation Dashboard" in resp.text:
            print("✓ Results page loaded")
        else:
            print("✗ Results page NOT loaded properly")
            
        if "Grand Final Score" in resp.text:
            print("✓ Score displayed")
        else:
            print("✗ Score NOT displayed")
            
        return resp.status_code == 200
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dashboard():
    """Test teacher dashboard"""
    print("\n=== TEST 6: Teacher Dashboard ===")
    try:
        resp = requests.get(f"{BASE_URL}/dashboard", timeout=5)
        print(f"✓ Status: {resp.status_code}")
        
        if "Evaluated Scoreboard Registry" in resp.text or "Instructor Ledger" in resp.text:
            print("✓ Dashboard loaded")
            return True
        else:
            print("✗ Dashboard page format issue")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("NEET_JEE APP LOCAL TESTING SUITE")
    print("=" * 60)
    
    results = []
    results.append(("Main Portal", test_main_portal()))
    results.append(("Exam Board (NEET)", test_exam_board_load()))
    results.append(("Exam Board (JEE)", test_jee_exam_board()))
    results.append(("Static Files", test_static_files()))
    results.append(("Exam Submission", test_submit_exam()))
    results.append(("Dashboard", test_dashboard()))
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60)
