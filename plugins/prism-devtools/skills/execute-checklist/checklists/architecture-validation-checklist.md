<!-- Powered by PRISM™ System -->

# Architecture Documentation Validation Checklist

## Purpose

Validate that all required architecture documentation exists, is complete, and meets PRISM quality standards.

## When to Use

- After running `*initialize-architecture` task
- Before finalizing architecture for a new project
- During quarterly architecture review
- Before major releases or architectural changes

## Checklist

### 1. Required Documents Exist

Check that all required architecture documents are present:

- [ ] `docs/architecture/README.md` - Master index exists
- [ ] `docs/architecture/coding-standards.md` - Coding standards document exists
- [ ] `docs/architecture/tech-stack.md` - Tech stack document exists
- [ ] `docs/architecture/source-tree.md` - Source tree document exists
- [ ] `docs/architecture/deployment.md` - Deployment document exists
- [ ] `docs/architecture/data-model.md` - Data model document exists
- [ ] `docs/architecture/api-contracts.md` - API contracts document exists

**Result:** ___/7 documents found

### 2. Coding Standards (`coding-standards.md`)

- [ ] **Code Style Guidelines** section is filled out
  - [ ] General principles defined
  - [ ] Language-specific standards documented
- [ ] **Naming Conventions** section is complete
  - [ ] Files and directories conventions specified
  - [ ] Variables and functions conventions specified
- [ ] **Code Organization** section is complete
  - [ ] File structure guidelines defined
  - [ ] Import order specified
- [ ] **Error Handling** patterns documented
- [ ] **Testing Standards** section is complete
  - [ ] Test coverage requirements specified
  - [ ] Test organization guidelines defined
- [ ] **Code Review Guidelines** checklist provided
- [ ] Status indicator updated (🔴 → 🟡 → 🟢)
- [ ] Last Updated date is current
- [ ] Document owner assigned

**Result:** ___/9 items complete

### 3. Tech Stack (`tech-stack.md`)

- [ ] **Technology Stack Overview** section is filled out
  - [ ] Frontend technologies specified
  - [ ] Backend technologies specified
  - [ ] Database technologies specified
  - [ ] Infrastructure technologies specified
  - [ ] Development tools listed
- [ ] **Dependencies** section is complete
  - [ ] Critical dependencies table filled out
  - [ ] Dependency management process documented
- [ ] **Technology Decisions** section documents reasoning
  - [ ] Stack rationale explained
  - [ ] Migration path documented
- [ ] All version numbers specified
- [ ] Alternatives considered documented
- [ ] Status indicator updated (🔴 → 🟡 → 🟢)
- [ ] Last Updated date is current
- [ ] Document owner assigned

**Result:** ___/12 items complete

### 4. Source Tree (`source-tree.md`)

- [ ] **Directory Structure** diagram is complete and accurate
- [ ] **Directory Descriptions** section filled out
  - [ ] /src directory documented
  - [ ] /docs directory documented
  - [ ] /tests directory documented
  - [ ] All major directories described
- [ ] **File Naming Conventions** documented
  - [ ] Components naming specified
  - [ ] Services naming specified
  - [ ] Utilities naming specified
- [ ] **Module Boundaries** section complete
  - [ ] Import rules defined
  - [ ] Dependency rules specified
- [ ] **Code Location Guidelines** provided
  - [ ] When to create new files
  - [ ] When to create new directories
- [ ] Status indicator updated (🔴 → 🟡 → 🟢)
- [ ] Last Updated date is current
- [ ] Document owner assigned

**Result:** ___/13 items complete

### 5. Deployment (`deployment.md`)

- [ ] **Environments** section complete
  - [ ] Development environment documented
  - [ ] Staging environment documented
  - [ ] Production environment documented
  - [ ] URLs for all environments specified
- [ ] **Infrastructure Components** documented
  - [ ] Application servers specified
  - [ ] Database configuration documented
  - [ ] Cache layer documented
- [ ] **Deployment Process** section complete
  - [ ] CI/CD pipeline documented
  - [ ] Rollback strategy defined
- [ ] **Monitoring and Alerts** section complete
  - [ ] Key metrics defined
  - [ ] Alerting configured
- [ ] **Security** section complete
  - [ ] Access control documented
  - [ ] Secrets management documented
- [ ] Status indicator updated (🔴 → 🟡 → 🟢)
- [ ] Last Updated date is current
- [ ] Document owner assigned

**Result:** ___/14 items complete

### 6. Data Model (`data-model.md`)

- [ ] **Data Model Overview** section complete
  - [ ] ERD diagram provided or described
- [ ] **Core Entities** documented
  - [ ] At least 3 entities documented
  - [ ] Fields table complete for each entity
  - [ ] Relationships documented
- [ ] **Database Schema** section complete
  - [ ] SQL CREATE statements provided
  - [ ] All tables documented
- [ ] **Indexes** documented
  - [ ] Performance indexes listed
- [ ] **Data Relationships** section complete
  - [ ] Referential integrity documented
- [ ] **Migration Strategy** documented
- [ ] **Data Retention** policies documented
- [ ] Status indicator updated (🔴 → 🟡 → 🟢)
- [ ] Last Updated date is current
- [ ] Document owner assigned

**Result:** ___/11 items complete

### 7. API Contracts (`api-contracts.md`)

- [ ] **API Overview** section complete
  - [ ] Base URLs for all environments specified
  - [ ] Authentication method documented
- [ ] **API Endpoints** section complete
  - [ ] At least 5 endpoints documented
  - [ ] Request format for each endpoint
  - [ ] Response format for each endpoint
  - [ ] Error responses documented
- [ ] **Error Responses** standard format defined
- [ ] **Rate Limiting** documented
  - [ ] Limits specified
  - [ ] Headers documented
- [ ] **Versioning** strategy documented
- [ ] **Integration Points** section complete
  - [ ] External APIs documented
  - [ ] Webhooks documented
- [ ] Status indicator updated (🔴 → 🟡 → 🟢)
- [ ] Last Updated date is current
- [ ] Document owner assigned

**Result:** ___/12 items complete

### 8. Master Index (`README.md`)

- [ ] **Quick Navigation** section has links to all documents
- [ ] **Document Status** table is complete
  - [ ] Status indicators accurate (🔴/🟡/🟢)
  - [ ] Last Updated dates current
- [ ] **How to Use This Documentation** section filled out
  - [ ] Guidance for developers
  - [ ] Guidance for architects
  - [ ] Guidance for new team members
- [ ] **Maintenance** section complete
  - [ ] Update frequency specified
  - [ ] Document owners assigned
- [ ] **Contributing** process documented
- [ ] All links work (no broken links)
- [ ] Last Updated date is current

**Result:** ___/7 items complete

### 9. Quality Standards

- [ ] All documents use consistent markdown formatting
- [ ] All documents have proper headers and sections
- [ ] All code blocks have language specifiers
- [ ] All tables are properly formatted
- [ ] No placeholder text remains (e.g., "[TODO]", "[Fill in]")
- [ ] All documents use consistent terminology
- [ ] Grammar and spelling are correct
- [ ] All cross-references between documents are accurate

**Result:** ___/8 items complete

### 10. Configuration Alignment

- [ ] `core-config.yaml` `architecture.architectureShardedLocation` matches actual location
- [ ] All files in `devLoadAlwaysFiles` exist
  - [ ] `docs/architecture/coding-standards.md` exists
  - [ ] `docs/architecture/tech-stack.md` exists
  - [ ] `docs/architecture/source-tree.md` exists
- [ ] All documents from `architecture.requiredDocs` exist
- [ ] No extra untracked files in architecture folder

**Result:** ___/5 items complete

## Overall Scoring

**Total Possible:** 98 items
**Total Complete:** ___/98 items

**Status:**
- 🟢 **Complete** (90-100%): Architecture documentation is production-ready
- 🟡 **In Progress** (70-89%): Architecture documentation needs refinement
- 🔴 **Draft** (< 70%): Architecture documentation needs significant work

## Remediation Actions

If checklist score is below 90%:

1. **Identify Missing Items:**
   - List all unchecked items
   - Prioritize by importance (critical → nice-to-have)

2. **Create Action Plan:**
   - Assign owners for each missing item
   - Set deadlines for completion
   - Schedule follow-up review

3. **Update Documents:**
   - Fill in missing sections
   - Update status indicators
   - Update last modified dates

4. **Re-run Checklist:**
   - Verify all items complete
   - Update status to 🟢

## Next Steps After Validation

Once all items are checked:

1. **Announce Completion:**
   - Notify team of completed architecture documentation
   - Share links to architecture folder

2. **Schedule Reviews:**
   - Set quarterly review dates
   - Add to team calendar

3. **Integrate into Workflow:**
   - Reference in onboarding docs
   - Link from project README
   - Use during code reviews

4. **Maintain Currency:**
   - Update documents as architecture evolves
   - Keep status indicators accurate
   - Review before major releases

---

_Architecture validation checklist powered by PRISM™ System_
