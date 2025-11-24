# 🎯 MOT_CEL - Multi-Object Tracking em Tempo Real

Sistema de detecção e rastreamento de múltiplos objetos em tempo real usando YOLOv8, BentoML e WebSocket.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-00FFFF.svg)
![BentoML](https://img.shields.io/badge/BentoML-1.2+-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## 📋 Sobre o Projeto

Este projeto implementa um sistema completo de **detecção e rastreamento de objetos** (Multi-Object Tracking - MOT) com as seguintes características:

- 🚀 **Processamento em Tempo Real**: Streaming de vídeo via WebSocket
- 🎯 **Detecção Precisa**: Utiliza YOLOv8 para detecção de objetos
- 🔄 **Tracking Inteligente**: Rastreamento persistente de objetos entre frames
- 🌐 **Interface Web**: Interface HTML interativa para visualização
- ⚡ **API Escalável**: Serviço BentoML para deploy em produção
- 📊 **Anotações Visuais**: Bounding boxes, IDs de tracking e trilhas de movimento

## 🏗️ Arquitetura

```
┌─────────────────┐      WebSocket      ┌──────────────────┐
│  Web Interface  │ ◄─────────────────► │ WebSocket Server │
│  (HTML/JS)      │                     │  (Port 8765)     │
└─────────────────┘                     └──────────────────┘
                                               │ HTTP
                                               ▼
                                        ┌──────────────────┐
                                        │  BentoML Service │
                                        │  YOLOv8 Tracker  │
                                        │  (Port 3000)     │
                                        └──────────────────┘
```

## 🚀 Funcionalidades

### Detecção e Tracking
- ✅ Detecção de múltiplos objetos em tempo real
- ✅ Atribuição automática de IDs de tracking
- ✅ Histórico de movimento (trilhas visuais)
- ✅ Cálculo de confiança por detecção
- ✅ Suporte a múltiplas classes de objetos

### Comunicação
- ✅ Streaming via WebSocket assíncrono
- ✅ Processamento de frames em base64
- ✅ Sistema de sessões por cliente
- ✅ Estatísticas em tempo real
- ✅ Ping/pong para manter conexão

### Performance
- ✅ Processamento assíncrono (asyncio/aiohttp)
- ✅ Timeout configurável (30s)
- ✅ Gerenciamento de múltiplas conexões
- ✅ Histórico limitado de tracking (últimos 30 pontos)

## 📦 Instalação

### Pré-requisitos

- Python 3.8+
- CUDA (opcional, para GPU)
- Webcam ou fonte de vídeo

### Passo 1: Clonar o repositório

```bash
git clone https://github.com/seu-usuario/MOT_CEL.git
cd MOT_CEL
```

### Passo 2: Instalar dependências

```bash
pip install -r requirements.txt
```

### Passo 3: Verificar modelo YOLO

Certifique-se de que o arquivo `best.pt` (modelo treinado) está na raiz do projeto.

## 🎮 Como Usar

### Método 1: Servidor Completo (Recomendado)

#### 1. Iniciar o Serviço BentoML

```bash
bentoml serve yolo_service:YOLOService
```

O serviço estará disponível em `http://localhost:3000`

#### 2. Iniciar o Servidor WebSocket

Em outro terminal:

```bash
python websocket_server.py
```

O servidor WebSocket estará rodando em `ws://localhost:8765`

#### 3. Abrir a Interface Web

Abra o arquivo `web_interface.html` no navegador ou sirva-o com um servidor HTTP:

```bash
# Opção 1: Abrir diretamente
start web_interface.html

# Opção 2: Usar servidor HTTP Python
python -m http.server 8080
# Acesse: http://localhost:8080/web_interface.html
```

### Método 2: Deploy com BentoML

#### Construir o Bento

```bash
bentoml build
```

#### Servir o Bento

```bash
bentoml serve yolo-realtime-tracker:latest
```

#### Containerizar (Docker)

```bash
bentoml containerize yolo-realtime-tracker:latest
docker run -p 3000:3000 yolo-realtime-tracker:latest
```

## 📂 Estrutura do Projeto

```
MOT_CEL/
├── yolo_service.py          # Serviço BentoML com YOLOv8
├── websocket_server.py      # Servidor WebSocket para streaming
├── web_interface.html       # Interface web do usuário
├── best.pt                  # Modelo YOLO treinado
├── bentofile.yaml          # Configuração BentoML
├── requirements.txt        # Dependências Python
└── README.md              # Este arquivo
```

### Descrição dos Arquivos

| Arquivo | Descrição |
|---------|-----------|
| `yolo_service.py` | Implementa o serviço BentoML com detecção YOLOv8 e sistema de tracking |
| `websocket_server.py` | Servidor WebSocket assíncrono para streaming de vídeo em tempo real |
| `web_interface.html` | Interface web com captura de webcam e visualização de detecções |
| `best.pt` | Modelo YOLOv8 treinado (pesos da rede neural) |
| `bentofile.yaml` | Configuração para build e deploy do serviço BentoML |

## 🔧 Configurações

### WebSocket Server

```python
# websocket_server.py
BENTOML_SERVICE_URL = "http://localhost:3000"  # URL do BentoML
WEBSOCKET_PORT = 8765                          # Porta do WebSocket
```

### BentoML Service

```python
# yolo_service.py
MODEL_PATH = "best.pt"  # Caminho do modelo YOLO
```

### Resources (bentofile.yaml)

```yaml
python:
  packages:
    - bentoml>=1.2.0
    - ultralytics>=8.0.0
    - torch>=2.0.0

docker:
  system_packages:
    - ffmpeg
    - libgl1-mesa-glx
```

## 📊 API Reference

### Endpoint: `/process_video_frame`

Processa um frame de vídeo e retorna detecções.

**Request:**
```json
{
  "data": {
    "frame": "base64_encoded_image",
    "session_id": "unique_session_id",
    "return_annotated": true
  }
}
```

**Response:**
```json
{
  "detections": [
    {
      "bbox": [x1, y1, x2, y2],
      "confidence": 0.95,
      "class_id": 0,
      "class_name": "person",
      "track_id": 1
    }
  ],
  "frame_shape": [720, 1280],
  "timestamp": 1234567890.123,
  "session_id": "unique_session_id",
  "annotated_frame": "base64_encoded_annotated_image"
}
```

### Endpoint: `/get_model_info`

Retorna informações sobre o modelo.

**Response:**
```json
{
  "model_type": "YOLOv8",
  "classes": {"0": "person", "1": "car", ...},
  "num_classes": 10,
  "input_size": "Dynamic",
  "tracking_enabled": true
}
```

## 🛠️ Tecnologias Utilizadas

### Backend
- **[Python 3.8+](https://www.python.org/)**: Linguagem principal
- **[YOLOv8 (Ultralytics)](https://github.com/ultralytics/ultralytics)**: Detecção de objetos
- **[BentoML](https://www.bentoml.com/)**: Framework de ML serving
- **[OpenCV](https://opencv.org/)**: Processamento de imagens
- **[PyTorch](https://pytorch.org/)**: Framework de deep learning
- **[WebSockets](https://websockets.readthedocs.io/)**: Comunicação em tempo real
- **[aiohttp](https://docs.aiohttp.org/)**: Cliente HTTP assíncrono

### Frontend
- **HTML5**: Estrutura da página
- **JavaScript (ES6+)**: Lógica da aplicação
- **WebRTC**: Captura de vídeo da webcam
- **Canvas API**: Renderização de vídeo e anotações

## 🎯 Casos de Uso

- 🚗 **Monitoramento de Tráfego**: Contagem e tracking de veículos
- 👥 **Análise de Fluxo de Pessoas**: Contagem de pedestres em ambientes
- 🏭 **Segurança Industrial**: Detecção de EPIs e monitoramento de áreas
- 🏪 **Varejo**: Análise de comportamento de clientes
- 🎮 **Aplicações Interativas**: Jogos e experiências com detecção de objetos

## 🐛 Troubleshooting

### Erro: "Connection refused" ao conectar no BentoML

```bash
# Verifique se o serviço está rodando
curl http://localhost:3000/healthz

# Reinicie o serviço
bentoml serve yolo_service:YOLOService
```

### Erro: "Module not found"

```bash
# Reinstale as dependências
pip install -r requirements.txt --upgrade
```

### Webcam não funciona

- Verifique permissões do navegador
- Tente usar HTTPS (alguns navegadores exigem)
- Teste em outro navegador (Chrome recomendado)

### Performance lenta

- Use GPU com CUDA instalado
- Reduza a resolução do vídeo
- Ajuste o FPS na interface web
- Use modelo YOLO menor (yolov8n.pt em vez de yolov8x.pt)

## 📈 Melhorias Futuras

- [ ] Suporte a múltiplas câmeras simultâneas
- [ ] Gravação de vídeo com anotações
- [ ] Dashboard com estatísticas em tempo real
- [ ] Exportação de dados de tracking (CSV/JSON)
- [ ] Alertas personalizados por eventos
- [ ] Suporte a RTSP streams
- [ ] API REST completa
- [ ] Autenticação e controle de acesso

## 🤝 Contribuindo

Contribuições são bem-vindas! Siga os passos:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 👤 Autor

**Bruno**

- GitHub: [@seu-usuario](https://github.com/seu-usuario)

## 🙏 Agradecimentos

- [Ultralytics](https://github.com/ultralytics) pelo excelente framework YOLOv8
- [BentoML](https://www.bentoml.com/) pela plataforma de ML serving
- Comunidade open source de Computer Vision

---

⭐ **Se este projeto foi útil, deixe uma estrela!** ⭐

