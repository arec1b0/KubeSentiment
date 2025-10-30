# Troubleshooting Guide

This guide provides solutions to common issues you might encounter while deploying or using the Sentiment Analysis Microservice.

## Table of Contents
- [Common Issues](#common-issues)
- [Error Codes](#error-codes)
- [Performance Issues](#performance-issues)
- [Deployment Issues](#deployment-issues)
- [Model Issues](#model-issues)
- [Getting Help](#getting-help)

## Common Issues

### Service Fails to Start

**Symptoms**:
- The container exits immediately after starting
- Health checks are failing

**Possible Causes and Solutions**:
1. **Port Conflict**:
   ```bash
   Error: [Errno 98] error while attempting to bind on address ('0.0.0.0', 8000): address already in use
   ```
   - Solution: Change the port in your configuration or stop the service using the port

2. **Missing Dependencies**:
   ```bash
   ModuleNotFoundError: No module named 'torch'
   ```
   - Solution: Ensure all dependencies are installed (`pip install -r requirements.txt`)

3. **Permission Issues**:
   ```bash
   PermissionError: [Errno 13] Permission denied: '/app/model_cache'
   ```
   - Solution: Ensure the container has write permissions to the model cache directory

### Health Check Failures

**Symptoms**:
- `/health` endpoint returns non-200 status
- Kubernetes restarts the pod repeatedly

**Troubleshooting Steps**:
1. Check container logs:
   ```bash
   kubectl logs -l app=sentiment-service -n mlops-sentiment --tail=100
   ```

2. Check health endpoint manually:
   ```bash
   curl http://localhost:8000/health
   ```

3. Common issues:
   - Model download failure (check internet connectivity)
   - Insufficient memory (increase container resources)
   - Corrupted model cache (clear the cache directory)

## Error Codes

The API returns standardized error codes for easier troubleshooting:

| Error Code | HTTP Status | Description | Solution |
|------------|-------------|-------------|-----------|
| `TEXT_EMPTY` | 400 | Empty text provided | Ensure the request contains valid text |
| `TEXT_TOO_LONG` | 400 | Text exceeds maximum length | Reduce text length or increase MAX_TEXT_LENGTH |
| `MODEL_LOAD_ERROR` | 500 | Failed to load ML model | Check logs for details, verify model files |
| `PREDICTION_ERROR` | 500 | Error during prediction | Check input format, verify model compatibility |

## Performance Issues

### High Latency

**Symptoms**:
- Slow response times
- High CPU usage

**Solutions**:
1. **Enable Batching**:
   ```python
   # In your client code
   responses = []
   for batch in batch_texts(texts, batch_size=32):
       response = client.predict(batch)
       responses.extend(response)
   ```

2. **Optimize Model**:
   ```python
   # In your model loading code
   model = AutoModelForSequenceClassification.from_pretrained(
       model_name,
       torchscript=True  # Enable TorchScript optimization
   )
   model = torch.jit.trace(model, (dummy_input,))
   ```

3. **Scale Horizontally**:
   ```bash
   # Scale the deployment
   kubectl scale deployment/sentiment-service --replicas=3 -n mlops
   ```

### High Memory Usage

**Symptoms**:
- Container restarts due to OOM (Out of Memory)
- High memory usage in metrics

**Solutions**:
1. **Reduce Batch Size**:
   ```python
   # In your configuration
   INFERENCE_BATCH_SIZE = 16  # Reduce if needed
   ```

2. **Enable Gradient Checkpointing**:
   ```python
   model = AutoModelForSequenceClassification.from_pretrained(
       model_name,
       gradient_checkpointing=True
   )
   ```

3. **Use Mixed Precision**:
   ```python
   from torch.cuda.amp import autocast
   
   with autocast():
       outputs = model(**inputs)
   ```

## Deployment Issues

### Kubernetes Pods in CrashLoopBackOff

**Troubleshooting Steps**:
1. Describe the pod:
   ```bash
   kubectl describe pod -l app=sentiment-service -n mlops
   ```

2. Check events:
   ```bash
   kubectl get events -n mlops-sentiment --sort-by='.metadata.creationTimestamp'
   ```

3. Common issues:
   - Insufficient resources (CPU/memory)
   - Missing ConfigMaps or Secrets
   - Image pull errors

### Ingress Not Working

**Troubleshooting Steps**:
1. Check ingress controller:
   ```bash
   kubectl get ingress -n mlops
   kubectl describe ingress sentiment-ingress -n mlops
   ```

2. Check ingress controller logs:
   ```bash
   kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx
   ```

## Model Issues

### Model Fails to Load

**Symptoms**:
- Errors during model initialization
- Service starts but fails on first prediction

**Solutions**:
1. Clear the model cache:
   ```bash
   # In your Dockerfile
   RUN rm -rf /root/.cache/huggingface/hub/
   ```

2. Verify model files:
   ```python
   from transformers import AutoModelForSequenceClassification, AutoTokenizer
   
   # Test model loading
   model = AutoModelForSequenceClassification.from_pretrained('distilbert-base-uncased-finetuned-sst-2-english')
   tokenizer = AutoTokenizer.from_pretrained('distilbert-base-uncased-finetuned-sst-2-english')
   ```

### Poor Prediction Quality

**Symptoms**:
- Inconsistent or incorrect predictions
- Low confidence scores

**Solutions**:
1. **Text Preprocessing**:
   ```python
   def preprocess_text(text):
       # Add your preprocessing steps
       text = text.lower().strip()
       # Remove special characters, URLs, etc.
       return text
   ```

2. **Model Fine-tuning**:
   - Fine-tune on domain-specific data
   - Adjust hyperparameters (learning rate, batch size, etc.)

## Getting Help

If you encounter an issue not covered in this guide:

1. **Check Logs**:
   ```bash
   kubectl logs -l app=sentiment-service -n mlops-sentiment --tail=100
   ```

2. **Enable Debug Logging**:
   ```bash
   # Set log level to DEBUG
   LOG_LEVEL=DEBUG
   ```

3. **Open an Issue**:
   - Include error messages and logs
   - Describe steps to reproduce
   - Specify your environment (Kubernetes version, Docker version, etc.)

4. **Community Support**:
   - Check Stack Overflow for similar issues
   - Join our community forum

## Known Issues

### GPU Memory Fragmentation
**Description**: After running predictions for a while, GPU memory might become fragmented.
**Workaround**: Periodically restart the service or implement a memory cleanup routine.

### Cold Start Latency
**Description**: First prediction takes longer due to model initialization.
**Workaround**: Implement a warm-up routine during service startup.
