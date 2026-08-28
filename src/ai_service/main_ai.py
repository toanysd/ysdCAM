import uvicorn
import torch
import os
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from typing import List

app = FastAPI(title="ysdCAM AI Microservice", version="1.0.0")

# Load PyTorch Weights
AAGNET_WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "AAGNet", "weights", "weight_on_MFInstseg.pth")
aagnet_model = None
if os.path.exists(AAGNET_WEIGHTS_PATH):
    try:
        # Load weights into CPU to avoid errors when CUDA is unavailable
        aagnet_model = torch.load(AAGNET_WEIGHTS_PATH, map_location=torch.device('cpu'), weights_only=True)
        print(f"[AI] Successfully loaded AAGNet weights from {AAGNET_WEIGHTS_PATH}")
    except Exception as e:
        print(f"[AI] Error loading AAGNet weights: {e}")

class FeaturePrediction(BaseModel):
    id: int
    label: str # "Through-hole", "Counterbore", "Pocket", "Slot"
    confidence: float
    nodes: List[int] # AAG Nodes

@app.get("/")
def read_root():
    return {"status": "AI Service Running", "models": ["AAGNet (Mock)", "MFTReNet (Mock)"]}

@app.post("/predict/aagnet", response_model=List[FeaturePrediction])
async def predict_features(file: UploadFile = File(...)):
    """
    Nhận file STEP hoặc dữ liệu AAG Graph từ Core CAM.
    Sử dụng AAGNet để dự đoán Instance Segmentation của các đặc trưng gia công.
    """
    # TODO: Load PyTorch model and run inference
    # content = await file.read()
    
    # Mock data return
    predictions = [
        FeaturePrediction(id=1, label="Counterbore", confidence=0.98, nodes=[1, 2, 3]),
        FeaturePrediction(id=2, label="Pocket", confidence=0.85, nodes=[10, 11, 12, 13, 14])
    ]
    return predictions

@app.post("/predict/mftrenet")
async def extract_topology(file: UploadFile = File(...)):
    """
    Sử dụng MFTReNet để phân tích Topology của B-Rep, 
    nhận diện các mối quan hệ ranh giới nâng cao.
    """
    return {"status": "success", "topology_graph": "Feature relationship extracted via Transformer."}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
