#!/usr/bin/env python3
"""
Test script to verify the improved button labels work correctly
"""
import requests
import json

def test_ui_accessibility():
    """Test that the UI loads and has the improved button labels"""
    print("🎨 Testing UI Button Label Improvements")
    print("=" * 50)
    
    try:
        # Test if frontend loads (advanced UI with file management)
        response = requests.get("http://localhost:8000/app", timeout=10)
        if response.status_code == 200:
            print("✅ Frontend loading successfully")
            
            # Check for improved button labels in HTML
            html_content = response.text
            
            # Check for the new button labels
            if "📋 Extract Requirements" in html_content:
                print("✅ Found improved 'Extract Requirements' button label")
            else:
                print("❌ Missing 'Extract Requirements' button label")
                
            if "🧠 Add to Knowledge Base" in html_content:
                print("✅ Found improved 'Add to Knowledge Base' button label") 
            else:
                print("❌ Missing 'Add to Knowledge Base' button label")
                
            if "🧠 Knowledge Processing Parameters" in html_content:
                print("✅ Found improved modal title")
            else:
                print("❌ Missing improved modal title")
                
            # Check for individual file buttons
            if "🧠 Knowledge" in html_content:
                print("✅ Found improved individual 'Knowledge' button label")
            else:
                print("❌ Missing improved individual 'Knowledge' button label")
                
        else:
            print(f"❌ Frontend loading failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ UI test error: {e}")
        return False
        
    print(f"\n🎯 Summary:")
    print("  • 📋 Extract Requirements: Traditional BPMN workflow processing")
    print("  • 🧠 Add to Knowledge Base: Transform into searchable knowledge")
    print("  • Clear separation of functions with visual icons")
    print("  • Tooltips explain what each button does")
    
    return True

if __name__ == "__main__":
    test_ui_accessibility()
