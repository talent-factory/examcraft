# Grading Schemes

!!! note "Enterprise Feature"
    Creating custom grading schemes requires the `grading_schemes:manage` permission, which is assigned by default to Admin and Institution Owner roles in the Enterprise tier.

ExamCraft AI includes eight preset system schemes (read-only) and allows institutions to define their own schemes. Route: `/admin/grading-schemes`.

## System Schemes vs. Institution Schemes

| Type | Origin | Editable? |
|------|--------|-----------|
| System Scheme | ExamCraft AI (pre-installed) | No |
| Institution Scheme | Created by you | Yes — editable and deletable |

System schemes cover the most common national grading systems (Swiss, German, Austrian, French, Dutch, ECTS, Percentage, Pass/Fail). Custom schemes extend this list.

## Configuration Types

### `linear`

Linear conversion from percentage to grade between `min_score` and `max_score`.

```yaml
type: linear
min_score: 1.0
max_score: 6.0
passing_percentage: 60
```

### `linear_segments`

Two linear segments with a breakpoint at `passing_percentage`. Grades below the passing threshold have a shallower slope than those above.

```yaml
type: linear_segments
min_score: 1.0
max_score: 6.0
passing_percentage: 60
passing_score: 4.0
```

### `stepped`

Grades in fixed steps. Each step defines a percentage range and the corresponding grade.

```yaml
type: stepped
steps:
  - { min_percent: 0,  max_percent: 49,  grade: "F" }
  - { min_percent: 50, max_percent: 64,  grade: "D" }
  - { min_percent: 65, max_percent: 79,  grade: "C" }
  - { min_percent: 80, max_percent: 89,  grade: "B" }
  - { min_percent: 90, max_percent: 100, grade: "A" }
```

## Creating a Custom Scheme

1. Navigate to `/admin/grading-schemes`
2. Click on **New Scheme**
3. Select the configuration type
4. Fill in the parameters
5. The **Live Preview** immediately shows which grade is assigned at which percentage value
6. **Save** — the scheme becomes available to instructors during grade export

## Setting an Institution Default

Click the star icon next to a scheme to set it as the default for your institution. This value will be pre-selected during grade export. Instructors can override the selection per export.

## Next Steps

- [:octicons-arrow-right-24: Moodle Connection](moodle.md)
- [:octicons-arrow-right-24: Roles and Permissions](roles.md)
- [:octicons-arrow-right-24: Grade Export (User Guide)](../user-guide/notenexport.md)
