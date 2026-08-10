import sys
import os

# Adjust path to import files correctly
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from tests.test_workshop_platform import test_database_crud, test_webhook_endpoint
from tests.test_customer_flow import (
    test_database_school_emergency_contact,
    test_registration_endpoint,
    test_webhook_order_webhook_payment_update
)
from data.database import get_dashboard_metrics, init_db

def main():
    print("==================================================")
    print("RUNNING WORKSHOP PLATFORM INTEGRATION TESTS")
    print("==================================================")
    
    try:
        print("Initializing SQLite Database (clearing old test data)...")
        init_db(clear=True)
        print("Database initialized.")
        
        print("\n[1/5] Running test_database_crud...")
        test_database_crud()
        print("-> SUCCESS")
        
        print("\n[2/5] Running test_webhook_endpoint...")
        test_webhook_endpoint()
        print("-> SUCCESS")

        print("\n[3/5] Running test_database_school_emergency_contact...")
        test_database_school_emergency_contact()
        print("-> SUCCESS")

        print("\n[4/5] Running test_registration_endpoint...")
        test_registration_endpoint()
        print("-> SUCCESS")

        print("\n[5/5] Running test_webhook_order_webhook_payment_update...")
        test_webhook_order_webhook_payment_update()
        print("-> SUCCESS")
        
        print("\n==================================================")
        print("TEST RUN RESULTS: ALL TESTS PASSED SUCCESSFULLY! [PASS]")
        print("==================================================")
        
        metrics = get_dashboard_metrics()
        print(f"Current DB Metrics: {metrics}")
        
    except Exception as e:
        print(f"\n[FAIL] TEST RUN FAILED with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
