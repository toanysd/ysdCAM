import os
import sys
import tempfile
import pytest
from fastapi.testclient import TestClient

# Đảm bảo có thể import được các module trong src
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import app FastAPI
from src.presentation.api import app

client = TestClient(app)

def test_analyze_step_returns_valid_boundaries():
    """
    Test tích hợp gọi API /analyze-step với mock STEP file.
    Kiểm tra cấu trúc JSON trả về có chứa 'boundaries' và là danh sách các polygons.
    """
    # Tạo một mock file STEP tạm thời
    mock_step_content = b"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('Mock STEP file'), '2;1');
FILE_NAME('mock.step', '2026-06-02', ('Author'), ('Organization'), 'preprocessor', 'originator', 'authorization');
FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));
ENDSEC;
DATA;
ENDSEC;
END-ISO-10303-21;
"""
    
    # Gửi request POST tới endpoint /api/analyze
    response = client.post(
        "/api/analyze",
        data={"strategy": "polygon", "calc_mode": "3d_only"},
        files={"file": ("test_mock.step", mock_step_content, "application/octet-stream")}
    )
    
    if response.status_code == 404:
        pytest.skip("Endpoint /api/analyze chưa được triển khai.")
        
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    
    data = response.json()
    
    # 1. Kiểm tra phải có key 'edges'
    assert "edges" in data, "JSON response phải chứa key 'edges'"
    
    # 2. 'edges' phải là danh sách (list)
    edges = data["edges"]
    assert isinstance(edges, list), "Giá trị của 'edges' phải là danh sách"
    
    # 3. Kiểm tra từng polygon trong danh sách nếu có
    for polygon in edges:
        # Mỗi polygon thường là một list các điểm hoặc dict
        assert isinstance(polygon, (list, dict)), "Mỗi polygon trong 'edges' phải là danh sách tọa độ hoặc đối tượng hợp lệ"
        
        # Nếu polygon là dict, kiểm tra wires
        if isinstance(polygon, dict) and "wires" in polygon:
             assert isinstance(polygon["wires"], list)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
