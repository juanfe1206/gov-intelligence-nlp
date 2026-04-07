# Deferred Work

## Deferred from: code review of 1-3-political-taxonomy-configuration (2026-04-07)

- No schema-level validation that `name` fields are lowercase with no spaces — real gap, but Story 1.5 (NLP classification) is the right enforcement point when names are used as DB values
- `tardà` uses non-ASCII character as a machine identifier in taxonomy.yaml — valid for now; should be addressed before any URL routing or DB key usage
- API tests assert specific taxonomy YAML content, not just structure — low-risk brittleness; tests will break on any taxonomy data change even if the API is correct
- `request.app.state.taxonomy` AttributeError if lifespan is bypassed in tests — current TestClient context manager usage guards against this; revisit if test patterns change
