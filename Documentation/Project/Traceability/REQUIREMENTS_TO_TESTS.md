# Requirements to Tests Traceability

Map each requirement to regression coverage.

| Requirement ID | Test Files | Validation Command | Notes |
|----------------|------------|--------------------|-------|
| REQ-101 | tests/test_cloud_api_parsing.py, tests/test_batch_end_to_end_simulated.py | python run_ci_tests.py | Covers analysis extraction, recommendation rules, and batch persistence behavior |
