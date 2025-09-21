#!/usr/bin/env python3
"""
Test runner for Product Feedback Miner infrastructure tests.

This script runs comprehensive infrastructure tests to verify that all
core components are working correctly. Tests are organized to mirror
the project structure for better maintainability.
"""

import sys
import subprocess
from pathlib import Path

def run_infrastructure_tests():
    """Run comprehensive infrastructure tests."""
    project_root = Path(__file__).parent.parent
    
    print("🧪 Running Product Feedback Miner Infrastructure Tests")
    print("=" * 60)
    print("📁 Test Structure (mirroring project structure):")
    print("   tests/")
    print("   ├── agents/base/test_agent.py")
    print("   ├── config/test_settings.py")
    print("   ├── database/test_models.py")
    print("   ├── database/test_setup.py")
    print("   ├── utils/test_logging.py")
    print("   └── utils/test_monitoring.py")
    print("=" * 60)
    
    # Define test files to run
    test_files = [
        "tests/database/test_models.py",
        "tests/database/test_setup.py", 
        "tests/config/test_settings.py",
        "tests/agents/base/test_agent.py",
        "tests/utils/test_logging.py",
        "tests/utils/test_monitoring.py"
    ]
    
    all_passed = True
    total_tests = 0
    total_passed = 0
    
    for test_file in test_files:
        test_path = project_root / test_file
        if not test_path.exists():
            print(f"❌ Test file not found: {test_file}")
            all_passed = False
            continue
        
        print(f"\n🔍 Running {test_file}...")
        
        try:
            # Run pytest for each test file
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                str(test_path), 
                "-v", 
                "--tb=short",
                "--color=yes"
            ], capture_output=True, text=True, cwd=project_root)
            
            # Parse test results
            if result.returncode == 0:
                print(f"✅ {test_file} - PASSED")
                # Count tests from output
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'PASSED' in line:
                        total_passed += 1
                        total_tests += 1
            else:
                print(f"❌ {test_file} - FAILED")
                all_passed = False
                # Count tests from output
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'PASSED' in line:
                        total_passed += 1
                        total_tests += 1
                    elif 'FAILED' in line:
                        total_tests += 1
                
                if result.stderr:
                    print(f"   Error: {result.stderr.strip()}")
            
        except Exception as e:
            print(f"❌ Error running {test_file}: {e}")
            all_passed = False
    
    print("\n" + "=" * 60)
    print(f"📊 Test Summary: {total_passed}/{total_tests} tests passed")
    
    if all_passed:
        print("🎉 All infrastructure tests passed!")
        print("✅ Step 1: Core Infrastructure Setup is complete and working!")
        print("\n📁 Test Structure Benefits:")
        print("   • Modular: Each component has its own test file")
        print("   • Scalable: Easy to add new tests as project grows")
        print("   • Intuitive: Test structure mirrors project structure")
        print("   • Maintainable: Easy to find and fix specific tests")
        return True
    else:
        print(f"💥 {total_tests - total_passed} tests failed!")
        return False

if __name__ == "__main__":
    success = run_infrastructure_tests()
    sys.exit(0 if success else 1)
