# Definition of Done Checklist

**Story:** #<!-- story-id -->
**PR:** #<!-- pr-id -->
**Reviewer:** @<!-- username -->
**Date:** <!-- YYYY-MM-DD -->

---

## ✅ Code Quality

- [ ] All acceptance criteria met with evidence
- [ ] Code follows project conventions (PEP 8, type hints)
- [ ] No debug statements (print, commented code)
- [ ] No hardcoded values (use config/env vars)
- [ ] Error handling implemented
- [ ] Logging added for key operations

## ✅ Testing

- [ ] Unit tests written for each acceptance criterion
- [ ] Unit tests passing locally
- [ ] Integration tests added (if applicable)
- [ ] Integration tests passing
- [ ] Test coverage >80% for new code
- [ ] No regressions (existing tests still pass)

## ✅ Documentation

- [ ] README updated (if user-facing change)
- [ ] API docs updated (if API change)
- [ ] Inline comments for complex logic
- [ ] ADR created (if architectural decision)

## ✅ Security

- [ ] No secrets in code
- [ ] No SQL injection risks
- [ ] User inputs validated
- [ ] Appropriate access controls

## ✅ Performance

- [ ] No obvious performance issues
- [ ] Database queries optimized
- [ ] No memory leaks

## ✅ Process

- [ ] PR linked to story (`Closes #<id>`)
- [ ] Branch follows naming convention (`feature/<id>-<slug>`)
- [ ] Branch up to date with main
- [ ] Evidence mapping complete (criterion → test → location)
- [ ] Self-reviewed the diff

---

## Reviewer Sign-off

- [ ] **Reviewer:** @<!-- username --> - Approved `YYYY-MM-DD`

---

## CODEOWNER Pre-Merge Checklist

- [ ] All CI checks passing
- [ ] Required approvals obtained
- [ ] No merge conflicts
- [ ] **CODEOWNER:** @nsin08 - Merge authorized `YYYY-MM-DD`

---

**Framework:** space_framework - Rule 03 (Definition of Done)
