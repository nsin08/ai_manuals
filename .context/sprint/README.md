# Sprint Context

**Purpose:** Sprint planning, retros, and execution artifacts  
**Location:** `.context/sprint/` (committed to version control)

---

## Sprint Cadence

* **Sprint Duration:** 2 weeks
* **Sprint Planning:** Monday Week 1
* **Sprint Review:** Friday Week 2
* **Sprint Retro:** Friday Week 2 (after review)

---

## Directory Structure

```
.context/sprint/
├── README.md                    # This file
├── sprint-01/
│   ├── plan.md                  # Sprint goals + stories
│   ├── retro.md                 # What went well/poorly
│   └── metrics.md               # Velocity, cycle time
├── sprint-02/
│   ├── plan.md
│   ├── retro.md
│   └── metrics.md
└── ...
```

---

## Naming Convention

* **Directories:** `sprint-NN/` (zero-padded, e.g., `sprint-01`, `sprint-10`)
* **Files:**
  * `plan.md` - Sprint goal, selected stories, assignments
  * `retro.md` - Retrospective notes (what went well, what to improve, action items)
  * `metrics.md` - Sprint metrics (velocity, cycle time, completion rate)

---

## Sprint Planning Template

Create a new directory for each sprint:

```bash
mkdir -p .context/sprint/sprint-NN
```

**`plan.md` template:**

```markdown
# Sprint NN Plan

**Sprint Goal:** [One sentence describing the sprint objective]

**Duration:** YYYY-MM-DD to YYYY-MM-DD

## Selected Stories

| ID | Title | Points | Assignee | Status |
|----|-------|--------|----------|--------|
| #X | Story title | N | @user | Ready |

## Sprint Capacity

* Total capacity: NN points
* Committed: NN points
* Team members: N

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Tests written and passing
- [ ] Code reviewed and approved
- [ ] Documentation updated
- [ ] Merged to main

---

**Created:** YYYY-MM-DD
```

**`retro.md` template:**

```markdown
# Sprint NN Retrospective

**Date:** YYYY-MM-DD  
**Participants:** @user1, @user2, @user3

## What Went Well

* 
* 

## What Could Be Improved

* 
* 

## Action Items

| Action | Owner | Due Date |
|--------|-------|----------|
| | | |

---

**Next Sprint Adjustments:**

* 
```

---

## Usage Guidelines

### When to Add Documents Here

- **Sprint plans** at the start of each sprint
- **Retrospectives** at the end of each sprint
- **Metrics** tracked during/after sprint

### When NOT to Add Here

- **Project-wide decisions** → use `.context/project/`
- **Temporary notes** → use `.context/temp/`
- **Issue-specific work** → use `.context/issues/`

---

## Metrics to Track

* **Velocity:** Story points completed per sprint
* **Cycle Time:** Days from "In Progress" to "Done"
* **Completion Rate:** % of committed stories completed
* **Rework Rate:** % of stories returned for changes

---

**Framework:** space_framework  
**Last Updated:** 2026-02-17
