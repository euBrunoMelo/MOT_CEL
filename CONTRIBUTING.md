# 🤝 Guia de Contribuição

Obrigado por considerar contribuir com o MOT_CEL! Este documento fornece diretrizes para contribuir com o projeto.

## 📋 Como Contribuir

### 1. Reportar Bugs

Se encontrar um bug, abra uma [issue](../../issues) incluindo:

- **Descrição clara** do problema
- **Passos para reproduzir** o erro
- **Comportamento esperado** vs **comportamento observado**
- **Ambiente**: SO, versão do Python, GPU/CPU
- **Logs de erro** (se aplicável)
- **Screenshots** (se relevante)

### 2. Sugerir Melhorias

Para sugerir novas funcionalidades:

- Verifique se já não existe uma issue similar
- Descreva o problema que a feature resolve
- Explique como a feature deveria funcionar
- Forneça exemplos de uso

### 3. Contribuir com Código

#### Setup do Ambiente de Desenvolvimento

```bash
# 1. Fork o repositório no GitHub

# 2. Clone seu fork
git clone https://github.com/seu-usuario/MOT_CEL.git
cd MOT_CEL

# 3. Adicione o repositório original como upstream
git remote add upstream https://github.com/usuario-original/MOT_CEL.git

# 4. Crie um ambiente virtual
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate

# 5. Instale dependências de desenvolvimento
pip install -r requirements.txt
pip install black flake8 pytest
```

#### Workflow de Desenvolvimento

1. **Crie uma branch** para sua feature:
   ```bash
   git checkout -b feature/nome-da-feature
   ```

2. **Faça suas alterações** seguindo as diretrizes de código

3. **Teste suas mudanças**:
   ```bash
   # Execute testes
   pytest tests/
   
   # Verifique formatação
   black .
   flake8 .
   ```

4. **Commit suas mudanças**:
   ```bash
   git add .
   git commit -m "feat: adiciona nova funcionalidade X"
   ```

5. **Mantenha sua branch atualizada**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

6. **Push para seu fork**:
   ```bash
   git push origin feature/nome-da-feature
   ```

7. **Abra um Pull Request** no GitHub

## 📝 Diretrizes de Código

### Estilo de Código

- Siga [PEP 8](https://pep8.org/) para Python
- Use [Black](https://github.com/psf/black) para formatação automática
- Máximo de 100 caracteres por linha
- Use type hints quando possível

**Exemplo:**

```python
def process_frame(frame: np.ndarray, session_id: str) -> Dict[str, Any]:
    """
    Processa um frame de vídeo.
    
    Args:
        frame: Frame de vídeo como numpy array
        session_id: ID único da sessão
        
    Returns:
        Dicionário com resultados da detecção
    """
    pass
```

### Convenções de Nomenclatura

- **Variáveis e funções**: `snake_case`
- **Classes**: `PascalCase`
- **Constantes**: `UPPER_SNAKE_CASE`
- **Arquivos**: `snake_case.py`

### Documentação

- Docstrings para todas as funções públicas
- Comentários em código complexo
- Atualize o README se adicionar features

### Mensagens de Commit

Use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` Nova funcionalidade
- `fix:` Correção de bug
- `docs:` Apenas documentação
- `style:` Formatação, sem mudança de código
- `refactor:` Refatoração de código
- `test:` Adicionar ou modificar testes
- `chore:` Tarefas de manutenção

**Exemplos:**
```
feat: adiciona suporte a múltiplas câmeras
fix: corrige erro de timeout no WebSocket
docs: atualiza guia de instalação
```

## 🧪 Testes

### Executar Testes

```bash
# Todos os testes
pytest

# Testes específicos
pytest tests/test_yolo_service.py

# Com cobertura
pytest --cov=.
```

### Escrever Testes

- Adicione testes para novas funcionalidades
- Mantenha cobertura de código acima de 80%
- Use fixtures para setup comum

**Exemplo:**

```python
def test_process_video_frame():
    service = YOLOService()
    frame_data = encode_test_image()
    
    result = service.process_video_frame({
        "frame": frame_data,
        "session_id": "test"
    })
    
    assert "detections" in result
    assert isinstance(result["detections"], list)
```

## 🔍 Code Review

### Critérios de Aprovação

- ✅ Código segue as diretrizes
- ✅ Testes passam
- ✅ Cobertura de código mantida/aumentada
- ✅ Documentação atualizada
- ✅ Sem conflitos com main
- ✅ Commits bem descritos

### Processo de Review

1. Mantenedores revisarão seu PR
2. Podem solicitar mudanças
3. Faça ajustes e atualize o PR
4. PR será mesclado após aprovação

## 🎯 Áreas Prioritárias

Contribuições são especialmente bem-vindas em:

- 📊 **Dashboard de Estatísticas**: Interface para métricas em tempo real
- 🎥 **Suporte a RTSP**: Streaming de câmeras IP
- 📝 **Exportação de Dados**: CSV/JSON com dados de tracking
- 🔔 **Sistema de Alertas**: Notificações por eventos
- 🧪 **Testes**: Aumentar cobertura de testes
- 📚 **Documentação**: Tutoriais e exemplos

## ❓ Perguntas

Tem dúvidas? Abra uma [Discussion](../../discussions) ou entre em contato!

## 📜 Código de Conduta

- Seja respeitoso e profissional
- Aceite críticas construtivas
- Foque no que é melhor para a comunidade
- Mostre empatia com outros contribuidores

---

**Obrigado por contribuir! 🎉**

