# GitHub Setup Commands

This document contains the commands to complete the space_framework setup for the ai_manuals repository.

---

## 1. Create Repository Labels (Rule 12)

Run these commands to create the canonical label set:

```bash
# Navigate to repo
cd d:\wsl_shared\projects\ai_maunuals

# State labels (workflow states)
gh label create "state:idea" --description "Initial submission" --color "E99695" --force
gh label create "state:approved" --description "Business value confirmed" --color "F9D0C4" --force
gh label create "state:ready" --description "Ready for implementation" --color "C2E0C6" --force
gh label create "state:in-progress" --description "Active development" --color "BFD4F2" --force
gh label create "state:in-review" --description "Code review active" --color "D4C5F9" --force
gh label create "state:done" --description "Complete, merged" --color "0E8A16" --force
gh label create "state:released" --description "Deployed to production" --color "5319E7" --force
gh label create "state:rejected" --description "Not proceeding" --color "D93F0B" --force
gh label create "state:blocked" --description "Waiting on dependency" --color "FBCA04" --force
gh label create "state:on-hold" --description "Paused" --color "CCCCCC" --force

# Type labels (artifact types)
gh label create "type:idea" --description "Initial feature request" --color "E99695" --force
gh label create "type:epic" --description "Large feature" --color "3E4B9E" --force
gh label create "type:story" --description "Implementable work unit" --color "0075CA" --force
gh label create "type:task" --description "Technical task" --color "D4C5F9" --force
gh label create "type:bug" --description "Something broken" --color "D73A4A" --force
gh label create "type:feature-request" --description "User-submitted request" --color "A2EEEF" --force

# Priority labels
gh label create "priority:critical" --description "Blocking/urgent" --color "D93F0B" --force
gh label create "priority:high" --description "Important" --color "FBCA04" --force
gh label create "priority:medium" --description "Normal" --color "FEF2C0" --force
gh label create "priority:low" --description "Nice to have" --color "C5DEF5" --force

# Role labels (optional - for assignment tracking)
gh label create "role:client" --description "Client/Sponsor work" --color "F9D0C4" --force
gh label create "role:po" --description "Product Owner work" --color "C2E0C6" --force
gh label create "role:architect" --description "Architecture work" --color "BFD4F2" --force
gh label create "role:implementer" --description "Developer work" --color "D4C5F9" --force
gh label create "role:reviewer" --description "Review work" --color "E4E669" --force
gh label create "role:devops" --description "DevOps work" --color "5319E7" --force
```

---

## 2. Branch Protection Setup (Lightweight - Not Strict)

### Option A: Using GitHub CLI (Recommended)

```bash
# Enable branch protection for main (lightweight settings)
gh api -X PUT /repos/nsin08/ai_manuals/branches/main/protection \
  -f required_status_checks='{"strict":false,"contexts":[]}' \
  -f enforce_admins=false \
  -f required_pull_request_reviews='{"required_approving_review_count":1,"require_code_owner_reviews":true}' \
  -f restrictions=null
```

**What this does:**
- Requires 1 approval before merge
- Requires Code Owner review (@nsin08)
- Does NOT require branch to be up-to-date (not strict)
- Does NOT enforce for admins (you can bypass if needed)
- No required status checks initially

### Option B: Using GitHub Web UI

1. Go to: https://github.com/nsin08/ai_manuals/settings/branches
2. Click "Add rule" or "Add branch protection rule"
3. Branch name pattern: `main`
4. Enable these settings:
   - ✅ Require a pull request before merging
     - ✅ Require approvals: 1
     - ✅ Require review from Code Owners
   - ⬜ Require status checks to pass before merging (leave unchecked for now)
   - ⬜ Require branches to be up to date before merging (leave unchecked - not strict)
   - ⬜ Do not allow bypassing the above settings (leave unchecked - you can bypass)
5. Click "Create" or "Save changes"

---

## 3. Verify Setup

```bash
# Verify labels were created
gh label list --limit 50

# Verify branch protection (should show protection rules)
gh api /repos/nsin08/ai_manuals/branches/main/protection
```

---

## 4. Next Steps

1. ✅ Labels created
2. ✅ Branch protection configured (lightweight)
3. Push initial commit to main
4. Create first Issue using templates
5. Test workflow

---

## 5. Optional: Enable GitHub Actions

If you created workflows:

1. Go to: https://github.com/nsin08/ai_manuals/settings/actions
2. Enable "Allow all actions and reusable workflows"
3. Save

---

## Notes

- **User requested:** "dont add strict branch protection rules"
- **Implementation:** Branch protection is enabled but NOT strict:
  - You can bypass as admin
  - Branch doesn't need to be up-to-date
  - No required status checks initially
- **When to make stricter:** When CI/CD workflows are ready and tested

---

**Framework:** space_framework  
**Last Updated:** 2026-02-17
