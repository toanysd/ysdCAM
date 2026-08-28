# v1.0.0
import networkx as nx
import math

class AnalysisSitusAdapter:
    """
    Giả lập logic của Analysis Situs:
    Sử dụng Attributed Adjacency Graph (AAG) để phân tích B-Rep topology.
    Nhận diện các đặc trưng gia công (Features) như Chamfer, Fillet, Hole.
    """
    def __init__(self, cq_shape):
        self.shape = cq_shape
        self.aag = nx.Graph()
        self.face_map = {}
        self._build_aag()

    def _build_aag(self):
        """
        Xây dựng đồ thị AAG (Attributed Adjacency Graph).
        Node: Mặt (Face)
        Edge: Cạnh (Edge) nối giữa 2 mặt.
        Thuộc tính: Loại mặt (Plane, Cylinder), Góc nhị diện (Dihedral Angle).
        """
        try:
            faces = self.shape.Faces()
            
            # Gắn Node
            for i, face in enumerate(faces):
                face_type = face.geomType()
                self.aag.add_node(i, face=face, type=face_type)
                self.face_map[i] = face
                
            # Duyệt để gắn Edge
            # CadQuery chưa có hàm lấy mặt kề trực tiếp dễ dàng trên Shape cũ,
            # Tuy nhiên ta có thể tìm các cạnh chung.
            # Với mỗi cạnh trong khối, nếu nó thuộc về 2 mặt, ta thêm 1 link.
            edges = self.shape.Edges()
            
            # Mapping Edge -> danh sách các Node ID (Faces)
            edge_to_faces = {}
            
            for i, face in enumerate(faces):
                for e in face.Edges():
                    e_hash = hash(e)
                    if e_hash not in edge_to_faces:
                        edge_to_faces[e_hash] = []
                    edge_to_faces[e_hash].append(i)
                    
            # Thêm link vào đồ thị
            for e_hash, face_ids in edge_to_faces.items():
                if len(face_ids) == 2:
                    f1, f2 = face_ids[0], face_ids[1]
                    # Tính góc giữa 2 mặt (tùy chọn để tối ưu, tạm thời gán link)
                    self.aag.add_edge(f1, f2, edge_hash=e_hash)
                    
            print(f"[AAG] Xây dựng thành công đồ thị: {self.aag.number_of_nodes()} faces, {self.aag.number_of_edges()} edges.")
        except Exception as e:
            print(f"[AAG] Lỗi khi dựng đồ thị AAG: {e}")

    def recognize_chamfers(self):
        """
        Nhận diện mặt Chamfer dựa trên AAG.
        Heuristics:
        - Là mặt Plane hoặc Cone.
        - Tiếp giáp với đúng 2 mặt chính lớn (Plane/Cylinder).
        - Bản thân mặt này có chu vi hẹp (diện tích nhỏ so với mặt chính).
        """
        chamfer_nodes = []
        try:
            for node in self.aag.nodes():
                data = self.aag.nodes[node]
                geom_type = data.get('type')
                
                # Chamfer thường là mặt phẳng (nhỏ) hoặc mặt nón (cone)
                if geom_type not in ['PLANE', 'CONE', 'Plane', 'Cone']:
                    continue
                    
                neighbors = list(self.aag.neighbors(node))
                
                # Một chamfer vát mép thường nối 2 mặt chính. 
                # (Với đa giác 3D, mặt chamfer có thể nối nhiều mặt nhỏ ở góc, 
                # nhưng xét về mặt lân cận chính là 2 mặt bự)
                if len(neighbors) >= 2:
                    # Tiêu chí: Diện tích mặt đang xét phải khá nhỏ (như dải băng)
                    face = data['face']
                    area = face.Area()
                    
                    # Tính diện tích trung bình của các mặt lân cận
                    neighbor_areas = [self.aag.nodes[n]['face'].Area() for n in neighbors]
                    max_neighbor_area = max(neighbor_areas) if neighbor_areas else 0.0
                    
                    # Nếu diện tích mặt này < 1/5 diện tích mặt lân cận to nhất, khả năng cao là Chamfer/Fillet
                    if area < max_neighbor_area * 0.2:
                        chamfer_nodes.append(node)
                        
            print(f"[AAG] Nhận diện được {len(chamfer_nodes)} mặt có thể là Chamfer/Fillet.")
            return chamfer_nodes
        except Exception as e:
            print(f"[AAG] Lỗi nhận diện Chamfer: {e}")
            return []
