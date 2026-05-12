import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { AuthProvider, useAuth } from "react-oidc-context";
import "./styles.css";
import {
  ACTION_FILTERS,
  actionClass,
  actionLabel,
  actionValue,
  displayScore,
  recommendationCounts,
  visibleRecommendations
} from "./recommendationHelpers";
import { activityBadgeLabel, activityTitle, compactTimestamp } from "./dashboardHelpers";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const STORAGE_KEY = "internlens.ui.state";
const AUTH_MODE = import.meta.env.VITE_AUTH_MODE ?? "dev";
const COGNITO_REGION = import.meta.env.VITE_COGNITO_REGION ?? "";
const COGNITO_USER_POOL_ID = import.meta.env.VITE_COGNITO_USER_POOL_ID ?? "";
const COGNITO_APP_CLIENT_ID = import.meta.env.VITE_COGNITO_APP_CLIENT_ID ?? "";
const RECOMMENDATION_FETCH_LIMIT = 1000;
const RECOMMENDATION_PAGE_SIZE = 20;

const JOB_STATE_LABELS = {
  saved: "Saved",
  applied: "Applied",
  dismissed: "Hidden"
};

const DASHBOARD_JOB_VIEWS = {
  recommendations: {
    label: "Shortlists",
    heading: "Current shortlist",
    empty: "Find matches or open a previous shortlist to review ranked internship leads."
  },
  saved: {
    label: "Saved",
    heading: "Saved jobs",
    endpoint: "saved-jobs",
    empty: "No saved jobs yet."
  },
  applied: {
    label: "Applied",
    heading: "Applied jobs",
    endpoint: "applied-jobs",
    empty: "No applied jobs yet."
  },
  dismissed: {
    label: "Hidden",
    heading: "Hidden jobs",
    endpoint: "dismissed-jobs",
    empty: "No hidden jobs yet."
  }
};

const SERVER_STATUS_LABELS = {
  checking: "Checking",
  online: "Online",
  offline: "Offline"
};

const DEGREE_OPTIONS = [
  "Associate",
  "Bachelor's",
  "Master's",
  "PhD",
  "Bootcamp / Certificate",
  "Other"
];

const ROLE_OPTIONS = [
  "Software Engineering Intern",
  "Frontend Engineering Intern",
  "Backend Engineering Intern",
  "Full Stack Engineering Intern",
  "Mobile Engineering Intern",
  "DevOps Intern",
  "Cloud Engineering Intern",
  "Cybersecurity Intern",
  "QA Engineering Intern",
  "Hardware Engineering Intern",
  "Mechanical Engineering Intern",
  "Electrical Engineering Intern",
  "Civil Engineering Intern",
  "Industrial Engineering Intern",
  "Machine Learning Engineer Intern",
  "AI Research Intern",
  "Data Science Intern",
  "Data Analyst Intern",
  "Business Intelligence Intern",
  "Product Manager Intern",
  "Business Analyst Intern",
  "UX Research Intern",
  "Product Design Intern",
  "Graphic Design Intern",
  "Content Design Intern",
  "Marketing Intern",
  "Growth Marketing Intern",
  "Digital Marketing Intern",
  "Content Marketing Intern",
  "Social Media Intern",
  "Sales Intern",
  "Customer Success Intern",
  "Finance Intern",
  "Accounting Intern",
  "Investment Analyst Intern",
  "Operations Intern",
  "Supply Chain Intern",
  "Human Resources Intern",
  "Talent Acquisition Intern",
  "Legal Intern",
  "Clinical Research Intern",
  "Biotech Research Intern",
  "Lab Research Intern",
  "Public Health Intern",
  "Policy Intern",
  "Government Affairs Intern",
  "Education Program Intern",
  "Nonprofit Program Intern",
  "Communications Intern",
  "Journalism Intern",
  "Sustainability Intern",
  "Environmental Research Intern"
];

const SKILL_GROUPS = [
  {
    label: "Programming",
    options: ["Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust", "R", "SQL"]
  },
  {
    label: "ML / Data",
    options: ["Machine Learning", "Deep Learning", "PyTorch", "TensorFlow", "Pandas", "NumPy", "Statistics", "A/B Testing", "Data Visualization"]
  },
  {
    label: "Web",
    options: ["React", "Vue", "Angular", "Node.js", "FastAPI", "Django", "Flask", "REST APIs", "GraphQL"]
  },
  {
    label: "Cloud / Tools",
    options: ["AWS", "Azure", "Google Cloud", "Docker", "Kubernetes", "Linux", "Git", "CI/CD", "Terraform"]
  },
  {
    label: "Analytics",
    options: ["Excel", "Tableau", "Power BI", "Looker", "Google Analytics", "Salesforce Analytics"]
  },
  {
    label: "Business",
    options: ["Market Research", "Financial Modeling", "Operations", "Project Management", "CRM", "Salesforce", "Business Strategy", "Competitive Analysis"]
  },
  {
    label: "Design / Research",
    options: ["User Research", "Figma", "Wireframing", "Prototyping", "Survey Design", "Accessibility", "Design Systems", "Usability Testing"]
  },
  {
    label: "Healthcare / Science",
    options: ["Clinical Research", "Biology", "Chemistry", "Lab Techniques", "Scientific Writing", "Data Collection", "Literature Review", "Regulatory Affairs"]
  },
  {
    label: "Policy / Communications",
    options: ["Policy Analysis", "Writing", "Editing", "Public Speaking", "Community Outreach", "Grant Writing", "Media Relations", "Social Media"]
  }
];

const SKILL_OPTIONS = SKILL_GROUPS.flatMap((group) => group.options);

const LOCATION_OPTIONS = [
  "Remote",
  "Hybrid",
  "United States",
  "California",
  "New York",
  "Seattle",
  "San Francisco",
  "San Jose",
  "Los Angeles",
  "San Diego",
  "Austin",
  "Dallas",
  "Houston",
  "Boston",
  "Chicago",
  "Atlanta",
  "Washington DC",
  "Denver",
  "Portland",
  "Raleigh",
  "Pittsburgh",
  "Toronto",
  "Vancouver",
  "London",
  "Berlin",
  "Singapore",
  "Seoul",
  "Tokyo"
];

const INDUSTRY_OPTIONS = [
  "AI",
  "Enterprise Software",
  "SaaS",
  "Fintech",
  "Health Tech",
  "Robotics",
  "Consumer Tech",
  "Cloud Infrastructure",
  "Cybersecurity",
  "Education",
  "Climate Tech",
  "Biotech",
  "Healthcare",
  "Finance",
  "Retail",
  "Media",
  "Government",
  "Nonprofit",
  "Manufacturing",
  "Automotive",
  "Aerospace",
  "Energy",
  "Real Estate",
  "Logistics",
  "Hospitality",
  "Sports",
  "Entertainment",
  "Telecommunications",
  "Semiconductors",
  "Pharmaceuticals",
  "Consumer Goods"
];

const PUBLIC_FEATURES = [
  {
    title: "Structured profile setup",
    body: "Start from guided role, skill, location, and industry choices instead of relying on a long free-text prompt.",
  },
  {
    title: "Explainable recommendations",
    body: "Review ranked internship leads with readable match reasons, blockers, and fit signals before taking action.",
  },
  {
    title: "Shortlist workflow",
    body: "Keep saved, applied, and hidden roles organized so each search pass gets easier to review.",
  },
];

const PUBLIC_STEPS = [
  "Create an account",
  "Build a profile",
  "Find matches",
  "Track decisions",
];

const PUBLIC_SAMPLE_JOBS = [
  {
    title: "Software Engineering Intern",
    company: "Example Robotics",
    meta: "Atlanta, GA | Summer 2026",
    reason: "Strong match for backend systems, Python, and product engineering interests.",
  },
  {
    title: "Data Analyst Intern",
    company: "Sample Health",
    meta: "Remote | Summer 2026",
    reason: "Matches analytics, SQL, dashboarding, and healthcare domain preferences.",
  },
  {
    title: "Product Operations Intern",
    company: "Demo Cloud",
    meta: "New York, NY | Fall 2026",
    reason: "Relevant to operations, customer workflows, and cross-functional product work.",
  },
];

const defaultProfile = {
  resume_text: "",
  degree_level: "",
  grad_date: "",
  preferred_roles: "",
  preferred_locations: "",
  target_industries: "",
  sponsorship_need: false,
  extracted_skills: "",
  years_of_experience: 0,
  notes: ""
};

function cognitoAuthority() {
  return `https://cognito-idp.${COGNITO_REGION}.amazonaws.com/${COGNITO_USER_POOL_ID}`;
}

function csvToList(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function addCsvItems(value, items) {
  const existing = csvToList(value);
  const normalized = new Set(existing.map((item) => item.toLowerCase()));
  const additions = items
    .map((item) => item.trim())
    .filter((item) => item && !normalized.has(item.toLowerCase()));
  return [...existing, ...additions].join(", ");
}

function removeCsvItem(value, item) {
  const normalizedItem = item.trim().toLowerCase();
  return csvToList(value).filter((entry) => entry.toLowerCase() !== normalizedItem).join(", ");
}

function listToCsv(value) {
  return Array.isArray(value) ? value.join(", ") : value ?? "";
}

function degreeOption(value) {
  const normalized = String(value ?? "").trim().toLowerCase();
  return DEGREE_OPTIONS.find((option) => option.toLowerCase() === normalized) ?? value ?? defaultProfile.degree_level;
}

function profileToForm(profile) {
  return {
    resume_text: profile.resume_text ?? defaultProfile.resume_text,
    degree_level: degreeOption(profile.degree_level),
    grad_date: profile.grad_date ?? defaultProfile.grad_date,
    preferred_roles: listToCsv(profile.preferred_roles),
    preferred_locations: listToCsv(profile.preferred_locations),
    target_industries: listToCsv(profile.target_industries),
    sponsorship_need: Boolean(profile.sponsorship_need),
    extracted_skills: listToCsv(profile.extracted_skills),
    years_of_experience: profile.years_of_experience ?? 0,
    notes: profile.notes ?? ""
  };
}

function profilePayload(form) {
  return {
    ...form,
    preferred_roles: csvToList(form.preferred_roles),
    preferred_locations: csvToList(form.preferred_locations),
    target_industries: csvToList(form.target_industries),
    extracted_skills: csvToList(form.extracted_skills),
    years_of_experience: Number(form.years_of_experience || 0)
  };
}

function profileQuality(form) {
  const roleCount = csvToList(form.preferred_roles).length;
  const skillCount = csvToList(form.extracted_skills).length;
  const locationCount = csvToList(form.preferred_locations).length;
  const backgroundLength = String(form.resume_text ?? "").trim().length;
  const items = [
    {
      label: "Target role selected",
      detail: "Choose at least one internship role.",
      complete: roleCount >= 1,
      required: true
    },
    {
      label: "Core skills selected",
      detail: "Choose at least three skills.",
      complete: skillCount >= 3,
      required: true
    },
    {
      label: "Location preference selected",
      detail: "Choose at least one location or work mode.",
      complete: locationCount >= 1,
      required: true
    },
    {
      label: "Education timeline set",
      detail: "Set degree and graduation month.",
      complete: Boolean(form.degree_level && form.grad_date),
      required: true
    },
    {
      label: "Background context added",
      detail: "Optional, but useful for projects and coursework.",
      complete: backgroundLength >= 30,
      required: false
    },
    {
      label: "Industry preference added",
      detail: "Optional, but helps break ties between similar roles.",
      complete: csvToList(form.target_industries).length >= 1,
      required: false
    }
  ];
  const requiredItems = items.filter((item) => item.required);
  const requiredComplete = requiredItems.filter((item) => item.complete).length;
  const completeCount = items.filter((item) => item.complete).length;
  return {
    items,
    completeCount,
    totalCount: items.length,
    requiredComplete,
    requiredTotal: requiredItems.length,
    isReady: requiredComplete === requiredItems.length
  };
}

function titleCase(value = "") {
  return String(value)
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function eligibilityLabel(value) {
  if (!value) {
    return null;
  }
  return titleCase(value);
}

function sentenceCase(value = "") {
  const text = String(value).trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : "";
}

function cleanSignal(value = "") {
  return sentenceCase(String(value).replace(/[_-]/g, " ").replace(/\s+/g, " "));
}

function uniqueItems(items = []) {
  return [...new Set(items.map((item) => String(item).trim()).filter(Boolean))];
}

function fitSummary(job) {
  const company = job.company ?? "This company";
  const role = job.title ?? "this role";
  const score = displayScore(job);
  const fit = titleCase(job.fit_level ?? "match");
  if (score === null) {
    return `${company} ${role} is a ${fit.toLowerCase()} based on the visible posting text.`;
  }
  return `${company} ${role} is a ${fit.toLowerCase()} match with a ${score}/100 fit score.`;
}

function positiveEvidence(job) {
  return uniqueItems([
    ...(job.why_apply ?? []),
    ...(job.reasons ?? [])
  ]).map(cleanSignal);
}

function watchoutEvidence(job) {
  return uniqueItems([
    ...(job.watchouts ?? []),
    ...(job.blocking_issues ?? []),
    ...(job.skill_gaps ?? []).map((skill) => `Missing or unclear signal: ${skill}`)
  ]).map(cleanSignal);
}

function skillSignals(job) {
  return uniqueItems(job.matched_skills ?? []).slice(0, 6).map(cleanSignal);
}

function clearActionLabel(state) {
  const labels = {
    applied: "Undo applied",
    dismissed: "Show again",
    saved: "Unsave"
  };
  return labels[state] ?? "Undo";
}

function jobStateLookup(dashboard) {
  const entries = [
    ...(dashboard?.saved_jobs ?? []),
    ...(dashboard?.dismissed_jobs ?? []),
    ...(dashboard?.applied_jobs ?? [])
  ];
  return Object.fromEntries(entries.map((item) => [item.job_id, item]));
}

function storedJobStateToRecommendation(item) {
  const snapshot = item.job_snapshot ?? {};
  return {
    job_id: item.job_id,
    company: snapshot.company ?? "Unknown company",
    title: snapshot.title ?? "Tracked role",
    location: snapshot.location ?? "Location not listed",
    recommendation: snapshot.recommendation ?? "apply_later",
    fit_level: snapshot.fit_level ?? "tracked",
    eligibility_status: snapshot.eligibility_status ?? "",
    summary: snapshot.summary ?? `${JOB_STATE_LABELS[item.state] ?? titleCase(item.state)} role from your dashboard.`,
    why_apply: snapshot.why_apply ?? [],
    watchouts: snapshot.watchouts ?? [],
    application_link: snapshot.application_link ?? null,
    user_job_state: item.state,
    user_job_state_source_run_id: item.source_run_id
  };
}

function updateRecommendationJobState(recommendations, jobId, state, sourceRunId) {
  if (!recommendations) {
    return recommendations;
  }

  return {
    ...recommendations,
    results: (recommendations.results ?? []).map((job) => {
      if (job.job_id !== jobId) {
        return job;
      }
      const updatedJob = { ...job };
      if (state) {
        updatedJob.user_job_state = state;
        updatedJob.user_job_state_source_run_id = sourceRunId ?? null;
      } else {
        delete updatedJob.user_job_state;
        delete updatedJob.user_job_state_source_run_id;
      }
      return updatedJob;
    })
  };
}

function readStoredState() {
  try {
    return JSON.parse(window.localStorage.getItem(STORAGE_KEY)) ?? {};
  } catch {
    return {};
  }
}

function writeStoredState(state) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // Storage can be unavailable in private browsing or locked-down environments.
  }
}

function oidcConfig() {
  if (AUTH_MODE !== "cognito") {
    return null;
  }
  if (!COGNITO_REGION || !COGNITO_USER_POOL_ID || !COGNITO_APP_CLIENT_ID) {
    return null;
  }

  return {
    authority: cognitoAuthority(),
    client_id: COGNITO_APP_CLIENT_ID,
    redirect_uri: window.location.origin,
    post_logout_redirect_uri: window.location.origin,
    response_type: "code",
    scope: "openid email"
  };
}

async function api(path, options = {}, authToken = null) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...(options.headers ?? {})
    },
    ...options
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(body.detail ?? `Request failed: ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return body;
}

function friendlyErrorMessage(error) {
  if (String(error.message).includes("fetch")) {
    return "Server is offline. Check that the local API is running.";
  }
  if (error.status === 401) {
    return "Sign in again, then save the profile.";
  }
  if (error.status === 403) {
    return "This account cannot access that saved profile. Save a new profile for the current account.";
  }
  return error.message || "Something went wrong. Try again.";
}

function App({ authToken = null, accountEmail = "Local demo user", onSignOut = null }) {
  const [storedState] = useState(() => readStoredState());
  const [form, setForm] = useState(() => ({ ...defaultProfile, ...(storedState.form ?? {}) }));
  const [savedProfileForm, setSavedProfileForm] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [recommendations, setRecommendations] = useState(null);
  const [selectedRun, setSelectedRun] = useState(() => storedState.selectedRun ?? null);
  const [recommendationFilter, setRecommendationFilter] = useState(() => storedState.recommendationFilter ?? "all");
  const [dashboardJobView, setDashboardJobView] = useState("recommendations");
  const [dashboardJobLists, setDashboardJobLists] = useState({});
  const [apiHealth, setApiHealth] = useState("checking");
  const [busy, setBusy] = useState(false);
  const [profileStatus, setProfileStatus] = useState(null);
  const quality = profileQuality(form);
  const profileState = savedProfileForm
    ? JSON.stringify(form) === JSON.stringify(savedProfileForm) ? "saved" : "changed"
    : "draft";

  async function runTask(task, options = {}) {
    setBusy(true);
    setProfileStatus(null);
    try {
      await task();
      setApiHealth("online");
      if (options.successMessage) {
        setProfileStatus({ type: "success", message: options.successMessage });
      }
    } catch (error) {
      if (String(error.message).includes("fetch")) {
        setApiHealth("offline");
      }
      setProfileStatus({ type: "error", message: friendlyErrorMessage(error) });
    } finally {
      setBusy(false);
    }
  }

  async function loadDashboard() {
    const data = await api("/me/dashboard", {}, authToken);
    setDashboard(data);
    return data;
  }

  async function loadDashboardJobView(view) {
    const endpoint = DASHBOARD_JOB_VIEWS[view]?.endpoint;
    if (!endpoint) {
      return [];
    }

    const data = await api(`/me/${endpoint}`, {}, authToken);
    setDashboardJobLists((current) => ({ ...current, [view]: data.jobs }));
    return data.jobs;
  }

  async function showDashboardJobView(view) {
    setDashboardJobView(view);
    if (view !== "recommendations") {
      await loadDashboardJobView(view);
    }
  }

  async function createOrLoadProfile() {
    const payload = profilePayload(form);
    const savedProfile = await api("/me/profile", {
      method: "PUT",
      body: JSON.stringify(payload)
    }, authToken);
    const savedForm = profileToForm(savedProfile);
    setForm(savedForm);
    setSavedProfileForm(savedForm);
    await loadDashboard();
  }

  async function runRecommendations() {
    setDashboardJobView("recommendations");
    const data = await api("/me/recommend", {
      method: "POST",
      body: JSON.stringify({
        top_k: RECOMMENDATION_FETCH_LIMIT,
        include_feedback: true,
        exclude_dismissed: true,
        exclude_applied: true,
        include_debug: true,
        save_run: true
      })
    }, authToken);
    setRecommendations(data);
    setSelectedRun(data.run_id);
    await loadDashboard();
  }

  async function loadRun(runId, { activate = true } = {}) {
    if (activate) {
      setDashboardJobView("recommendations");
    }
    const data = await api(`/me/recommendations/${runId}`, {}, authToken);
    setRecommendations(data);
    setSelectedRun(runId);
  }

  async function actOnJob(jobId, action) {
    const response = await api(`/me/jobs/${jobId}/action`, {
      method: "POST",
      body: JSON.stringify({ action, run_id: selectedRun })
    }, authToken);
    setRecommendations((current) => updateRecommendationJobState(
      current,
      jobId,
      response.job_state?.state ?? null,
      response.job_state?.source_run_id
    ));
    await loadDashboard();
    if (dashboardJobView !== "recommendations") {
      await loadDashboardJobView(dashboardJobView);
    }
    if (recommendations && selectedRun) {
      await loadRun(selectedRun, { activate: false });
    }
  }

  useEffect(() => {
    let cancelled = false;
    document.title = "InternLens";

    async function restoreSession() {
      try {
        await api("/health", {}, authToken);
      } catch {
        if (!cancelled) {
          setApiHealth("offline");
        }
        return;
      }

      if (cancelled) return;
      setApiHealth("online");

      let restoredDashboard;
      try {
        const storedProfile = await api("/me/profile", {}, authToken);
        if (cancelled) return;
        const restoredForm = profileToForm(storedProfile);
        setForm(restoredForm);
        setSavedProfileForm(restoredForm);
        restoredDashboard = await api("/me/dashboard", {}, authToken);
      } catch (error) {
        if ([401, 403, 404].includes(error.status)) {
          if (!cancelled) {
            setSavedProfileForm(null);
            setDashboard(null);
            setRecommendations(null);
            setSelectedRun(null);
          }
          return;
        }
        return;
      }
      if (cancelled) return;
      setDashboard(restoredDashboard);

      if (storedState.selectedRun) {
        try {
          const restoredRun = await api(
            `/me/recommendations/${storedState.selectedRun}`,
            {},
            authToken
          );
          if (cancelled) return;
          setRecommendations(restoredRun);
        } catch {
          if (!cancelled) {
            setSelectedRun(null);
          }
        }
      }
    }

    restoreSession();
    return () => {
      cancelled = true;
    };
  }, [authToken, storedState.selectedRun]);

  useEffect(() => {
    writeStoredState({ form, selectedRun, recommendationFilter });
  }, [form, selectedRun, recommendationFilter]);

  return (
    <main className="shell">
      <header className="app-header">
        <div className="product-title">
          <p className="eyebrow">InternLens</p>
          <h1>Internship application board</h1>
          <p className="hero-copy">
            Review ranked leads, keep useful roles in motion, and suppress noise from the next pass.
          </p>
        </div>
        <div className={`status-card server-status ${apiHealth}`}>
          <div className="server-status-main">
            <span className={busy || apiHealth === "checking" ? "pulse-dot active" : "pulse-dot"} />
            <div>
              <p className="eyebrow">Server</p>
              <h2>{SERVER_STATUS_LABELS[apiHealth]}</h2>
            </div>
          </div>
          <div className="account-strip">
            <span>{accountEmail}</span>
            {onSignOut && <button onClick={onSignOut}>Sign out</button>}
          </div>
        </div>
      </header>

      <section className="grid two">
        <ProfilePanel
          form={form}
          setForm={setForm}
          profileState={profileState}
          quality={quality}
          busy={busy}
          status={profileStatus}
          onSubmit={() => runTask(createOrLoadProfile, { successMessage: "Profile saved. Dashboard is ready." })}
        />
        <DashboardPanel
          dashboard={dashboard}
          profileState={profileState}
          profileReady={quality.isReady}
          busy={busy}
          onRefresh={() => runTask(() => loadDashboard())}
          onRun={() => runTask(runRecommendations)}
          onLoadRun={(runId) => runTask(() => loadRun(runId))}
          activeJobView={dashboardJobView}
          onShowJobView={(view) => runTask(() => showDashboardJobView(view))}
        />
      </section>

      <RecommendationPanel
        recommendations={recommendations}
        dashboard={dashboard}
        dashboardJobView={dashboardJobView}
        dashboardJobLists={dashboardJobLists}
        selectedRun={selectedRun}
        filter={recommendationFilter}
        onFilterChange={setRecommendationFilter}
        busy={busy}
        onAction={(jobId, action) => runTask(() => actOnJob(jobId, action))}
      />
    </main>
  );
}

function AuthShell({ title, detail, action }) {
  return (
    <main className="shell auth-shell">
      <section className="panel auth-panel">
        <p className="eyebrow">InternLens</p>
        <h1>{title}</h1>
        <p>{detail}</p>
        {action}
      </section>
    </main>
  );
}

function PublicHome({ onSignIn, errorMessage }) {
  return (
    <main className="public-shell">
      <header className="public-nav">
        <div className="public-brand">
          <p className="eyebrow">InternLens</p>
          <strong>Internship application board</strong>
        </div>
        <div className="public-auth-actions" aria-label="Account actions">
          <button className="ghost-action" onClick={onSignIn}>
            Log in
          </button>
          <button className="primary-action" onClick={onSignIn}>
            Sign up
          </button>
        </div>
      </header>

      {errorMessage && (
        <section className="public-alert" role="alert">
          <strong>Sign-in problem</strong>
          <span>{errorMessage}</span>
        </section>
      )}

      <section className="public-hero">
        <p className="eyebrow">Internship discovery workspace</p>
        <h1>InternLens</h1>
        <p>
          Build a structured candidate profile, find ranked internship matches from public ATS data, and keep each
          application decision organized in one account.
        </p>
        <div className="public-hero-actions">
          <button className="primary-action" onClick={onSignIn}>
            Start matching
          </button>
          <span>Personalized profiles, shortlists, and job actions appear only after sign-in.</span>
        </div>
      </section>

      <section className="public-workflow" aria-label="How InternLens works">
        {PUBLIC_STEPS.map((step, index) => (
          <article key={step}>
            <span>{index + 1}</span>
            <strong>{step}</strong>
          </article>
        ))}
      </section>

      <section className="public-content-grid">
        <div className="public-feature-list">
          {PUBLIC_FEATURES.map((feature) => (
            <article key={feature.title}>
              <h2>{feature.title}</h2>
              <p>{feature.body}</p>
            </article>
          ))}
        </div>

        <section className="public-preview" aria-label="Sample shortlist preview">
          <div className="preview-heading">
            <p className="eyebrow">Sample preview</p>
            <h2>Ranked leads without exposing private data</h2>
          </div>
          <div className="sample-job-list">
            {PUBLIC_SAMPLE_JOBS.map((job, index) => (
              <article key={`${job.company}-${job.title}`} className="sample-job-card">
                <div>
                  <span className="sample-rank">#{index + 1}</span>
                  <h3>{job.title}</h3>
                  <p>{job.company}</p>
                </div>
                <small>{job.meta}</small>
                <p>{job.reason}</p>
              </article>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}

function AuthenticatedApp() {
  const auth = useAuth();

  async function signOut() {
    const returnUrl = window.location.origin;
    await auth.removeUser();
    window.location.assign(returnUrl);
  }

  if (auth.isLoading) {
    return <AuthShell title="Opening InternLens" detail="Checking your session." />;
  }

  if (auth.error) {
    return <PublicHome onSignIn={() => auth.signinRedirect()} errorMessage={auth.error.message} />;
  }

  if (!auth.isAuthenticated) {
    return <PublicHome onSignIn={() => auth.signinRedirect()} />;
  }

  return (
    <App
      authToken={auth.user?.access_token}
      accountEmail={auth.user?.profile?.email ?? "Signed in"}
      onSignOut={signOut}
    />
  );
}

function Root() {
  const config = oidcConfig();
  if (!config) {
    return <App />;
  }

  return (
    <AuthProvider {...config}>
      <AuthenticatedApp />
    </AuthProvider>
  );
}

function ProfilePanel({ form, setForm, profileState, quality, busy, status, onSubmit }) {
  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  const stateCopy = {
    draft: {
      label: "Profile not saved yet",
      detail: "Save once to unlock matching and dashboard history."
    },
    changed: {
      label: "Unsaved changes",
      detail: "Save changes before finding a fresh shortlist."
    },
    saved: {
      label: "Saved to this account",
      detail: "Your dashboard and future shortlists use this profile."
    }
  }[profileState];

  return (
    <section className="panel profile-panel">
      <div className="panel-heading">
        <p className="eyebrow">Profile Setup</p>
        <h2>Candidate information</h2>
      </div>
      <div className={`profile-state ${profileState}`}>
        <strong>{stateCopy.label}</strong>
        <span>{stateCopy.detail}</span>
      </div>
      <ProfileQuality quality={quality} />
      <div className="form-grid">
        <label>
          Graduation
          <input type="month" value={form.grad_date} onChange={(event) => update("grad_date", event.target.value)} />
        </label>
        <label>
          Degree
          <select value={form.degree_level} onChange={(event) => update("degree_level", event.target.value)}>
            <option value="">Select degree</option>
            {DEGREE_OPTIONS.map((degree) => (
              <option key={degree} value={degree}>
                {degree}
              </option>
            ))}
          </select>
        </label>
        <label>
          Experience years
          <input
            type="number"
            min="0"
            value={form.years_of_experience}
            onChange={(event) => update("years_of_experience", event.target.value)}
          />
        </label>
        <ChipSelector
          title="Preferred roles"
          value={form.preferred_roles}
          options={ROLE_OPTIONS}
          customPlaceholder="Add another role"
          onChange={(value) => update("preferred_roles", value)}
        />
        <ChipSelector
          title="Skills"
          value={form.extracted_skills}
          options={SKILL_OPTIONS}
          customPlaceholder="Search or add skill"
          onChange={(value) => update("extracted_skills", value)}
        />
        <ChipSelector
          title="Locations"
          value={form.preferred_locations}
          options={LOCATION_OPTIONS}
          customPlaceholder="Add another location"
          onChange={(value) => update("preferred_locations", value)}
        />
        <ChipSelector
          title="Industries"
          value={form.target_industries}
          options={INDUSTRY_OPTIONS}
          customPlaceholder="Add another industry"
          onChange={(value) => update("target_industries", value)}
        />
        <label className="check-row">
          <input
            type="checkbox"
            checked={form.sponsorship_need}
            onChange={(event) => update("sponsorship_need", event.target.checked)}
          />
          Needs sponsorship
        </label>
        <label className="wide">
          Additional background
          <textarea
            value={form.resume_text}
            placeholder="Optional context: projects, coursework, research, domain interests, or constraints."
            onChange={(event) => update("resume_text", event.target.value)}
          />
        </label>
      </div>
      <button className="primary-action" disabled={busy || !quality.isReady} onClick={onSubmit}>
        {busy
          ? "Saving..."
          : !quality.isReady
          ? "Complete essentials"
          : profileState === "changed"
          ? "Save changes"
          : "Save profile"}
      </button>
      {!quality.isReady && (
        <p className="profile-save-note">Complete the required items above before saving this profile.</p>
      )}
      {status && <p className={`form-status ${status.type}`}>{status.message}</p>}
    </section>
  );
}

function ProfileQuality({ quality }) {
  return (
    <div className={`quality-card ${quality.isReady ? "ready" : "needs-work"}`}>
      <div className="quality-heading">
        <strong>{quality.isReady ? "Ready for matching" : "Profile quality"}</strong>
        <span>
          {quality.requiredComplete}/{quality.requiredTotal} required
        </span>
      </div>
      <div className="quality-list">
        {quality.items.map((item) => (
          <div key={item.label} className={item.complete ? "complete" : "incomplete"}>
            <span>{item.complete ? "Done" : item.required ? "Needed" : "Optional"}</span>
            <div>
              <strong>{item.label}</strong>
              <small>{item.detail}</small>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ChipSelector({ title, value, options = [], customPlaceholder, onChange }) {
  const [query, setQuery] = useState("");
  const selectedItems = csvToList(value);
  const normalizedSelected = new Set(selectedItems.map((item) => item.toLowerCase()));
  const normalizedQuery = query.trim().toLowerCase();
  const suggestions = options
    .filter((item) => !normalizedSelected.has(item.toLowerCase()))
    .filter((item) => !normalizedQuery || item.toLowerCase().includes(normalizedQuery))
    .slice(0, 7);

  function removeItem(item) {
    onChange(removeCsvItem(value, item));
  }

  function addItems(items) {
    if (items.length === 0) {
      return;
    }
    onChange(addCsvItems(value, items));
    setQuery("");
  }

  function addQuery() {
    addItems(csvToList(query));
  }

  return (
    <div className="selector-field wide">
      <div className="selector-heading">
        <strong>{title}</strong>
        <span>{selectedItems.length} selected</span>
      </div>
      {selectedItems.length > 0 && (
        <div className="selected-chip-row" aria-label={`Selected ${title.toLowerCase()}`}>
          {selectedItems.map((item) => (
            <button key={item} type="button" onClick={() => removeItem(item)} title={`Remove ${item}`}>
              {item}
            </button>
          ))}
        </div>
      )}
      <div className="search-select">
        <input
          value={query}
          placeholder={customPlaceholder}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              addQuery();
            }
          }}
        />
        <button type="button" disabled={!query.trim()} onClick={addQuery}>
          Add
        </button>
      </div>
      {query.trim() && suggestions.length > 0 && (
        <div className="suggestion-menu" aria-label={`${title} suggestions`}>
          {suggestions.map((item) => (
            <button key={item} type="button" onClick={() => addItems([item])}>
              {item}
            </button>
          ))}
        </div>
      )}
      {query.trim() && suggestions.length === 0 && (
        <p className="suggestion-empty">Press Add to use this custom value.</p>
      )}
    </div>
  );
}

function DashboardPanel({
  dashboard,
  profileState,
  profileReady,
  busy,
  onRefresh,
  onRun,
  onLoadRun,
  activeJobView,
  onShowJobView
}) {
  const summary = dashboard?.summary;
  const canFindMatches = Boolean(dashboard) && profileState === "saved" && profileReady;

  return (
    <section className="panel dashboard-panel">
      <div className="panel-heading split">
        <div>
          <p className="eyebrow">Dashboard</p>
          <h2>Current application board</h2>
        </div>
        <button className="ghost-action" disabled={busy || !dashboard} onClick={onRefresh}>
          Refresh
        </button>
      </div>

      {!dashboard ? (
        <div className="empty-state">
          <strong>No profile loaded</strong>
          <span>Save the candidate profile to open the dashboard.</span>
        </div>
      ) : (
        <>
          <div className="metric-row">
            <Metric
              label="Shortlists"
              value={summary.recommendation_run_count}
              active={activeJobView === "recommendations"}
              onClick={() => onShowJobView("recommendations")}
            />
            <Metric
              label="Saved"
              value={summary.saved_jobs_count}
              active={activeJobView === "saved"}
              onClick={() => onShowJobView("saved")}
            />
            <Metric
              label="Applied"
              value={summary.applied_jobs_count}
              active={activeJobView === "applied"}
              onClick={() => onShowJobView("applied")}
            />
            <Metric
              label="Hidden"
              value={summary.dismissed_jobs_count}
              active={activeJobView === "dismissed"}
              onClick={() => onShowJobView("dismissed")}
            />
          </div>

          <div className="next-actions">
            {dashboard.recommended_next_actions.length === 0 ? (
              <article>
                <span>No pending actions</span>
                <p>The current board has no saved or applied follow-up items.</p>
              </article>
            ) : (
              dashboard.recommended_next_actions.map((action) => (
                <article key={`${action.action}-${action.target_job_id ?? action.target_run_id ?? "none"}`}>
                  <span>{action.label}</span>
                  <p>{action.description}</p>
                </article>
              ))
            )}
          </div>

          <button className="primary-action" disabled={busy || !canFindMatches} onClick={onRun}>
            {!profileReady ? "Complete profile first" : profileState === "changed" ? "Save changes first" : "Find matches"}
          </button>
          {(!profileReady || profileState !== "saved") && (
            <p className="dashboard-action-note">
              {!profileReady
                ? "Complete the required profile items before running a shortlist."
                : "Save the profile before running a new shortlist."}
            </p>
          )}

          <div className="mini-columns">
            <PreviewList title="Saved jobs" items={dashboard.saved_jobs} empty="No saved jobs yet." />
            <PreviewList title="Applied jobs" items={dashboard.applied_jobs} empty="No applied jobs yet." />
          </div>

          <div className="dashboard-lower">
            <ActivityList activities={dashboard.activity.activities} jobLookup={jobStateLookup(dashboard)} />
            <RunList
              runs={dashboard.recent_runs}
              totalRuns={summary.recommendation_run_count}
              onLoadRun={onLoadRun}
            />
          </div>
        </>
      )}
    </section>
  );
}

function RecommendationPanel({
  recommendations,
  dashboard,
  dashboardJobView,
  dashboardJobLists,
  selectedRun,
  filter,
  onFilterChange,
  busy,
  onAction
}) {
  const [page, setPage] = useState(1);
  const showingDashboardJobs = dashboardJobView !== "recommendations";
  const dashboardView = DASHBOARD_JOB_VIEWS[dashboardJobView] ?? DASHBOARD_JOB_VIEWS.recommendations;
  const dashboardStateJobs = showingDashboardJobs
    ? (dashboardJobLists[dashboardJobView] ?? dashboard?.[`${dashboardJobView}_jobs`] ?? []).map(storedJobStateToRecommendation)
    : [];
  const jobs = showingDashboardJobs ? dashboardStateJobs : recommendations?.results ?? [];
  const counts = recommendationCounts(jobs);
  const visibleJobs = showingDashboardJobs ? jobs : visibleRecommendations(jobs, filter);
  const hasBoard = showingDashboardJobs ? Boolean(dashboard) : Boolean(recommendations);
  const heading = showingDashboardJobs
    ? dashboardView.heading
    : selectedRun ? DASHBOARD_JOB_VIEWS.recommendations.heading : "No shortlist loaded";
  const resultTotal = showingDashboardJobs ? jobs.length : recommendations?.returned_jobs;
  const pageCount = Math.max(1, Math.ceil(visibleJobs.length / RECOMMENDATION_PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const pageStart = visibleJobs.length === 0 ? 0 : (currentPage - 1) * RECOMMENDATION_PAGE_SIZE + 1;
  const pageEnd = Math.min(currentPage * RECOMMENDATION_PAGE_SIZE, visibleJobs.length);
  const pagedJobs = visibleJobs.slice(pageStart === 0 ? 0 : pageStart - 1, pageEnd);

  useEffect(() => {
    setPage(1);
  }, [dashboardJobView, selectedRun, filter, visibleJobs.length]);

  return (
    <section className="panel results-panel">
      <div className="panel-heading split">
        <div>
          <p className="eyebrow">{showingDashboardJobs ? "Dashboard jobs" : "Recommendations"}</p>
          <h2>{heading}</h2>
        </div>
        {hasBoard && (
          <span className="result-count">
            {pageStart}-{pageEnd} of {resultTotal} shown
          </span>
        )}
      </div>

      {!hasBoard ? (
        <div className="empty-state">
          <strong>{showingDashboardJobs ? dashboardView.heading : "No shortlist loaded"}</strong>
          <span>{dashboardView.empty}</span>
        </div>
      ) : (
        <>
          {!showingDashboardJobs && (
            <div className="filter-bar" aria-label="Recommendation filters">
              {ACTION_FILTERS.map((item) => (
                <button
                  key={item.value}
                  className={filter === item.value ? "active" : ""}
                  onClick={() => onFilterChange(item.value)}
                >
                  <span>{item.label}</span>
                  <strong>{counts[item.value] ?? 0}</strong>
                </button>
              ))}
            </div>
          )}

          {visibleJobs.length === 0 ? (
            <div className="empty-state">
              <strong>No jobs shown</strong>
              <span>
                {showingDashboardJobs
                  ? dashboardView.empty
                  : jobs.length === 0
                  ? "This shortlist has no visible roles. Applied and hidden roles are excluded from new shortlists."
                  : "No jobs match the selected recommendation filter."}
              </span>
            </div>
          ) : (
            <>
              <PaginationControls
                currentPage={currentPage}
                pageCount={pageCount}
                pageStart={pageStart}
                pageEnd={pageEnd}
                total={visibleJobs.length}
                onPageChange={setPage}
              />
              <div className="job-list">
                {pagedJobs.map((job) => (
                  <JobCard key={job.job_id} job={job} busy={busy} onAction={onAction} />
                ))}
              </div>
              <PaginationControls
                currentPage={currentPage}
                pageCount={pageCount}
                pageStart={pageStart}
                pageEnd={pageEnd}
                total={visibleJobs.length}
                onPageChange={setPage}
              />
            </>
          )}
        </>
      )}
    </section>
  );
}

function PaginationControls({ currentPage, pageCount, pageStart, pageEnd, total, onPageChange }) {
  if (pageCount <= 1) {
    return null;
  }

  return (
    <nav className="pagination" aria-label="Shortlist pages">
      <button type="button" disabled={currentPage === 1} onClick={() => onPageChange(currentPage - 1)}>
        Previous
      </button>
      <span>
        {pageStart}-{pageEnd} of {total} · Page {currentPage} / {pageCount}
      </span>
      <button type="button" disabled={currentPage === pageCount} onClick={() => onPageChange(currentPage + 1)}>
        Next
      </button>
    </nav>
  );
}

function JobCard({ job, busy, onAction }) {
  const score = displayScore(job);
  const label = actionLabel(job);
  const action = actionValue(job);
  const currentState = job.user_job_state;
  const positives = positiveEvidence(job);
  const watchouts = watchoutEvidence(job);
  const skills = skillSignals(job);
  const eligibility = eligibilityLabel(job.eligibility_status);
  const isSaved = currentState === "saved";
  const isApplied = currentState === "applied";
  const isDismissed = currentState === "dismissed";

  return (
    <article className={`job-card ${actionClass(label ?? action)} ${currentState ? `state-${currentState}` : ""}`}>
      <div>
        <div className="job-meta">
          <span>{job.company}</span>
          <span>{job.location}</span>
          <span>{titleCase(job.fit_level)}</span>
          {label && <span className={`action-pill ${actionClass(label)}`}>{label}</span>}
          {currentState && <span className={`state-pill ${currentState}`}>{JOB_STATE_LABELS[currentState] ?? currentState}</span>}
        </div>
        <h3>{job.title}</h3>
        <p className="fit-summary">{fitSummary(job)}</p>
        {job.summary && <p className="job-summary">{job.summary}</p>}
        {skills.length > 0 && (
          <div className="skill-chip-row" aria-label="Matched skills">
            {skills.map((skill) => (
              <span key={skill}>{skill}</span>
            ))}
          </div>
        )}
        {eligibility && (
          <div className="job-detail-row">
            <span>{eligibility}</span>
          </div>
        )}

        <div className="evidence-grid">
          <EvidenceList title="Why it fits" items={positives} empty="No strong positive signals surfaced." />
          <EvidenceList title="What to check" items={watchouts} empty="No major watchouts surfaced." />
        </div>
      </div>
      <div className="job-side">
        <ScoreDial score={score} fitLevel={job.fit_level} />
        <div className="job-actions">
          {job.application_link && (
            <a href={job.application_link} target="_blank" rel="noreferrer">
              Open
            </a>
          )}
          <button disabled={busy || isSaved || isApplied || isDismissed} onClick={() => onAction(job.job_id, "save")}>
            {isSaved ? "Saved" : "Save"}
          </button>
          <button disabled={busy || isApplied || isDismissed} onClick={() => onAction(job.job_id, "apply")}>
            {isApplied ? "Applied" : "Mark applied"}
          </button>
          <button disabled={busy || isDismissed || isApplied} onClick={() => onAction(job.job_id, "dismiss")}>
            {isDismissed ? "Hidden" : "Hide role"}
          </button>
          {currentState && (
            <button className="subtle-action" disabled={busy} onClick={() => onAction(job.job_id, "clear")}>
              {clearActionLabel(currentState)}
            </button>
          )}
        </div>
        {isDismissed && (
          <p className="state-note">
            Hidden from future shortlists. Open Dashboard Hidden to review it or use Show again.
          </p>
        )}
      </div>
    </article>
  );
}

function ScoreDial({ score, fitLevel }) {
  const safeScore = score ?? 0;

  return (
    <div className={`score-dial ${fitLevel}`} style={{ "--score": `${Math.min(Math.max(safeScore, 0), 100) * 3.6}deg` }}>
      <strong>{score ?? "--"}</strong>
      <span>{score === null ? "no score" : "score"}</span>
    </div>
  );
}

function EvidenceList({ title, items = [], empty }) {
  const visibleItems = items.filter(Boolean).slice(0, 3);

  return (
    <div className="evidence-list">
      <h4>{title}</h4>
      {visibleItems.length === 0 ? (
        <p>{empty}</p>
      ) : (
        <ul>
          {visibleItems.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Metric({ label, value, active, onClick }) {
  return (
    <button type="button" className={`metric ${active ? "active" : ""}`} onClick={onClick}>
      <strong>{value}</strong>
      <span>{label}</span>
    </button>
  );
}

function ActivityList({ activities, jobLookup }) {
  return (
    <section className="activity-list">
      <h3>Activity</h3>
      {activities.length === 0 ? (
        <p className="muted">No recent activity yet.</p>
      ) : (
        activities.map((activity) => (
          <article key={`${activity.activity_type}-${activity.created_at}-${activity.job_id ?? activity.run_id ?? "none"}`}>
            <span className={`activity-badge ${actionClass(activityBadgeLabel(activity))}`}>
              {activityBadgeLabel(activity)}
            </span>
            <div>
              <strong>{activityTitle(activity, jobLookup)}</strong>
              <small>{compactTimestamp(activity.created_at)}</small>
            </div>
          </article>
        ))
      )}
    </section>
  );
}

function RunList({ runs, totalRuns, onLoadRun }) {
  return (
    <section className="run-list">
      <h3>Previous shortlists</h3>
      {runs.length === 0 ? (
        <p className="muted">No previous shortlists yet. Start one from this dashboard.</p>
      ) : (
        runs.map((run, index) => (
          <button key={run.run_id} onClick={() => onLoadRun(run.run_id)}>
            <span>Shortlist {Math.max(totalRuns - index, 1)}</span>
            <small>{run.returned_jobs} roles · {compactTimestamp(run.created_at)}</small>
          </button>
        ))
      )}
    </section>
  );
}

function PreviewList({ title, items, empty }) {
  return (
    <div className="preview-list">
      <h3>{title}</h3>
      {items.length === 0 ? (
        <p className="muted">{empty}</p>
      ) : (
        items.map((item) => (
          <div className="preview-item" key={item.job_id}>
            <strong>{item.job_snapshot?.title ?? "Saved role"}</strong>
            <span>{item.job_snapshot?.company ?? titleCase(item.state ?? "tracked")}</span>
          </div>
        ))
      )}
    </div>
  );
}

createRoot(document.getElementById("root")).render(<Root />);
