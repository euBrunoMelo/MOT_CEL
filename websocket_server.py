"""
WebSocket Server para streaming de vídeo em tempo real
Integrado com o serviço BentoML
"""

import asyncio
import websockets
import json
import base64
import numpy as np
import cv2
from typing import Set, Dict, Any
import logging
import aiohttp
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações
BENTOML_SERVICE_URL = "http://localhost:3000"  # URL do serviço BentoML
WEBSOCKET_PORT = 8765

class VideoStreamHandler:
    """Gerenciador de streams de vídeo"""
    
    def __init__(self):
        self.active_connections: Set[Any] = set()
        self.session_data: Dict[str, Any] = {}
        
    async def register(self, websocket: Any, session_id: str):
        """Registra nova conexão"""
        self.active_connections.add(websocket)
        self.session_data[session_id] = {
            "websocket": websocket,
            "started_at": datetime.now(),
            "frames_processed": 0,
            "last_fps": 0
        }
        logger.info(f"Nova conexão registrada: {session_id}")
        
    async def unregister(self, websocket: Any, session_id: str):
        """Remove conexão"""
        self.active_connections.discard(websocket)
        if session_id in self.session_data:
            del self.session_data[session_id]
        logger.info(f"Conexão removida: {session_id}")
        
    async def process_frame(self, frame_data: str, session_id: str) -> Dict[str, Any]:
        """
        Processa frame através do serviço BentoML
        """
        try:
            # Preparar dados para o BentoML - WRAPPED IN 'data' field
            payload = {
                "data": {
                    "frame": frame_data,
                    "session_id": session_id,
                    "return_annotated": True
                }
            }
            
            # Fazer requisição ASSÍNCRONA ao BentoML
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(
                        f"{BENTOML_SERVICE_URL}/process_video_frame",
                        json=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=aiohttp.ClientTimeout(total=30)  # AUMENTADO PARA 30 SEGUNDOS
                    ) as response:
                        
                        if response.status == 200:
                            result = await response.json()
                            
                            # Atualizar estatísticas
                            if session_id in self.session_data:  # VERIFICAÇÃO ADICIONAL
                                self.session_data[session_id]["frames_processed"] += 1
                            
                            return result
                        else:
                            error_text = await response.text()
                            logger.error(f"Erro no BentoML ({response.status}): {error_text}")
                            return {"error": f"Processing error: {response.status}"}
                
                except asyncio.TimeoutError:
                    logger.error(f"Timeout ao processar frame da sessão {session_id}")
                    return {"error": "Processing timeout"}
                except aiohttp.ClientError as e:
                    logger.error(f"Erro de conexão ao BentoML: {type(e).__name__} - {e}")
                    return {"error": f"Connection error: {str(e)}"}
                    
        except Exception as e:
            logger.error(f"Erro inesperado ao processar frame: {type(e).__name__} - {e}")
            return {"error": str(e)}
    
    async def broadcast_stats(self):
        """Envia estatísticas para todos os clientes conectados"""
        while True:
            await asyncio.sleep(1)  # Atualizar a cada segundo
            
            stats = {
                "type": "stats",
                "active_connections": len(self.active_connections),
                "timestamp": datetime.now().isoformat()
            }
            
            # Enviar para todos os clientes
            if self.active_connections:
                await asyncio.gather(
                    *[ws.send(json.dumps(stats)) for ws in self.active_connections],
                    return_exceptions=True
                )

# Instância global do handler
stream_handler = VideoStreamHandler()

async def handle_client(websocket: Any):
    """
    Handler principal para cada cliente WebSocket
    """
    session_id = None
    
    try:
        # Aguardar mensagem inicial com session_id
        init_message = await websocket.recv()
        init_data = json.loads(init_message)
        session_id = init_data.get("session_id", "unknown")
        
        # Registrar cliente
        await stream_handler.register(websocket, session_id)
        
        # Enviar confirmação
        await websocket.send(json.dumps({
            "type": "connected",
            "session_id": session_id,
            "message": "Conectado ao servidor de streaming"
        }))
        
        # Loop principal para processar frames
        async for message in websocket:
            try:
                data = json.loads(message)
                
                if data.get("type") == "frame":
                    # Processar frame de vídeo
                    frame_data = data.get("data", "")
                    
                    if frame_data:
                        # Processar através do BentoML
                        result = await stream_handler.process_frame(frame_data, session_id)
                        
                        # Preparar resposta
                        response = {
                            "type": "detection_result",
                            "session_id": session_id,
                            "detections": result.get("detections", []),
                            "annotated_frame": result.get("annotated_frame", ""),
                            "timestamp": result.get("timestamp", 0)
                        }
                        
                        # Enviar resultado de volta
                        await websocket.send(json.dumps(response))
                
                elif data.get("type") == "ping":
                    # Responder ao ping
                    await websocket.send(json.dumps({"type": "pong"}))
                    
            except json.JSONDecodeError:
                logger.error(f"Erro ao decodificar JSON de {session_id}")
            except Exception as e:
                logger.error(f"Erro ao processar mensagem de {session_id}: {e}")
                
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Conexão fechada: {session_id}")
    except Exception as e:
        logger.error(f"Erro na conexão {session_id}: {e}")
    finally:
        if session_id:
            await stream_handler.unregister(websocket, session_id)

async def main():
    """
    Função principal para iniciar o servidor WebSocket
    """
    logger.info(f"Iniciando servidor WebSocket na porta {WEBSOCKET_PORT}")
    
    # Iniciar task de broadcast de estatísticas
    asyncio.create_task(stream_handler.broadcast_stats())
    
    # Iniciar servidor WebSocket
    async with websockets.serve(handle_client, "0.0.0.0", WEBSOCKET_PORT):
        logger.info(f"Servidor WebSocket rodando em ws://localhost:{WEBSOCKET_PORT}")
        await asyncio.Future()  # Rodar para sempre

if __name__ == "__main__":
    asyncio.run(main())