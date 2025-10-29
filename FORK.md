# Aether Kestrel Fork

## Why This Fork Exists

The Aether team is building a modern threat hunting platform and needs an actively maintained, high-performance version of Kestrel. While we deeply respect the original `opencybersecurityalliance/kestrel-lang` project, it has been **inactive since 2024** with no recent releases or issue responses.

Rather than let this excellent threat hunting language stagnate, we're committed to:

1. **Active maintenance** - Monthly releases minimum, issue response within 48-72 hours
2. **Modern Python support** - Python 3.10+ with latest type hints and performance improvements
3. **High-performance analytics** - Polars DataFrames, DuckDB, and Ibis for blazing-fast data processing
4. **Declarative playbooks** - YAML-based hunt playbooks for easier sharing and automation
5. **Community-first development** - Transparent roadmap, welcoming contributions

## Our Commitment

### Development Principles

- ✅ **Maintain backward compatibility** - Existing Kestrel huntbooks work unchanged
- ✅ **Contribute upstream when possible** - We'll submit PRs to original project if it becomes active
- ✅ **Transparent governance** - Public roadmap, regular releases, community input
- ✅ **Production quality** - Comprehensive tests, CI/CD, proper versioning
- ✅ **Open source** - Apache 2.0 license maintained, community contributions welcome

### Release Cadence

- **Monthly releases minimum** - Bug fixes, dependency updates, security patches
- **Quarterly feature releases** - New analytics capabilities, performance improvements
- **Immediate security patches** - Critical vulnerabilities addressed within 24 hours

### Community Support

- **GitHub Issues** - Response within 48-72 hours
- **GitHub Discussions** - Active community engagement
- **Documentation** - Maintained and updated with each release
- **Examples** - Real-world hunt playbooks and analytics

## Differences from Upstream

See [DIFFERENCES.md](DIFFERENCES.md) for detailed comparison.

**Summary:**

| Feature | Upstream (v2.0.0b) | Aether Fork |
|---------|-------------------|-------------|
| Python Support | 3.8+ | 3.10+ (3.8 EOL) |
| DataFrames | Pandas only | Pandas + Polars |
| Analytics | Python functions | Python + Ibis/DuckDB |
| Playbooks | Kestrel code only | Kestrel + YAML |
| Releases | Stale (2024) | Monthly minimum |
| Issue Response | Inactive | 48-72 hours |
| Test Coverage | ~70% | >85% target |

## Roadmap

### Current: v2.0.0b (inherited)

Starting point from upstream.

### v2.1.0-aether.1 (Target: December 2025)

**Foundation modernization:**
- Python 3.10, 3.11, 3.12 support (drop 3.8, 3.9)
- Updated dependencies (pandas, SQLAlchemy, etc.)
- Polars DataFrame support (opt-in, backward compatible)
- Improved error messages
- 100% test pass rate on all supported Python versions
- CI/CD pipeline with multi-version testing

### v2.2.0-aether.1 (Target: February 2026)

**Advanced analytics:**
- Ibis analytics interface
- DuckDB integration for high-performance queries
- Polars-native analytics support
- Analytics registry and discovery
- Performance benchmarks and optimizations

### v2.3.0-aether.1 (Target: April 2026)

**Declarative playbooks:**
- YAML playbook support
- Playbook validation and testing
- Playbook library and templates
- CLI enhancements for playbook execution
- Jupyter integration improvements

### v3.0.0-aether.1 (Target: Q3 2026)

**Major enhancements:**
- Breaking changes if needed (with migration guide)
- Advanced caching and persistence
- Distributed execution support
- Enhanced STIX integration
- ML/AI analytics framework

## Getting Started

### For Existing Kestrel Users

**Drop-in replacement:**

```bash
# Uninstall original (if installed)
pip uninstall kestrel_core

# Install Aether fork
pip install aether-kestrel-core
```

Your existing huntbooks work unchanged. New features are opt-in.

### For New Users

```bash
# Install
pip install aether-kestrel-core

# Run interactive shell
ikestrel

# Or execute huntflow
kestrel -f my_hunt.hf
```

See [documentation](https://docs.aether-threat-hunting.com/kestrel) for tutorials.

### For Contributors

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md).

**Priority areas:**
- Analytics development (see `packages/kestrel_core/src/kestrel/analytics/`)
- Data source interfaces (see `packages/kestrel_interface_*/`)
- Documentation and examples
- Test coverage improvements

## Maintainers

See [MAINTAINERS.md](MAINTAINERS.md) for current maintainer team.

**Primary contacts:**
- Jules <jules@aether-security.com> - Lead maintainer
- Technical discussions: GitHub Discussions
- Security issues: security@aether-security.com (private)

## Relationship with Upstream

We respect and acknowledge the original `opencybersecurityalliance/kestrel-lang` project. This fork exists because:

1. **No activity since 2024** - No commits, releases, or issue responses
2. **Community needs active maintenance** - Security updates, bug fixes, modernization
3. **Innovation needed** - Modern analytics, performance, usability improvements

**If upstream becomes active again:**
- We'll gladly contribute our improvements back
- We'll coordinate to avoid ecosystem fragmentation
- We'll merge beneficial changes from upstream

Until then, we're committed to being the **actively maintained** Kestrel implementation.

## License

Apache 2.0 License - same as upstream. See [LICENSE.md](LICENSE.md).

## Acknowledgments

Huge thanks to the original Kestrel team:
- Xiaokui Shu
- Paul Coccoli
- All contributors to opencybersecurityalliance/kestrel-lang

This fork builds on their excellent foundation. We're honored to carry the torch forward.

---

**Join us in building the future of threat hunting!**

- GitHub: https://github.com/mikeyasaservice/kestrel-lang
- Docs: https://docs.aether-threat-hunting.com/kestrel
- Community: GitHub Discussions
