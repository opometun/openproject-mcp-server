# Testing Checklist for add_comment Implementation

## Unit Tests (`test_add_comment.py`)

### ✅ Success Cases
- [ ] `test_add_comment_success` - Verify 201 response returns activity data
- [ ] `test_add_comment_with_notify` - Verify notify=true sends notifications
- [ ] `test_add_comment_markdown_formatting` - Verify markdown is preserved

### ✅ Error Handling
- [ ] `test_add_comment_401_raises_auth_error` - AuthError on 401
- [ ] `test_add_comment_403_raises_permission_error` - PermissionError on 403
- [ ] `test_add_comment_404_raises_not_found` - NotFound on 404
- [ ] `test_add_comment_422_raises_validation_error` - ValidationError on 422

### ✅ Input Validation
- [ ] `test_add_comment_validates_input` - Pydantic validation for invalid inputs
- [ ] `test_add_comment_sanitizes_error_messages` - No secret leakage in errors

### ✅ Edge Cases
- [ ] Long comment text handling
- [ ] Special characters in markdown
- [ ] Empty notify parameter defaults to false

## Integration Tests

### Manual Testing Checklist
Run against real OpenProject instance:

```bash
# Set up test environment
export OPENPROJECT_URL="https://test.openproject.com"
export OPENPROJECT_API_KEY="test_key_here"

# Run specific test
pytest tests/test_add_comment.py::test_add_comment_success -v
```

- [ ] Add comment to existing work package
- [ ] Add comment with notify=true triggers email
- [ ] Verify comment appears in work package activity stream
- [ ] Test with markdown formatting (bold, lists, links)

## Coverage Goals

Target: 100% coverage for `add_comment` function

```bash
pytest tests/test_add_comment.py --cov=src/openproject_mcp/tools/work_packages --cov-report=html
```

- [ ] All lines covered
- [ ] All branches covered (if/else, try/except)
- [ ] All error paths tested

## Pre-Merge Checklist

- [ ] All unit tests pass
- [ ] Coverage > 90%
- [ ] Linting passes (`ruff check`)
- [ ] Formatting passes (`black --check`)
- [ ] Type checking passes (`mypy`)
- [ ] Manual smoke test completed
- [ ] Documentation updated in README.md
- [ ] CHANGELOG.md updated
