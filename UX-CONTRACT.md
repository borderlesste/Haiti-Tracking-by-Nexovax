# Shared behavior contract

## Canonical UI Map
| Capability | Canonical owner | Source of truth | Allowed variants | Verification |
|---|---|---|---|---|
| Select/Listbox | Field/native select in ui.jsx | Browser semantics, localized options | native | browser keyboard and popup |
| Form | Form and Field in ui.jsx | server schemas + native constraint API | create/edit/auth | validation, error preservation |
| Scrollbar | styles.css global baseline | DESIGN.md | geometry only | responsive browser |
| Toast | App notice live region | App context | success/error/info | aria status |
| CRUD | api.js and route pages | API state machine | list/create/detail | integration tests |

Links navigate; buttons mutate. Forms use noValidate with explicit validity handling and first-invalid focus. Shared Field associates label, input, inline error and help. Every request has pending/error/empty recovery; search cancels stale results. Failed saves preserve input. No secrets, GPS, sessions or credentials in localStorage. Drafts are authenticated server records. Successful create goes to owning contribution list; successful register requests email verification. Moderation decisions require reasons; self-approval and role permissions are server responsibilities. API key secrets appear once in memory, revocation requires app-owned confirmation.

Private screens present sign-in and retain a safe local next path. Admin controls never grant server authority. GPS is requested only after explicit activation; denial allows a draft or unverified suggestion. Precision is stated honestly. Rewards are disabled. Public map never requests GPS on load and only displays API-authorized locations.

Modal owner: native HTML dialog with showModal, autofocus and close restoration. Form failures are persistent inline alerts. List pages use bounded API pagination and load more. Search/filter state is stored in URL. Locale persists as a non-sensitive browser preference. Authentication cookies and CSRF remain server-managed.
