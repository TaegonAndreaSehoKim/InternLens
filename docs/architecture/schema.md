# Schema Design

## Jobs Table
| Column | Type | Description |
|---|---|---|
| job_id | string | Unique identifier for each job posting |
| company | string | Company name |
| title | string | Job title |
| location | string | Job location |
| description | text | Full job description |
| min_qualifications | text | Required qualifications |
| preferred_qualifications | text | Preferred qualifications |
| posting_date | date | Date the job was posted |
| sponsorship_info | string | Sponsorship or work authorization information |
| employment_type | string | Internship, full-time, etc. |
| source | string | Source of the posting |

## Candidate Profile
| Field | Type | Description |
|---|---|---|
| profile_id | string | Unique profile identifier |
| resume_text | text | Full resume text |
| degree_level | string | Bachelor's, Master's, etc. |
| grad_date | string | Expected graduation date |
| preferred_roles | list[string] | Preferred job roles |
| preferred_locations | list[string] | Preferred job locations |
| sponsorship_need | boolean | Whether the candidate needs sponsorship |
| extracted_skills | list[string] | Skills extracted from resume |