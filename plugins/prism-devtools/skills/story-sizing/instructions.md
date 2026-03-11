# Story Sizing — Full Instructions

Covers three modes: **Estimate**, **Calibrate**, and **Resize**.

---

## Mode 1: PROBE Estimation

Apply the PROBE (PROxy-Based Estimation) method to estimate story size and effort using historical data.

### When to Use

- Estimating effort for a new story
- During sprint planning for sizing stories
- Comparing story complexity to historical work
- Calibrating estimation accuracy over time

### 1. Gather Historical Data

Check for previous stories in `devStoryLocation` and extract:
- Story complexity ratings (VS, S, M, L, VL)
- Estimated hours from story files
- Actual completion time (from Status timestamps)

If no historical data exists, use these initial proxy values:
```yaml
initial_proxies:
  very_small: 2 hours
  small: 4 hours
  medium: 8 hours
  large: 16 hours
  very_large: 32 hours
```

### 2. Map Story Points to Size Category

```yaml
story_point_mapping:
  1: very_small
  2: small
  3: medium
  5: large
  8: very_large

size_categories:
  very_small:
    story_points: 1
    description: "Simple config change or single-file update"
    typical_tasks: 1-2
    complexity: "Trivial logic, no dependencies"

  small:
    story_points: 2
    description: "Single feature or bug fix"
    typical_tasks: 3-5
    complexity: "Simple logic, minimal dependencies"

  medium:
    story_points: 3
    description: "Multi-component feature"
    typical_tasks: 6-10
    complexity: "Moderate logic, some integration"

  large:
    story_points: 5
    description: "Cross-system feature"
    typical_tasks: 11-20
    complexity: "Complex logic, significant integration"

  very_large:
    story_points: 8
    description: "Architectural change or major feature"
    typical_tasks: 20+
    complexity: "Very complex, multiple systems"
```

### 3. Find Similar Stories (Proxy Selection)

Search historical stories for similar characteristics:
- Similar technical components (frontend/backend/database)
- Similar task count and acceptance criteria count
- Similar risk profile

### 4. Calculate Estimate

```yaml
probe_calculation:
  with_history:
    estimate: beta0 + (beta1 * proxy_size)
    range:
      optimistic: estimate * 0.7
      likely: estimate
      pessimistic: estimate * 1.5

  without_history:
    estimate: selected_proxy_value
    range:
      optimistic: estimate * 0.5
      likely: estimate
      pessimistic: estimate * 2.0
```

### 5. Add Estimation Data to Story

Append to story file in Dev Notes section:

```yaml
psp_estimation:
  method: "PROBE"
  story_points: {1|2|3|5|8}
  size_category: "{very_small|small|medium|large|very_large}"
  proxy_stories:
    - "{epic.story} - {actual_hours}h"
  estimated_hours:
    optimistic: X
    likely: Y
    pessimistic: Z
  confidence: "{high|medium|low}"
  estimation_date: "YYYY-MM-DD"
  start_date: null
  end_date: null
  actual_hours: null
```

### 6. Track Actuals

When story completes, update:
- Set `end_date`, calculate `actual_hours`
- Record `estimation_accuracy` (estimated vs actual variance)

### 7. Continuous Improvement

After every 5 completed stories:
- Calculate estimation accuracy metrics
- Adjust proxy values based on actuals
- Note patterns in estimation errors

Store in `../data/estimation-history.yaml`:

```yaml
estimation_metrics:
  total_stories: N
  average_accuracy: X%
  size_distribution:
    very_small: { count: N, avg_hours: H, std_dev: S }
    small: { count: N, avg_hours: H, std_dev: S }
    medium: { count: N, avg_hours: H, std_dev: S }
    large: { count: N, avg_hours: H, std_dev: S }
    very_large: { count: N, avg_hours: H, std_dev: S }
  improvement_trend: "improving|stable|degrading"
```

### Estimate Output Format

```markdown
### PSP Estimation (PROBE Method)

- **Size Category**: Medium
- **Similar Stories Used**:
  - 1.2 User Auth (12h actual)
  - 1.5 API Integration (14h actual)
- **Estimate**: 8-13-20 hours (optimistic-likely-pessimistic)
- **Confidence**: Medium
- **Estimated**: YYYY-MM-DD
```

### Estimate Success Criteria

- [ ] Story has size category assigned
- [ ] Estimation includes range (O/L/P)
- [ ] Historical data referenced if available
- [ ] Tracking fields ready for actuals

---

## Mode 2: Calibrate Sizing

Improve story sizing accuracy by analyzing historical estimation data.

### When to Use

- After completing 10+ stories
- When estimation variance is consistently high (>30%)
- Before starting a new project phase or quarter
- When team composition or technology stack changes

### Reference

For detailed YAML examples of all structures, see [./reference/probe-methodology.md](./reference/probe-methodology.md).

### 1. Gather Historical Data

Load completed stories from last 10-20 completions. Collect size distribution data including count, estimated average, actual average, and variance for each size category (VS, S, M, L, VL). Flag Very Large stories for potential breakdown.

### 2. Identify Patterns

Analyze systematic biases:
- Overestimation patterns (e.g., Backend CRUD)
- Underestimation patterns (e.g., third-party integrations)
- Technology factors (new vs familiar tech multipliers)
- Complexity factors (high integration vs standalone)

### 3. Update Size Definitions

Based on actual data, compare old ranges to actual averages and propose new ranges. Update story point mapping (1, 2, 3, 5, 8 points). Flag 8-point stories as requiring split.

### 4. Refine PROBE Proxies

- Retire outdated proxies that no longer represent current patterns
- Add new proxies from recent well-estimated stories
- Organize proxies into categories: ui_simple, ui_with_api, backend_crud, integration

### 5. Create Regression Model (30+ stories)

If sufficient data:
- Base overhead (intercept)
- Factors per: acceptance criteria, API endpoints, UI components, database tables, integration points

### 6. Generate Recommendations

Three categories:
- **Immediate actions**: Size definition updates, buffer adjustments
- **Process improvements**: Flags for large stories, checklists for integrations
- **Training needs**: Team-specific guidance based on identified patterns

### 7. Update Estimation History

Record calibration details: date, stories analyzed, adjustments made, accuracy improvement metrics, next trigger.

### 8. Generate Calibration Report

Markdown report including:
- Executive Summary
- Size Category Performance table
- Pattern Analysis (over/under with actions)
- Updated Sizing Guide
- Recommendations and Next Steps

See [./reference/probe-methodology.md](./reference/probe-methodology.md) for the full report template.

### Calibrate Success Criteria

- [ ] Minimum 10 stories analyzed
- [ ] Patterns identified and documented
- [ ] Size definitions updated if needed
- [ ] Proxy library refreshed
- [ ] Recommendations actionable
- [ ] History file updated

---

## Mode 3: Resize Story

Adjust estimates and split/combine stories that are too large or too small.

### When to Use

- Story estimation exceeds 3 days (split needed)
- Story estimation is under 0.5 days (combine candidate)
- New information changes story complexity
- During sprint planning when stories need right-sizing

### 1. Analyze Current Story

```yaml
story_analysis:
  size_assessment:
    too_large: hours > 24 (3 days)
    too_small: hours < 4 (0.5 days)
    just_right: 4 <= hours <= 24

  complexity_factors:
    technical_components: N
    integration_points: M
    acceptance_criteria: P
    risk_factors: ["list"]
```

### 2. Identify Split Points (If Too Large)

Natural boundaries to split on:
- **Functional**: Create/Read/Update/Delete; happy path vs error handling
- **Technical**: Frontend vs Backend vs Database; API vs UI vs Business Logic
- **Temporal**: Now vs Later; MVP vs Nice-to-have
- **Risk-based**: Known vs Unknown; Simple vs Complex

### 3. Create Split Stories

For each split, define: id, title, scope (includes/excludes), acceptance criteria, estimation (points, category, hours), dependencies.

### 4. Validate Splits

```yaml
split_validation:
  independence:
    can_be_developed_alone: true/false
    can_be_tested_alone: true/false
    delivers_value: true/false

  size_check:
    within_target_range: true/false  # 4-24 hours
    needs_further_split: true/false

  completeness:
    all_acs_covered: true/false
    no_scope_gaps: true/false
```

### 5. Combine Small Stories (If Needed)

Combination rules:
- Must be related functionality
- Should touch same components
- Combined size still in target range (4-24h)
- Maintains single responsibility

### 6. Update PROBE Estimations

Re-estimate each resized story using PROBE (Mode 1), referencing similar proxy stories and size factors.

### 7. Update Dependencies

Resequence dependent stories after splits. Document new dependency chain and impact analysis.

### 8. Generate Resize Report

```markdown
# Story Resize Report

## Original Story
- ID, Size, Issue

## Resize Action
- Action taken (split/combine), new total hours

## New Stories
List each new story with size, confidence, and readiness

## Benefits
- Faster feedback cycles
- Reduced risk per story
- Parallel development opportunities

## Recommendations
- Execution order
- Parallel work opportunities
- Deferral candidates
```

### Resize Success Criteria

- [ ] No stories larger than 24 hours
- [ ] Minimal stories smaller than 4 hours
- [ ] Each story independently valuable
- [ ] Dependencies properly mapped
- [ ] PROBE estimates updated
- [ ] Original scope fully covered
