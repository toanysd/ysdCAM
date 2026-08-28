import RBush from 'rbush';

class CADSnapEngine {
  constructor() {
    this.tree = new RBush();
  }

  // Khởi tạo R-Tree từ dữ liệu Lỗ (Center) và Đường biên (Endpoint, Midpoint)
  loadData(holesData, edgesData, minX, maxY, hiddenLayers) {
    this.tree.clear();
    const bulkData = [];
    
    // 1. Quét các Lỗ khoan (Snapping vào TÂM - Center)
    if (holesData) {
      holesData.forEach((hole, idx) => {
        if (hiddenLayers[`hole-${hole.depth}`]) return; // Bỏ qua layer bị ẩn
        
        const x = hole.x - minX;
        const y = maxY - hole.y; // Chuyển đổi tọa độ hệ SVG
        
        // Tạo bounding box siêu nhỏ gọn cho điểm
        bulkData.push({
          minX: x - 0.01, minY: y - 0.01, maxX: x + 0.01, maxY: y + 0.01,
          type: 'center', x, y, originalIndex: idx, depth: hole.depth
        });
      });
    }

    // 2. Quét các Đường biên/Wires (Snapping vào ENDPOINT và MIDPOINT)
    if (edgesData) {
      edgesData.forEach(edgeGrp => {
        if (hiddenLayers[`edge-${edgeGrp.depth}`]) return; // Bỏ qua layer bị ẩn
        
        edgeGrp.wires.forEach(wire => {
          if (wire.length < 2) return;
          
          for (let i = 0; i < wire.length - 1; i++) {
            const p1 = { x: wire[i].x - minX, y: maxY - wire[i].y };
            const p2 = { x: wire[i+1].x - minX, y: maxY - wire[i+1].y };
            
            // Endpoint 1
            bulkData.push({
              minX: p1.x - 0.01, minY: p1.y - 0.01, maxX: p1.x + 0.01, maxY: p1.y + 0.01,
              type: 'endpoint', x: p1.x, y: p1.y, depth: edgeGrp.depth
            });
            
            // Endpoint 2
            bulkData.push({
              minX: p2.x - 0.01, minY: p2.y - 0.01, maxX: p2.x + 0.01, maxY: p2.y + 0.01,
              type: 'endpoint', x: p2.x, y: p2.y, depth: edgeGrp.depth
            });
            
            // Midpoint
            const midX = (p1.x + p2.x) / 2;
            const midY = (p1.y + p2.y) / 2;
            bulkData.push({
              minX: midX - 0.01, minY: midY - 0.01, maxX: midX + 0.01, maxY: midY + 0.01,
              type: 'midpoint', x: midX, y: midY, depth: edgeGrp.depth
            });
          }
        });
      });
    }

    // Nạp hàng loạt vào R-Tree (Cực nhanh: O(N log N))
    this.tree.load(bulkData);
  }

  // Tìm điểm gần nhất trong bán kính Threshold
  findSnapPoint(worldX, worldY, threshold = 10) {
    // Khoanh vùng tìm kiếm (Aperture Box)
    const searchBox = {
      minX: worldX - threshold,
      minY: worldY - threshold,
      maxX: worldX + threshold,
      maxY: worldY + threshold
    };
    
    // Tìm qua R-Tree (O(log N))
    const results = this.tree.search(searchBox);
    
    if (results.length === 0) return null;
    
    // Tìm điểm gần nhất trong các ứng viên
    let closestDist = Infinity;
    let closestPoint = null;
    
    results.forEach(item => {
      const dist = Math.sqrt((item.x - worldX) ** 2 + (item.y - worldY) ** 2);
      if (dist < closestDist && dist <= threshold) {
        closestDist = dist;
        closestPoint = { ...item, distance: dist };
      }
    });
    
    return closestPoint;
  }
}

// Xuất Singleton
export const snapEngine = new CADSnapEngine();
