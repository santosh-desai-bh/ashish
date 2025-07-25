#!/usr/bin/env python3
"""
UI Layout Regression Test
Ensures the UI spacing and layout remains consistent and doesn't regress
"""
import re
import os

class TestUILayoutRegression:
    def test_map_height_consistent(self):
        """Ensure map height stays at 650px"""
        with open('/Users/blowhorn/ashish/main.py', 'r') as f:
            content = f.read()
        
        # Check map height is 650px
        map_height_match = re.search(r'height=(\d+)', content)
        if map_height_match:
            height = int(map_height_match.group(1))
            assert height == 650, f"Map height should be 650px, found {height}px"
            print(f"✅ Map height correct: {height}px")
        else:
            raise AssertionError("Map height not found in main.py")
    
    def test_spacing_margins_controlled(self):
        """Ensure spacing margins are properly controlled"""
        with open('/Users/blowhorn/ashish/main.py', 'r') as f:
            content = f.read()
        
        # Check for controlled negative margins (should be -50px)
        margin_matches = re.findall(r'margin-top:\s*(-?\d+)px', content)
        
        if margin_matches:
            for margin in margin_matches:
                margin_val = int(margin)
                assert margin_val >= -50, f"Margin too negative: {margin_val}px (max allowed: -50px)"
            print(f"✅ Margins controlled: {margin_matches}")
        else:
            print("⚠️ No explicit margins found - using default spacing")
    
    def test_ui_sections_order(self):
        """Ensure UI sections are in the correct order"""
        with open('/Users/blowhorn/ashish/main.py', 'r') as f:
            content = f.read()
        
        # Check order of UI sections (cost analytics is in separate file)
        sections = [
            'st_folium',  # Map display
            'Network overview',  # Metrics
            'First Mile Fleet Requirements',  # Vehicle summary
            'show_simple_cost_analysis'  # Cost analytics function call
        ]
        
        last_pos = 0
        for section in sections:
            pos = content.find(section)
            if pos == -1:
                raise AssertionError(f"UI section '{section}' not found")
            
            if pos < last_pos:
                raise AssertionError(f"UI section '{section}' out of order")
            
            last_pos = pos
            print(f"✅ Section '{section}' in correct position")
    
    def test_no_excessive_blank_space(self):
        """Ensure no excessive blank space in UI"""
        with open('/Users/blowhorn/ashish/main.py', 'r') as f:
            content = f.read()
        
        # Check for multiple consecutive st.markdown with empty divs
        excessive_space = re.findall(r'(st\.markdown\([^)]*margin-top:\s*-?\d+px[^)]*\)){2,}', content)
        
        assert len(excessive_space) == 0, f"Found excessive spacing patterns: {len(excessive_space)}"
        print("✅ No excessive blank space patterns found")
    
    def test_checkpoint_ui_preserved(self):
        """Ensure UI_CHECKPOINT.md requirements are met"""
        checkpoint_file = '/Users/blowhorn/ashish/UI_CHECKPOINT.md'
        
        if not os.path.exists(checkpoint_file):
            raise AssertionError("UI_CHECKPOINT.md not found")
        
        with open(checkpoint_file, 'r') as f:
            checkpoint_content = f.read()
        
        # Check key checkpoint requirements
        requirements = [
            'Height.*650px',
            '4 columns.*metrics',
            'Vehicle.*below metrics',
            'Cost.*below vehicles'
        ]
        
        with open('/Users/blowhorn/ashish/main.py', 'r') as f:
            main_content = f.read()
        
        # Verify 4-column layout exists
        four_columns = re.search(r'st\.columns\(4\)', main_content)
        assert four_columns, "4-column layout not found"
        print("✅ 4-column layout preserved")
        
        # Verify vehicle section exists
        vehicle_section = 'First Mile Fleet Requirements' in main_content
        assert vehicle_section, "Vehicle section not found"
        print("✅ Vehicle section preserved")
        
        # Verify cost section exists (function call)
        cost_section = 'show_simple_cost_analysis' in main_content
        assert cost_section, "Cost section function call not found"
        print("✅ Cost section preserved")

def run_ui_regression_tests():
    """Run all UI regression tests"""
    print("🧪 UI LAYOUT REGRESSION TEST SUITE")
    print("=" * 50)
    
    test_suite = TestUILayoutRegression()
    tests = [
        test_suite.test_map_height_consistent,
        test_suite.test_spacing_margins_controlled,
        test_suite.test_ui_sections_order,
        test_suite.test_no_excessive_blank_space,
        test_suite.test_checkpoint_ui_preserved
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: {e}")
    
    print(f"\n📊 UI REGRESSION TEST RESULTS")
    print("=" * 40)
    
    if passed == total:
        print(f"🎉 ALL UI TESTS PASSED ({passed}/{total})")
        print("✅ UI layout is stable and consistent")
        return True
    else:
        print(f"❌ UI TESTS FAILED ({passed}/{total})")
        print("⚠️ UI has regressed - needs fixing")
        return False

if __name__ == "__main__":
    success = run_ui_regression_tests()
    if not success:
        exit(1)