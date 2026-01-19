"""
Guardrails/Safety Patterns para MOT_CEL
Implementa Input Validation e Output Filtering conforme padrões agentic

Este módulo implementa guardrails de segurança baseados nos padrões de design agentic:
- Input Validation: Validação rigorosa de frames e dados de entrada
- Output Filtering: Filtragem e validação de detecções de saída
- Rate Limiting: Controle de taxa de requisições por sessão
"""

import base64
import time
import logging
import numpy as np
import cv2
from typing import Tuple, List, Dict, Any
from collections import defaultdict

# Configurar logging
logger = logging.getLogger(__name__)

# =============================================================================
# INPUT VALIDATION GUARDRAILS
# =============================================================================

class RateLimiter:
    """Rate Limiter para controle de taxa de requisições por sessão"""
    
    _requests = defaultdict(list)
    
    @staticmethod
    def check(session_id: str, max_per_second: int = 30) -> Tuple[bool, str]:
        """
        Verifica se sessão não excedeu limite de taxa
        
        Args:
            session_id: ID da sessão
            max_per_second: Máximo de requisições por segundo
            
        Returns:
            Tuple[bool, str]: (is_allowed, error_message)
        """
        now = time.time()
        requests = RateLimiter._requests[session_id]
        
        # Remover requisições antigas (> 1 segundo)
        requests[:] = [req_time for req_time in requests if now - req_time < 1.0]
        
        # Verificar limite
        if len(requests) >= max_per_second:
            return False, f"Rate limit exceeded: max {max_per_second} requests/second"
        
        # Registrar nova requisição
        requests.append(now)
        return True, "OK"
    
    @staticmethod
    def reset_session(session_id: str):
        """Reseta contador de rate limiting para uma sessão"""
        if session_id in RateLimiter._requests:
            del RateLimiter._requests[session_id]


class FrameValidator:
    """
    Validador de frames de entrada
    Implementa validação de tamanho, formato, dimensões e sanitização
    """
    
    # Configurações de limites
    MAX_FRAME_SIZE = 10 * 1024 * 1024  # 10MB (tamanho do base64)
    MIN_FRAME_DIMENSION = 32  # Pixels
    MAX_FRAME_DIMENSION = 4096  # Pixels
    MAX_FPS_PER_SESSION = 30  # Frames por segundo por sessão
    MIN_BASE64_LENGTH = 100  # Tamanho mínimo esperado para base64
    
    @staticmethod
    def validate_frame_data(frame_data: str, session_id: str) -> Tuple[bool, str, np.ndarray]:
        """
        Valida dados do frame antes de processar
        
        Args:
            frame_data: String base64 do frame
            session_id: ID da sessão para rate limiting
            
        Returns:
            Tuple[bool, str, np.ndarray]: (is_valid, error_message, decoded_frame)
            Se is_valid=False, decoded_frame será None
        """
        # 1. Verificar se frame_data não está vazio
        if not frame_data or not isinstance(frame_data, str):
            return False, "Frame data está vazio ou não é string", None
        
        # 2. Verificar tamanho do base64
        if len(frame_data) > FrameValidator.MAX_FRAME_SIZE:
            return False, f"Frame muito grande: {len(frame_data)} bytes (max: {FrameValidator.MAX_FRAME_SIZE})", None
        
        if len(frame_data) < FrameValidator.MIN_BASE64_LENGTH:
            return False, f"Frame muito pequeno: {len(frame_data)} bytes (min: {FrameValidator.MIN_BASE64_LENGTH})", None
        
        # 3. Extrair base64 (remover prefixo data URL se presente)
        try:
            if "," in frame_data:
                # Formato: "data:image/jpeg;base64,<base64_data>"
                base64_part = frame_data.split(",")[-1]
            else:
                base64_part = frame_data
            
            # 4. Decodificar base64 para bytes
            try:
                frame_bytes = base64.b64decode(base64_part, validate=True)
            except Exception as e:
                return False, f"Formato base64 inválido: {str(e)}", None
            
            # 5. Verificar tamanho dos bytes decodificados
            if len(frame_bytes) == 0:
                return False, "Frame decodificado está vazio", None
            
            if len(frame_bytes) > FrameValidator.MAX_FRAME_SIZE:
                return False, f"Frame decodificado muito grande: {len(frame_bytes)} bytes", None
            
            # 6. Converter bytes para numpy array e decodificar imagem
            try:
                nparr = np.frombuffer(frame_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            except Exception as e:
                return False, f"Erro ao decodificar imagem: {str(e)}", None
            
            # 7. Verificar se a imagem foi decodificada com sucesso
            if frame is None:
                return False, "Não foi possível decodificar a imagem do frame", None
            
            # 8. Verificar dimensões do frame
            h, w = frame.shape[:2]
            
            if h < FrameValidator.MIN_FRAME_DIMENSION or w < FrameValidator.MIN_FRAME_DIMENSION:
                return False, f"Frame muito pequeno: {w}x{h} pixels (min: {FrameValidator.MIN_FRAME_DIMENSION}x{FrameValidator.MIN_FRAME_DIMENSION})", None
            
            if h > FrameValidator.MAX_FRAME_DIMENSION or w > FrameValidator.MAX_FRAME_DIMENSION:
                return False, f"Frame muito grande: {w}x{h} pixels (max: {FrameValidator.MAX_FRAME_DIMENSION}x{FrameValidator.MAX_FRAME_DIMENSION})", None
            
            # 9. Verificar se frame tem formato válido (altura e largura > 0)
            if h <= 0 or w <= 0:
                return False, f"Dimensões inválidas: {w}x{h}", None
            
            # 10. Verificar número de canais (deve ser 3 para RGB/BGR)
            if len(frame.shape) != 3 or frame.shape[2] != 3:
                return False, f"Formato de cor inválido: esperado 3 canais, recebido {frame.shape[2] if len(frame.shape) > 2 else 'N/A'}", None
            
            # 11. Rate limiting por sessão
            is_allowed, rate_error = RateLimiter.check(session_id, FrameValidator.MAX_FPS_PER_SESSION)
            if not is_allowed:
                return False, rate_error, None
            
            # Frame válido!
            logger.debug(f"Frame válido para sessão {session_id}: {w}x{h}, {len(frame_bytes)} bytes")
            return True, "OK", frame
        
        except Exception as e:
            logger.error(f"Erro inesperado na validação do frame: {type(e).__name__} - {e}")
            return False, f"Erro na validação: {str(e)}", None
    
    @staticmethod
    def validate_session_id(session_id: str) -> Tuple[bool, str]:
        """
        Valida formato do session_id
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if not session_id:
            return False, "Session ID não pode estar vazio"
        
        if not isinstance(session_id, str):
            return False, "Session ID deve ser string"
        
        if len(session_id) > 256:
            return False, f"Session ID muito longo: {len(session_id)} caracteres (max: 256)"
        
        if len(session_id) < 1:
            return False, "Session ID muito curto"
        
        # Verificar caracteres válidos (alphanumeric, underscore, hyphen)
        if not session_id.replace("_", "").replace("-", "").isalnum():
            return False, "Session ID contém caracteres inválidos (use apenas alphanumeric, _ e -)"
        
        return True, "OK"


# =============================================================================
# OUTPUT FILTERING GUARDRAILS
# =============================================================================

class DetectionValidator:
    """
    Validador de detecções de saída
    Implementa filtragem e validação de detecções para garantir qualidade
    """
    
    # Configurações de limites
    MIN_CONFIDENCE = 0.3  # Confiança mínima aceitável (30%)
    MIN_BBOX_AREA = 100  # Área mínima do bounding box em pixels²
    MAX_DETECTIONS_PER_FRAME = 100  # Máximo de detecções por frame
    MAX_BBOX_SIZE_RATIO = 0.95  # Bbox não pode ocupar mais que 95% do frame
    
    @staticmethod
    def validate_detections(
        detections: List[Dict[str, Any]], 
        frame_shape: Tuple[int, int]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Valida e filtra detecções inválidas
        
        Args:
            detections: Lista de detecções
            frame_shape: Tupla (height, width) do frame
            
        Returns:
            Tuple[List[Dict], List[str]]: (detecções válidas, lista de warnings)
        """
        if not detections:
            return [], []
        
        if not isinstance(detections, list):
            return [], ["Detecções devem ser uma lista"]
        
        if len(frame_shape) != 2:
            return [], ["Frame shape inválido"]
        
        h, w = frame_shape
        valid_detections = []
        warnings = []
        
        # Estatísticas para logging
        rejected_low_confidence = 0
        rejected_invalid_bbox = 0
        rejected_too_small = 0
        rejected_out_of_bounds = 0
        
        for i, det in enumerate(detections):
            if not isinstance(det, dict):
                warnings.append(f"Detecção {i} não é um dicionário, ignorada")
                continue
            
            # 1. Verificar confiança mínima
            confidence = det.get("confidence", 0.0)
            if not isinstance(confidence, (int, float)):
                warnings.append(f"Detecção {i} tem confiança inválida: {confidence}")
                continue
            
            if confidence < DetectionValidator.MIN_CONFIDENCE:
                rejected_low_confidence += 1
                continue
            
            # 2. Validar bounding box
            bbox = det.get("bbox", [])
            if not isinstance(bbox, list):
                warnings.append(f"Detecção {i} tem bbox inválido (não é lista)")
                continue
            
            if len(bbox) != 4:
                warnings.append(f"Detecção {i} tem bbox com tamanho incorreto: {len(bbox)} (esperado 4)")
                rejected_invalid_bbox += 1
                continue
            
            try:
                x1, y1, x2, y2 = [float(coord) for coord in bbox]
            except (ValueError, TypeError):
                warnings.append(f"Detecção {i} tem coordenadas bbox inválidas: {bbox}")
                rejected_invalid_bbox += 1
                continue
            
            # 3. Verificar se bbox é válido (x1 < x2, y1 < y2)
            if x1 >= x2 or y1 >= y2:
                warnings.append(f"Detecção {i} tem bbox inválido: coordenadas invertidas ({x1}, {y1}, {x2}, {y2})")
                rejected_invalid_bbox += 1
                continue
            
            # 4. Verificar se bbox está dentro do frame (com tolerância de 5%)
            tolerance = 0.05
            if x1 < -w * tolerance or y1 < -h * tolerance or x2 > w * (1 + tolerance) or y2 > h * (1 + tolerance):
                # Permitir pequenas extensões, mas registrar warning
                if x1 < -w * 0.1 or y1 < -h * 0.1 or x2 > w * 1.1 or y2 > h * 1.1:
                    rejected_out_of_bounds += 1
                    continue
                else:
                    # Clamp bbox ao frame
                    x1 = max(0, min(x1, w))
                    y1 = max(0, min(y1, h))
                    x2 = max(0, min(x2, w))
                    y2 = max(0, min(y2, h))
                    warnings.append(f"Detecção {i}: bbox foi ajustado para dentro do frame")
            
            # 5. Verificar área mínima
            area = (x2 - x1) * (y2 - y1)
            if area < DetectionValidator.MIN_BBOX_AREA:
                rejected_too_small += 1
                continue
            
            # 6. Verificar se bbox não ocupa mais que X% do frame (possível erro)
            frame_area = w * h
            bbox_ratio = area / frame_area if frame_area > 0 else 0
            if bbox_ratio > DetectionValidator.MAX_BBOX_SIZE_RATIO:
                warnings.append(f"Detecção {i}: bbox muito grande ({bbox_ratio*100:.1f}% do frame), possivelmente um erro")
                # Não rejeitar, apenas avisar
            
            # 7. Verificar campos obrigatórios
            required_fields = ["class_id", "class_name", "track_id"]
            missing_fields = [field for field in required_fields if field not in det]
            if missing_fields:
                warnings.append(f"Detecção {i} está faltando campos: {missing_fields}")
                continue
            
            # Criar detecção validada com bbox ajustado
            validated_det = det.copy()
            validated_det["bbox"] = [float(x1), float(y1), float(x2), float(y2)]
            validated_det["confidence"] = float(confidence)
            valid_detections.append(validated_det)
        
        # Limitar número máximo de detecções
        if len(valid_detections) > DetectionValidator.MAX_DETECTIONS_PER_FRAME:
            # Priorizar por confiança
            valid_detections.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            removed = len(valid_detections) - DetectionValidator.MAX_DETECTIONS_PER_FRAME
            valid_detections = valid_detections[:DetectionValidator.MAX_DETECTIONS_PER_FRAME]
            warnings.append(f"Limite de {DetectionValidator.MAX_DETECTIONS_PER_FRAME} detecções por frame excedido. {removed} detecções removidas (menor confiança)")
        
        # Log de estatísticas
        if rejected_low_confidence > 0 or rejected_invalid_bbox > 0 or rejected_too_small > 0 or rejected_out_of_bounds > 0:
            logger.debug(
                f"Validação de detecções: {len(valid_detections)} válidas, "
                f"rejeitadas - confiança baixa: {rejected_low_confidence}, "
                f"bbox inválido: {rejected_invalid_bbox}, "
                f"muito pequenas: {rejected_too_small}, "
                f"fora do frame: {rejected_out_of_bounds}"
            )
        
        return valid_detections, warnings
    
    @staticmethod
    def validate_frame_shape(frame_shape: List[int]) -> Tuple[bool, str]:
        """
        Valida formato do frame_shape
        
        Args:
            frame_shape: Lista [height, width]
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if not isinstance(frame_shape, list):
            return False, "Frame shape deve ser uma lista"
        
        if len(frame_shape) != 2:
            return False, f"Frame shape deve ter 2 elementos, recebido {len(frame_shape)}"
        
        try:
            h, w = int(frame_shape[0]), int(frame_shape[1])
        except (ValueError, TypeError):
            return False, "Frame shape deve conter apenas inteiros"
        
        if h <= 0 or w <= 0:
            return False, f"Frame shape inválido: {w}x{h} (deve ser > 0)"
        
        return True, "OK"
