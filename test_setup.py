#!/usr/bin/env python3
"""
Test script to verify Work Time Tracker setup
"""

import os
import sys
from dotenv import load_dotenv

def test_imports():
    """Test if all required packages can be imported"""
    print("Testing imports...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        print("✓ PyQt6 imported successfully")
    except ImportError as e:
        print(f"✗ PyQt6 import failed: {e}")
        return False
    
    try:
        from notion_client import Client
        print("✓ Notion client imported successfully")
    except ImportError as e:
        print(f"✗ Notion client import failed: {e}")
        return False
    
    try:
        from PIL import ImageGrab
        print("✓ Pillow imported successfully")
    except ImportError as e:
        print(f"✗ Pillow import failed: {e}")
        return False
    
    return True

def test_env_vars():
    """Test environment variables"""
    print("\nTesting configuration...")
    
    try:
        import yaml
        with open('config.yaml', 'r') as file:
            config = yaml.safe_load(file)
        
        notion_token = config.get('notion', {}).get('api')
        database_id = config.get('notion', {}).get('database_id')
        
        if not notion_token or notion_token == "your_notion_integration_token_here":
            print("✗ Notion API token not configured in config.yaml")
            return False
        else:
            print("✓ Notion API token found")
        
        if not database_id or database_id == "your_database_id_here":
            print("✗ Database ID not configured in config.yaml")
            return False
        else:
            print("✓ Database ID found")
        
        return True
        
    except FileNotFoundError:
        print("✗ config.yaml file not found")
        return False
    except Exception as e:
        print(f"✗ Error reading config.yaml: {e}")
        return False

def test_notion_connection():
    """Test Notion API connection"""
    print("\nTesting Notion connection...")
    
    try:
        from src.notion_client import NotionClient
        client = NotionClient()
        
        if client.test_connection():
            print("✓ Notion connection successful")
            return True
        else:
            print("✗ Notion connection failed")
            return False
            
    except Exception as e:
        print(f"✗ Notion connection error: {e}")
        return False

def test_screenshot_capability():
    """Test screenshot capability"""
    print("\nTesting screenshot capability...")
    
    try:
        from PIL import ImageGrab
        # Just test if we can import, actual screenshot requires GUI
        print("✓ Screenshot capability available")
        return True
    except Exception as e:
        print(f"✗ Screenshot capability error: {e}")
        return False

def main():
    """Run all tests"""
    print("Work Time Tracker Setup Test")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_env_vars,
        test_notion_connection,
        test_screenshot_capability
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 40)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed! Setup is complete.")
        print("You can now run: python main.py")
    else:
        print("✗ Some tests failed. Please check the setup instructions.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 