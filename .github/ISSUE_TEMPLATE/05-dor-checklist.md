# Definition of Ready Checklist

**Story:** #<!-- story-id -->
**Epic:** #<!-- epic-id -->
**Tech Lead:** @<!-- username -->
**Date:** <!-- YYYY-MM-DD -->

---

## ✅ Ready to Start Implementation

### Story Quality

- [ ] User story follows format: "As a [role], I want [action], so that [benefit]"
- [ ] Acceptance criteria are specific and measurable
- [ ] Acceptance criteria are testable
- [ ] Non-goals explicitly listed (what's out of scope)

### Technical Clarity

- [ ] Technical approach documented
- [ ] Components/files affected identified
- [ ] Integration points defined
- [ ] Test approach specified (unit/integration/e2e)

### Dependencies

- [ ] All blocking issues identified and linked
- [ ] External dependencies documented
- [ ] Required data/services available

### Estimation

- [ ] Story pointed (1-8 points; >8 → split)
- [ ] Effort estimate realistic for one sprint

### Architecture

- [ ] Architect reviewed (if architectural change)
- [ ] No known technical blockers
- [ ] Fits within existing architecture patterns

---

## ✅ Examples

**Good Acceptance Criterion:**
```
Given a user uploads a PDF file,
When the file size is under 50MB,
Then the system ingests the file and returns a document ID within 30 seconds.
```

**Bad Acceptance Criterion:**
```
The system should handle PDFs.  ❌ (not specific/measurable)
```

---

## Tech Lead Sign-Off

- [ ] **Tech Lead:** @<!-- username --> - Approved `YYYY-MM-DD`

---

## Transition

When all items checked:
1. Add label `state:ready`
2. Remove label `state:approved`
3. Story moves to backlog for assignment

---

**Framework:** space_framework - Rule 02 (Definition of Ready)
