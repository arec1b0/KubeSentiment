# Development Environment Guide

## 🚀 Quick Start

### 1. **Environment Setup**
```bash
# The virtual environment is already created at: F:\Projects\MLOps\venv\
# Python version: 3.13.5
# All dependencies are installed
```

### 2. **Start Development Server**
```bash
python run.py
```

### 3. **Access the Service**
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

## 🧪 Testing

### Quick Test
```bash
python test_service.py
```

### Manual Testing
```bash
# Health check
curl -X GET "http://localhost:8000/health"

# Positive sentiment
curl -X POST "http://localhost:8000/predict" \
     -H "Content-Type: application/json" \
     -d '{"text": "I love this service!"}'

# Negative sentiment  
curl -X POST "http://localhost:8000/predict" \
     -H "Content-Type: application/json" \
     -d '{"text": "This is terrible"}'
```

## 📁 Project Structure

```
f:\Projects\MLOps\
├── .env                    # Environment variables
├── app/                    # Main application
│   ├── __init__.py         # Package init
│   ├── main.py            # FastAPI app & lifecycle
│   ├── config.py          # Configuration management
│   ├── api.py             # API endpoints
│   └── ml/                # ML modules
│       ├── __init__.py    
│       └── sentiment.py   # Sentiment analysis logic
├── venv/                  # Virtual environment
├── run.py                 # Development server launcher
├── test_service.py        # Test script
├── setup_dev.py          # Environment setup script
├── requirements.txt       # Dependencies
├── Dockerfile            # Container definition
└── README.md             # Documentation
```

## ⚙️ Configuration

### Environment Variables (.env file)
```bash
MLOPS_DEBUG=true                    # Enable debug mode
MLOPS_LOG_LEVEL=INFO               # Logging level
MLOPS_HOST=0.0.0.0                 # Server host
MLOPS_PORT=8000                    # Server port
MLOPS_ENABLE_METRICS=true          # Enable metrics
MLOPS_MODEL_NAME=distilbert-base-uncased-finetuned-sst-2-english
```

### Model Configuration
- **Model**: DistilBERT fine-tuned on SST-2
- **Input**: Text strings (max 512 chars)
- **Output**: POSITIVE/NEGATIVE with confidence score
- **Performance**: ~100ms response time

## 🔧 Development Workflow

### 1. **Code Changes**
- The server runs with hot reload enabled
- Changes to `app/` directory are automatically detected
- Browser refresh shows updated API docs

### 2. **Adding New Endpoints**
1. Add endpoint to `app/api.py`
2. Update Pydantic models if needed
3. Test via `/docs` interface

### 3. **Model Changes**
1. Update `app/ml/sentiment.py`
2. Modify `app/config.py` for new settings
3. Restart server to reload model

## 🐛 Troubleshooting

### Common Issues

**Import Errors**
```bash
# Reinstall dependencies
F:\Projects\MLOps\venv\Scripts\python.exe -m pip install -r requirements.txt
```

**Model Loading Issues**
- Check internet connection (model downloads from Hugging Face)
- Verify disk space (model ~268MB)
- Check logs for specific errors

**Port Already in Use**
```bash
# Change port in .env file
MLOPS_PORT=8001
```

**Performance Issues**
- Model loads on first startup (~30 seconds)
- Subsequent requests are fast (~100ms)
- CPU-only inference (no GPU required)

## 📊 Monitoring

### Health Check Response
```json
{
  "status": "healthy",
  "model_status": "available", 
  "version": "1.0.0",
  "timestamp": 1726251097.5
}
```

### Metrics Response
```json
{
  "torch_version": "2.5.1+cpu",
  "cuda_available": false,
  "cuda_memory_allocated_mb": 0.0,
  "cuda_memory_reserved_mb": 0.0,
  "cuda_device_count": 0
}
```

## 🚢 Deployment

### Local Container
```bash
docker build -t sentiment-service:1.0 .
docker run -d -p 8000:8000 sentiment-service:1.0
```

### Production Considerations
- Use `MLOPS_DEBUG=false` in production
- Set up proper logging aggregation
- Configure health checks for orchestrators
- Use process managers (gunicorn) for scaling
- Set up monitoring and alerting

## 📝 Next Steps

1. **Add Tests**: Create proper unit and integration tests
2. **Add CI/CD**: Set up automated testing and deployment
3. **Add Monitoring**: Integrate with Prometheus/Grafana
4. **Add Security**: API keys, rate limiting, input validation
5. **Add Documentation**: API specifications, deployment guides
