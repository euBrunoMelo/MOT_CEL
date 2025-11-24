"""
YOLO Object Detection and Tracking Service with BentoML 1.4+
Suporta streaming de vídeo em tempo real via WebRTC/WebSocket
"""

import bentoml
import numpy as np
import cv2
from ultralytics import YOLO
import base64
from typing import Dict, Any, List
import time
from collections import defaultdict
from pydantic import BaseModel

# Configurações do serviço
MODEL_PATH = "best.pt"

# Modelos Pydantic para validação de entrada/saída
class VideoFrameRequest(BaseModel):
    frame: str
    session_id: str = "default"
    return_annotated: bool = False

class DetectionResult(BaseModel):
    bbox: List[float]
    confidence: float
    class_id: int
    class_name: str
    track_id: int

class VideoFrameResponse(BaseModel):
    detections: List[Dict[str, Any]]
    frame_shape: List[int]
    timestamp: float
    session_id: str
    annotated_frame: str = ""
    error: str = ""

class ModelInfoResponse(BaseModel):
    model_type: str
    classes: Dict[int, str]
    num_classes: int
    input_size: str
    tracking_enabled: bool

class YOLOTracker:
    """Classe para gerenciar detecção e tracking de objetos"""
    
    def __init__(self, model_path: str):
        self.model = YOLO(model_path)
        self.trackers = {}
        self.track_id_counter = 0
        self.track_history = defaultdict(list)
        
    def detect_and_track(self, frame: np.ndarray, session_id: str) -> Dict[str, Any]:
        """Realiza detecção e tracking de objetos em um frame"""
        # Realizar detecção
        results = self.model(frame, stream=False, verbose=False)
        
        detections = []
        
        for r in results:
            if r.boxes is not None:
                for box in r.boxes:
                    # Extrair informações da detecção
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = box.conf[0].cpu().numpy()
                    class_id = int(box.cls[0].cpu().numpy())
                    
                    # Obter nome da classe
                    class_name = self.model.names[class_id] if class_id < len(self.model.names) else f"class_{class_id}"
                    
                    detection = {
                        "bbox": [float(x1), float(y1), float(x2), float(y2)],
                        "confidence": float(confidence),
                        "class_id": class_id,
                        "class_name": class_name,
                        "track_id": self._assign_track_id(session_id, [x1, y1, x2, y2])
                    }
                    
                    detections.append(detection)
                    
                    # Adicionar ao histórico de tracking
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2
                    self.track_history[detection["track_id"]].append((center_x, center_y))
                    
                    # Limitar histórico a últimos 30 pontos
                    if len(self.track_history[detection["track_id"]]) > 30:
                        self.track_history[detection["track_id"]].pop(0)
        
        return {
            "detections": detections,
            "frame_shape": list(frame.shape[:2]),
            "timestamp": time.time(),
            "session_id": session_id
        }
    
    def _assign_track_id(self, session_id: str, bbox: List[float]) -> int:
        """Atribui um ID de tracking baseado em IoU com detecções anteriores"""
        if session_id not in self.trackers:
            self.trackers[session_id] = {}
        
        center_x = (bbox[0] + bbox[2]) / 2
        center_y = (bbox[1] + bbox[3]) / 2
        
        min_distance = float('inf')
        matched_id = None
        
        for track_id, last_pos in self.trackers[session_id].items():
            distance = np.sqrt((center_x - last_pos[0])**2 + (center_y - last_pos[1])**2)
            if distance < min_distance and distance < 50:  # threshold de 50 pixels
                min_distance = distance
                matched_id = track_id
        
        if matched_id is None:
            matched_id = self.track_id_counter
            self.track_id_counter += 1
        
        self.trackers[session_id][matched_id] = (center_x, center_y)
        
        return matched_id
    
    def get_track_history(self, track_id: int) -> List[tuple]:
        """Retorna o histórico de posições de um objeto rastreado"""
        return self.track_history.get(track_id, [])

# Inicializar o tracker globalmente
tracker = YOLOTracker(MODEL_PATH)

# Definir o serviço BentoML 1.4+
@bentoml.service(
    name="yolo-realtime-tracker",
    resources={
        "cpu": "2",
        "memory": "4Gi",
    },
)
class YOLOService:
    
    def __init__(self):
        self.tracker = tracker
    
    @bentoml.api
    def process_video_frame(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Endpoint para processar frames de vídeo codificados em base64
        Usado para integração com WebRTC/WebSocket
        """
        try:
            # Decodificar frame base64
            frame_data = data.get("frame", "")
            session_id = data.get("session_id", "default")
            
            if not frame_data:
                return {"error": "No frame data provided", "detections": [], "frame_shape": [], "timestamp": time.time(), "session_id": session_id}
            
            # Remover prefixo data URL se presente
            if "," in frame_data:
                frame_data = frame_data.split(",")[1]
            
            # Decodificar base64 para bytes
            frame_bytes = base64.b64decode(frame_data)
            
            # Converter bytes para numpy array
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return {"error": "Failed to decode frame", "detections": [], "frame_shape": [], "timestamp": time.time(), "session_id": session_id}
            
            # Processar frame
            result = self.tracker.detect_and_track(frame, session_id)
            
            # Adicionar frame anotado se solicitado
            if data.get("return_annotated", False):
                annotated_frame = draw_annotations(frame, result["detections"], self.tracker)
                _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                result["annotated_frame"] = base64.b64encode(buffer).decode('utf-8')
            
            return result
            
        except Exception as e:
            return {
                "error": str(e),
                "detections": [],
                "frame_shape": [],
                "timestamp": time.time(),
                "session_id": data.get("session_id", "default")
            }
    
    @bentoml.api
    def get_model_info(self) -> Dict[str, Any]:
        """Retorna informações sobre o modelo"""
        return {
            "model_type": "YOLOv8",
            "classes": self.tracker.model.names,
            "num_classes": len(self.tracker.model.names),
            "input_size": "Dynamic",
            "tracking_enabled": True
        }

def draw_annotations(frame: np.ndarray, detections: List[Dict], tracker: YOLOTracker) -> np.ndarray:
    """Desenha anotações no frame"""
    annotated = frame.copy()
    
    for det in detections:
        bbox = det["bbox"]
        x1, y1, x2, y2 = [int(x) for x in bbox]
        
        # Desenhar bounding box
        color = get_color_for_class(det["class_id"])
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        
        # Adicionar label
        label = f"{det['class_name']} #{det['track_id']} ({det['confidence']:.2f})"
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        
        # Background para o texto
        cv2.rectangle(annotated, 
                     (x1, y1 - label_size[1] - 10),
                     (x1 + label_size[0], y1),
                     color, -1)
        
        # Texto
        cv2.putText(annotated, label,
                   (x1, y1 - 5),
                   cv2.FONT_HERSHEY_SIMPLEX,
                   0.5, (255, 255, 255), 1)
        
        # Desenhar trilha de tracking
        track_history = tracker.get_track_history(det["track_id"])
        if len(track_history) > 1:
            points = np.array(track_history, dtype=np.int32)
            cv2.polylines(annotated, [points], False, color, 2)
    
    return annotated

def get_color_for_class(class_id: int) -> tuple:
    """Retorna uma cor única para cada classe"""
    colors = [
        (255, 0, 0),    # Vermelho
        (0, 255, 0),    # Verde
        (0, 0, 255),    # Azul
        (255, 255, 0),  # Amarelo
        (255, 0, 255),  # Magenta
        (0, 255, 255),  # Ciano
        (128, 0, 128),  # Roxo
        (255, 165, 0),  # Laranja
        (0, 128, 0),    # Verde escuro
        (0, 0, 128),    # Azul escuro
    ]
    return colors[class_id % len(colors)]