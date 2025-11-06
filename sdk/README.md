# KubeSentiment SDKs

Official client libraries for KubeSentiment API in Python and JavaScript/TypeScript.

## Available SDKs

### Python SDK
- **Location**: `python/kubesentiment_sdk.py`
- **Python Version**: 3.7+
- **Dependencies**: `requests`
- **Type Hints**: Fully typed with dataclasses

### JavaScript/TypeScript SDK
- **Location**: `javascript/kubesentiment-sdk.ts`
- **Runtime**: Node.js 14+ or modern browsers
- **Dependencies**: None (uses native `fetch`)
- **Type Safety**: Full TypeScript support

## Quick Start

### Python

```python
from kubesentiment_sdk import KubeSentimentClient

client = KubeSentimentClient(base_url="http://localhost:8000")
result = client.predict("This is amazing!")
print(f"{result.label}: {result.confidence:.2%}")
```

### TypeScript/JavaScript

```typescript
import { KubeSentimentClient } from './kubesentiment-sdk';

const client = new KubeSentimentClient({ baseUrl: 'http://localhost:8000' });
const result = await client.predict('This is amazing!');
console.log(`${result.label}: ${(result.confidence * 100).toFixed(2)}%`);
```

## Features

Both SDKs provide:
- ✅ Single predictions
- ✅ Batch predictions (sync and async)
- ✅ Job status polling
- ✅ Model information
- ✅ Health checks
- ✅ Metrics retrieval
- ✅ Drift detection summaries
- ✅ Business KPIs
- ✅ Type safety
- ✅ Error handling
- ✅ Timeout configuration

## Documentation

See [QUICK_WINS_FEATURES.md](../docs/QUICK_WINS_FEATURES.md) for complete documentation and examples.

## License

MIT
