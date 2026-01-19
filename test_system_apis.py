import requests
import json
import sys

BASE_URL = "http://localhost:3000/api"

def print_result(name, success, info=""):
    marker = "✅ PASS" if success else "❌ FAIL"
    print(f"[{marker}] {name} {info}")

def test_auth_apis():
    print("\n--- KIỂM TRA API AUTHENTICATION ---")
    try:
        resp = requests.get(f"{BASE_URL}/auth/status")
        success = resp.status_code == 200
        info = f"({resp.json().get('email', 'Guest')})" if success else f"(Status: {resp.status_code})"
        print_result("GET /api/auth/status", success, info)
    except Exception as e:
        print_result("GET /api/auth/status", False, str(e))

def test_utility_apis():
    print("\n--- KIỂM TRA API UTILITIES ---")
    try:
        payload = {"url": "https://docs.google.com/spreadsheets/d/1zFzHePIcOHXiWyAQRN7YOxIkE3kpDKwCuKMsdEe-snU/edit#gid=0"}
        resp = requests.post(f"{BASE_URL}/utils/parse-url", json=payload)
        success = resp.status_code == 200 and "spreadsheetId" in resp.json()
        print_result("POST /api/utils/parse-url", success)
    except Exception as e:
        print_result("POST /api/utils/parse-url", False, str(e))

def test_v2_model_reads():
    print("\n--- KIỂM TRA API V2 (GET DATA) ---")
    models = ["Media_Calendar", "Facebook_db", "Youtube_db", "Facebook_Config", "Youtube_Config"]
    for model in models:
        try:
            resp = requests.get(f"{BASE_URL}/v2/sheets/{model}")
            success = resp.status_code == 200 and isinstance(resp.json(), list)
            count = len(resp.json()) if success else 0
            print_result(f"GET /v2/sheets/{model}", success, f"({count} hàng)")
        except Exception as e:
            print_result(f"GET /v2/sheets/{model}", False, str(e))

def test_v2_crud_lifecycle():
    print("\n--- KIỂM TRA CHU KỲ CRUD V2 (CREATE/UPDATE/DELETE) ---")
    target = "Facebook_Config"
    try:
        # Create
        payload = {"page_name": "TEST_AUTO", "page_id": "999", "access_token": "T_TOKEN"}
        resp = requests.post(f"{BASE_URL}/v2/sheets/{target}", json=payload)
        if resp.status_code != 200:
            print_result(f"POST /v2/sheets/{target}", False, "Không thể tạo hàng test")
            return

        # Read to find index
        data = requests.get(f"{BASE_URL}/v2/sheets/{target}").json()
        idx = len(data) - 1
        
        # Update
        payload["page_name"] = "TEST_AUTO_UPDATED"
        resp = requests.put(f"{BASE_URL}/v2/sheets/{target}/{idx}", json=payload)
        update_ok = resp.status_code == 200
        
        # Delete
        resp = requests.delete(f"{BASE_URL}/v2/sheets/{target}/{idx}")
        delete_ok = resp.status_code == 200
        
        print_result("POST (Create)", True)
        print_result("PUT (Update)", update_ok)
        print_result("DELETE (Cleanup)", delete_ok)
        
    except Exception as e:
        print_result("CRUD Lifecycle", False, str(e))

def test_task_apis():
    print("\n--- KIỂM TRA API TASKS ---")
    try:
        resp = requests.get(f"{BASE_URL}/tasks")
        success = resp.status_code == 200
        print_result("GET /api/tasks", success)
    except Exception as e:
        print_result("GET /api/tasks", False, str(e))

if __name__ == "__main__":
    print("🚀 BẮT ĐẦU UNIT TEST TOÀN BỘ HỆ THỐNG API\n")
    test_auth_apis()
    test_task_apis()
    test_utility_apis()
    test_v2_model_reads()
    test_v2_crud_lifecycle()
    print("\n🏁 HOÀN TẤT KIỂM TRA.")
