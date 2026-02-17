# Space Framework Setup - Verification & File Tree

**Repository:** https://github.com/nsin08/ai_manuals  
**Project:** Equipment Manuals Chatbot  
**Date:** 2026-02-17

---

## Expected File Tree

```
d:\wsl_shared\projects\ai_maunuals\
├── .github/
│   ├── CODEOWNERS                           ✅ Created
│   ├── copilot-instructions.md              ✅ Created
│   ├── pull_request_template.md             ✅ Created
│   ├── SETUP_COMMANDS.md                    ✅ Created (label + branch protection commands)
│   ├── ISSUE_TEMPLATE/
│   │   ├── 01-idea.md                       ✅ Created
│   │   ├── 02-epic.md                       ✅ Created
│   │   ├── 03-story.md                      ✅ Created
│   │   ├── 04-task.md                       ✅ Created
│   │   ├── 05-dor-checklist.md              ✅ Created
│   │   ├── 06-dod-checklist.md              ✅ Created
│   │   └── 07-feature-request.md            ✅ Created
│   └── workflows/
│       └── README.md                        ✅ Created (instructions for copying workflows)
├── .context/
│   ├── project/
│   │   ├── README.md                        ✅ Created
│   │   └── CODEX_HANDOVER.md                ✅ Created (MVP requirements)
│   ├── sprint/
│   │   └── README.md                        ✅ Created
│   ├── temp/                                (git-ignored)
│   ├── issues/                              (git-ignored)
│   └── reports/                             (git-ignored)
├── .gitignore                               ✅ Created (with Rule 11 ignores)
└── README.md                                ⏳ TO CREATE

```

---

## Verification Checklist

### Phase 1: Files Created ✅

- [x] `.github/copilot-instructions.md` - Project-specific with Equipment Manuals Chatbot details
- [x] `.github/CODEOWNERS` - @nsin08 as owner
- [x] `.gitignore` - Rule 11 ignores added
- [x] `.context/project/README.md` - Project context structure
- [x] `.context/project/CODEX_HANDOVER.md` - MVP requirements document
- [x] `.context/sprint/README.md` - Sprint workflow guide
- [x] Issue templates (7 total): Idea, Epic, Story, Task, DoR, DoD, Feature Request
- [x] PR template with evidence mapping
- [x] Workflow README with setup instructions

### Phase 2: Repository Setup 🔄

- [x] Repository created on GitHub: https://github.com/nsin08/ai_manuals
- [ ] Initial commit pushed to main
- [ ] Labels created (see `.github/SETUP_COMMANDS.md`)
- [ ] Branch protection configured (lightweight, non-strict)
- [ ] GitHub Actions enabled (if workflows are added)

### Phase 3: Verification 🔄

- [ ] Issue templates appear in "New Issue" menu
- [ ] PR template auto-fills when creating PR
- [ ] Labels visible in repository
- [ ] Branch protection shows in Settings > Branches
- [ ] Copilot recognizes instructions file

---

## Quick Start Commands

### 1. Initialize Git and Push

```bash
cd d:\wsl_shared\projects\ai_maunuals

# Initialize git (if not already)
git init
git branch -M main

# Add remote (already done via gh repo create)
git remote -v  # Should show origin -> nsin08/ai_manuals

# Stage all files
git add .

# Create initial commit
git commit -m "chore: adopt space_framework governance model

- Add copilot instructions with project-specific details
- Add CODEOWNERS file (@nsin08)
- Add .gitignore with Rule 11 context ignores
- Add 7 issue templates (Idea, Epic, Story, Task, DoR, DoD, Feature Request)
- Add PR template with evidence mapping
- Add .context structure (project + sprint)
- Add CODEX_HANDOVER with MVP requirements
- Add workflow setup instructions

Framework: space_framework v1.0.0
Ref: https://github.com/nsin08/space_framework"

# Push to GitHub
git push -u origin main
```

### 2. Create Labels

```bash
# Run all label creation commands from .github/SETUP_COMMANDS.md
# Copy and paste the entire "Create Repository Labels" section
```

### 3. Configure Branch Protection

```bash
# Option A: Use the gh CLI command from SETUP_COMMANDS.md
# Option B: Use GitHub web UI (step-by-step instructions in SETUP_COMMANDS.md)
```

### 4. Verify Setup

```bash
# Check labels
gh label list --limit 50

# Check branch protection
gh api /repos/nsin08/ai_manuals/branches/main/protection

# Check issue templates (via web)
# Go to: https://github.com/nsin08/ai_manuals/issues/new/choose
```

---

## Next Steps After Verification

1. **Create first Idea issue** using template
2. **Test workflow** (Idea → Epic → Story → PR)
3. **Copy enforcement workflows** from space_framework (see `.github/workflows/README.md`)
4. **Set up CI/CD** (basic Python test workflow)
5. **Start implementation** following space_framework governance

---

## Troubleshooting

### Issue templates not showing

- Wait 1-2 minutes (GitHub caches)
- Ensure files are in `.github/ISSUE_TEMPLATE/`
- Ensure pushed to default branch (`main`)

### Copilot not recognizing instructions

- File must be exactly `.github/copilot-instructions.md`
- Reload VS Code window
- Check file is committed and pushed

### Labels not created

- Ensure `gh` CLI is authenticated: `gh auth status`
- Check you have write access to repository
- Run commands one by one if batch fails

---

## Summary

### ✅ Completed

1. GitHub repository created: `nsin08/ai_manuals`
2. Full space_framework governance structure in place
3. Copilot instructions customized for Equipment Manuals Chatbot
4. All templates created (issue + PR)
5. Context directories initialized
6. CODEX handover document with MVP requirements
7. Setup commands documented

### 🔄 Pending (Human Action Required)

1. Push initial commit to GitHub
2. Create labels using commands in SETUP_COMMANDS.md
3. Configure branch protection (lightweight, non-strict)
4. Copy enforcement workflows from framework (optional)
5. Verify setup by creating first issue

### 📋 Reference Documents

- **Framework setup guide:** `.github/SETUP_COMMANDS.md`
- **Workflow setup:** `.github/workflows/README.md`
- **Project requirements:** `.context/project/CODEX_HANDOVER.md`
- **Copilot instructions:** `.github/copilot-instructions.md`

---

**Framework:** space_framework v1.0.0  
**Source:** https://github.com/nsin08/space_framework  
**Last Updated:** 2026-02-17
