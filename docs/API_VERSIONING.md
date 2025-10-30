# API Versioning Strategy

This document outlines the API versioning approach used in KubeSentiment and provides guidance for API consumers and contributors.

## Versioning Approach

KubeSentiment uses **URL-based versioning** with the `/api/v1` prefix for all production endpoints.

### Version Prefix

- **Production**: All API endpoints are prefixed with `/api/v1`
  - Example: `/api/v1/predict`, `/api/v1/health`, `/api/v1/metrics`

- **Development**: Debug mode (`MLOPS_DEBUG=true`) omits the version prefix for easier local testing
  - Example: `/predict`, `/health`, `/metrics`

### Implementation

The version prefix is conditionally applied in `app/main.py`:

```python
# Include API router with conditional versioning
app.include_router(router, prefix="/api/v1" if not settings.debug else "")
```

## Current API Version

**Version:** `v1`
**Status:** Stable
**Release Date:** 2024-01-01

## Endpoint Structure

All v1 endpoints follow this structure:

```
/api/v1/<resource>/<action>
```

### Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/predict` | POST | Single text sentiment prediction |
| `/api/v1/batch/predict` | POST | Submit batch prediction job |
| `/api/v1/batch/status/{job_id}` | GET | Check batch job status |
| `/api/v1/batch/results/{job_id}` | GET | Retrieve batch job results |
| `/api/v1/health` | GET | Service health check |
| `/api/v1/metrics` | GET | Prometheus metrics |
| `/api/v1/model-info` | GET | Model metadata |

## Backward Compatibility

### Guarantees

- **Minor version updates** (e.g., v1.1, v1.2) maintain backward compatibility
- **Breaking changes** require a new major version (e.g., v2)
- **Deprecation period**: Minimum 6 months notice before removing deprecated endpoints

### Deprecation Process

1. **Announcement**: Deprecated endpoints are marked in documentation
2. **Headers**: Response includes `X-API-Deprecated: true` header
3. **Logging**: Deprecation warnings logged for tracking usage
4. **Timeline**: 6-month minimum before removal

Example deprecation header:

```
X-API-Deprecated: true
X-API-Deprecation-Date: 2024-07-01
X-API-Sunset-Date: 2025-01-01
X-API-Replacement: /api/v2/predict
```

## Versioning for New Features

### Adding New Endpoints

New endpoints can be added to existing versions without breaking compatibility:

```python
# New endpoint in v1
@router.post("/api/v1/analyze")
async def analyze_sentiment_advanced(...):
    pass
```

### Modifying Existing Endpoints

**Non-Breaking Changes (Allowed in same version):**
- Adding optional parameters
- Adding new response fields
- Improving error messages
- Performance optimizations

**Breaking Changes (Require new version):**
- Removing required parameters
- Changing parameter types
- Removing response fields
- Changing authentication methods

## Version Migration Guide

### From v1 to v2 (Future)

When v2 is released, this section will include:

1. **What's Changed**: List of breaking changes
2. **Migration Steps**: How to update client code
3. **Compatibility Layer**: Temporary bridges between versions
4. **Timeline**: Deprecation schedule for v1

### Example Migration

```python
# v1 (Current)
POST /api/v1/predict
{
  "text": "I love this product!"
}

# v2 (Hypothetical future version)
POST /api/v2/analyze
{
  "content": "I love this product!",
  "options": {
    "include_confidence": true,
    "language": "en"
  }
}
```

## Client Recommendations

### Version Pinning

Always specify the API version in your client code:

```python
# Good: Version specified
BASE_URL = "https://api.example.com/api/v1"

# Bad: No version (may break)
BASE_URL = "https://api.example.com"
```

### Error Handling

Handle version-related errors gracefully:

```python
response = requests.post(f"{BASE_URL}/predict", json={"text": text})

if response.status_code == 410:  # Gone - endpoint removed
    # Fallback or migrate to new version
    pass
elif "X-API-Deprecated" in response.headers:
    # Log warning, plan migration
    logger.warning(f"Using deprecated API. Sunset: {response.headers['X-API-Sunset-Date']}")
```

### Stay Informed

- Subscribe to API changelog: [CHANGELOG.md](../CHANGELOG.md)
- Monitor deprecation headers in responses
- Test against staging environment before major updates

## API Evolution Best Practices

### For Maintainers

1. **Semantic Versioning**: Use semantic versioning for API contracts
2. **Documentation**: Update API docs with each change
3. **Testing**: Maintain integration tests for all versions
4. **Monitoring**: Track usage of deprecated endpoints
5. **Communication**: Announce breaking changes early

### For Contributors

When adding API changes:

1. Check if it's a breaking change
2. Update OpenAPI specification
3. Add integration tests
4. Document in changelog
5. Update this versioning guide

## OpenAPI Specification

The API is documented using OpenAPI 3.0 specification:

- **Interactive Docs**: Available at `/docs` (Swagger UI)
- **Alternative Docs**: Available at `/redoc` (ReDoc)
- **OpenAPI JSON**: Available at `/openapi.json`

```bash
# Access API documentation
curl http://localhost:8000/openapi.json

# Interactive testing
open http://localhost:8000/docs
```

## Version Detection

Clients can detect the API version from:

1. **URL Path**: `/api/v1/...`
2. **Response Header**: `X-API-Version: 1.0`
3. **Model Info Endpoint**: `GET /api/v1/model-info`

Example response:

```json
{
  "api_version": "1.0",
  "model_name": "distilbert-base-uncased-finetuned-sst-2-english",
  "model_version": "1.0.0",
  "supported_languages": ["en"]
}
```

## Frequently Asked Questions

### Why URL-based versioning?

URL-based versioning (`/api/v1/`) is:
- Clear and explicit
- Easy to route and cache
- Widely supported by API gateways
- Discoverable in documentation

### Can I use multiple versions simultaneously?

Yes! The service can run multiple API versions concurrently:

```python
# v1 routes
app.include_router(v1_router, prefix="/api/v1")

# v2 routes (future)
app.include_router(v2_router, prefix="/api/v2")
```

### How do I test beta features?

Beta features may be available under:
- `/api/v1/beta/...` - Beta endpoints in current version
- `/api/v2-beta/...` - Preview of next major version

These are not covered by stability guarantees.

### What about GraphQL or gRPC?

Currently, KubeSentiment uses REST API with JSON. Future versions may support:
- GraphQL for flexible querying
- gRPC for high-performance streaming

## Monitoring API Usage

Track API version usage with Prometheus metrics:

```promql
# Requests by API version
rate(http_requests_total{endpoint=~"/api/v1/.*"}[5m])

# Deprecated endpoint usage
rate(http_requests_total{deprecated="true"}[5m])
```

## References

- [Semantic Versioning](https://semver.org/)
- [REST API Versioning Best Practices](https://restfulapi.net/versioning/)
- [OpenAPI Specification](https://swagger.io/specification/)
- [Architecture Documentation](../architecture.md)

## Change History

| Version | Release Date | Status | Notes |
|---------|--------------|--------|-------|
| v1 | 2024-01-01 | Stable | Initial release |

---

**Last Updated:** 2025-10-30
**Maintained By:** KubeSentiment Team
