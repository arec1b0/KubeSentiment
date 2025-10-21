# Documentation Index

**Version:** 1.0.0  
**Last Updated:** October 21, 2025

Welcome to the MLOps Sentiment Analysis project documentation. This index provides a comprehensive guide to all available documentation.

---

## 📚 Core Documentation

### Getting Started

| Document | Description | Audience |
|----------|-------------|----------|
| [README.md](../README.md) | Project overview and quick start | All users |
| [QUICKSTART](setup/QUICKSTART.md) | 5-minute setup guide | New users |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Contribution guidelines | Contributors |

### Architecture & Design

| Document | Description | Audience |
|----------|-------------|----------|
| [ARCHITECTURE.md](../ARCHITECTURE.md) | Complete system architecture | Architects, Senior Engineers |
| [DEVELOPMENT.md](../DEVELOPMENT.md) | Development guide and workflows | Developers |
| [DEPLOYMENT.md](../DEPLOYMENT.md) | Deployment guide for all platforms | DevOps, SREs |

---

## 🛠️ Operational Guides

### Deployment & Infrastructure

| Document | Description | Audience |
|----------|-------------|----------|
| [KUBERNETES.md](KUBERNETES.md) | Kubernetes deployment guide | Platform Engineers |
| [CICD.md](../CICD.md) | CI/CD pipeline documentation | DevOps Engineers |
| [CICD_QUICK_REFERENCE.md](CICD_QUICK_REFERENCE.md) | CI/CD quick reference | All |

### Monitoring & Operations

| Document | Description | Audience |
|----------|-------------|----------|
| [MONITORING.md](MONITORING.md) | Monitoring and observability | SREs, Operations |
| [BENCHMARKING.md](BENCHMARKING.md) | Performance testing guide | Performance Engineers |
| [Troubleshooting](troubleshooting/index.md) | Common issues and solutions | All |

### Security

| Document | Description | Audience |
|----------|-------------|----------|
| [SECRETS.md](../.github/SECRETS.md) | Secret management with Vault | Security, DevOps |
| [VAULT_SETUP.md](setup/VAULT_SETUP.md) | Vault configuration | Platform Engineers |

---

## 👨‍💻 Development Resources

### Code Quality

| Document | Description | Audience |
|----------|-------------|----------|
| [CODE_QUALITY_SETUP.md](../CODE_QUALITY_SETUP.md) | Linting, formatting, testing | Developers |
| [DEVELOPMENT.md](../DEVELOPMENT.md) | Local development setup | Developers |

### Testing

| Document | Description | Audience |
|----------|-------------|----------|
| [tests/README.md](../tests/README.md) | Testing guide and conventions | QA, Developers |

---

## 📊 Reference Documentation

### API Documentation

| Resource | Description | Audience |
|----------|-------------|----------|
| [OpenAPI Spec](../openapi-specs/sentiment-api.yaml) | Complete API specification | API Consumers |
| [Swagger UI](http://localhost:8000/docs) | Interactive API docs | Developers |
| [ReDoc](http://localhost:8000/redoc) | Alternative API docs | Developers |

### Configuration

| Document | Description | Audience |
|----------|-------------|----------|
| [Environment Variables](../DEPLOYMENT.md#environment-configuration) | All configuration options | All |
| [Helm Values](../helm/mlops-sentiment/values.yaml) | Kubernetes configuration | Platform Engineers |

---

## 🎓 Tutorials & Examples

### Notebooks

| Notebook | Description | Audience |
|----------|-------------|----------|
| [01_getting_started.ipynb](../notebooks/01_getting_started.ipynb) | Basic usage | New users |
| [02_model_exploration.ipynb](../notebooks/02_model_exploration.ipynb) | Model internals | Data Scientists |
| [03_api_testing.ipynb](../notebooks/03_api_testing.ipynb) | API testing | QA |
| [04_benchmarking_analysis.ipynb](../notebooks/04_benchmarking_analysis.ipynb) | Performance analysis | Performance Engineers |
| [05_monitoring_metrics.ipynb](../notebooks/05_monitoring_metrics.ipynb) | Metrics exploration | SREs |
| [06_development_workflow.ipynb](../notebooks/06_development_workflow.ipynb) | Dev workflow | Developers |
| [07_deployment_guide.ipynb](../notebooks/07_deployment_guide.ipynb) | Deployment walkthrough | DevOps |

### Example Code

| Directory | Description | Audience |
|----------|-------------|----------|
| [benchmarking/examples/](../benchmarking/examples/) | Benchmarking examples | All |
| [serverless/](../serverless/) | Serverless deployment examples | Cloud Engineers |

---

## 🔍 Finding Documentation

### By Role

**New User:**
1. Start with [README.md](../README.md)
2. Follow [QUICKSTART](setup/QUICKSTART.md)
3. Explore [notebooks/01_getting_started.ipynb](../notebooks/01_getting_started.ipynb)

**Developer:**
1. Read [ARCHITECTURE.md](../ARCHITECTURE.md)
2. Setup using [DEVELOPMENT.md](../DEVELOPMENT.md)
3. Review [CODE_QUALITY_SETUP.md](../CODE_QUALITY_SETUP.md)
4. Check [CONTRIBUTING.md](../CONTRIBUTING.md)

**DevOps/SRE:**
1. Study [ARCHITECTURE.md](../ARCHITECTURE.md)
2. Follow [DEPLOYMENT.md](../DEPLOYMENT.md)
3. Setup [MONITORING.md](MONITORING.md)
4. Configure [CICD.md](../CICD.md)

**Architect:**
1. Review [ARCHITECTURE.md](../ARCHITECTURE.md)
2. Understand [KUBERNETES.md](KUBERNETES.md)
3. Plan with [DEPLOYMENT.md](../DEPLOYMENT.md)

### By Task

**I want to...**

- **Run locally**: [DEVELOPMENT.md](../DEVELOPMENT.md)
- **Deploy to Kubernetes**: [DEPLOYMENT.md](../DEPLOYMENT.md) → [KUBERNETES.md](KUBERNETES.md)
- **Set up CI/CD**: [CICD.md](../CICD.md)
- **Monitor in production**: [MONITORING.md](MONITORING.md)
- **Fix an issue**: [troubleshooting/index.md](troubleshooting/index.md)
- **Contribute code**: [CONTRIBUTING.md](../CONTRIBUTING.md)
- **Understand architecture**: [ARCHITECTURE.md](../ARCHITECTURE.md)
- **Configure secrets**: [SECRETS.md](../.github/SECRETS.md)
- **Run performance tests**: [BENCHMARKING.md](BENCHMARKING.md)

---

## 📝 Documentation Standards

### Writing Guidelines

All documentation should follow these standards:

1. **Clear Structure**: Use headers, tables, and lists
2. **Code Examples**: Provide runnable examples
3. **Target Audience**: Specify who should read it
4. **Up-to-date**: Review quarterly
5. **Version**: Include version and last updated date

### Requesting Updates

Found an issue or need clarification?

1. **Minor fixes**: Submit PR with changes
2. **Major changes**: Create issue for discussion
3. **Questions**: Ask in #mlops-docs Slack channel

### Contributing to Docs

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines on:

- Documentation style guide
- Pull request process
- Review requirements

---

## 🔄 Document Lifecycle

### Review Schedule

| Document | Frequency | Next Review |
|----------|-----------|-------------|
| ARCHITECTURE.md | Quarterly | January 2026 |
| DEVELOPMENT.md | Monthly | November 2025 |
| DEPLOYMENT.md | Monthly | November 2025 |
| KUBERNETES.md | Quarterly | January 2026 |
| CICD.md | Quarterly | January 2026 |
| All others | As needed | - |

### Version History

- **v1.0.0** (Oct 2025): Initial consolidated documentation
- **v0.9.0** (Sep 2025): Refactoring documentation
- **v0.8.0** (Aug 2025): CI/CD documentation added
- **v0.7.0** (Jul 2025): Initial documentation

---

## 📞 Support

### Getting Help

1. **Documentation**: Check this index first
2. **FAQs**: [troubleshooting/index.md](troubleshooting/index.md)
3. **Slack**: #mlops-help channel
4. **Email**: mlops-team@example.com
5. **Issues**: [GitHub Issues](https://github.com/arec1b0/mlops-sentiment/issues)

### Escalation Path

1. Team Lead → #mlops-help
2. Technical Issue → Create GitHub issue
3. Urgent Production → #production-alerts
4. Security Issue → security@example.com

---

## 🌟 Quick Links

**Most Popular:**
- [Quick Start](setup/QUICKSTART.md)
- [Architecture Overview](../ARCHITECTURE.md)
- [API Documentation](http://localhost:8000/docs)
- [Deployment Guide](../DEPLOYMENT.md)

**For Teams:**
- [Development Workflow](../DEVELOPMENT.md)
- [Code Quality Standards](../CODE_QUALITY_SETUP.md)
- [CI/CD Pipeline](../CICD.md)
- [Monitoring Setup](MONITORING.md)

---

**Maintained by**: Documentation Team  
**Last Review**: October 2025  
**Next Review**: January 2026

For documentation requests or improvements, contact #mlops-docs on Slack.
