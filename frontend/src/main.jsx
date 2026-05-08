import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
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
import { activityLabel, activityTitle, compactTimestamp } from "./dashboardHelpers";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const STORAGE_KEY = "internlens.ui.state";

const JOB_STATE_LABELS = {
  saved: "Saved",
  applied: "Applied",
  dismissed: "Dismissed"
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

const defaultProfile = {
  profile_id: "user_001",
  resume_text: "Graduate student with Python, machine learning, ranking systems, and data analysis experience.",
  degree_level: "Master's",
  grad_date: "2027-12",
  preferred_roles: "Machine Learning Engineer Intern, Applied Scientist Intern, Data Science Intern",
  preferred_locations: "Remote, California",
  target_industries: "AI, Tech",
  sponsorship_need: true,
  extracted_skills: "Python, Machine Learning, PyTorch, Data Analysis",
  years_of_experience: 1,
  notes: "Interested in recommendation and ranking systems"
};

function csvToList(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
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

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {})
    },
    ...options
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail ?? `Request failed: ${response.status}`);
  }
  return body;
}

function App() {
  const [storedState] = useState(() => readStoredState());
  const [form, setForm] = useState(() => ({ ...defaultProfile, ...(storedState.form ?? {}) }));
  const [profileId, setProfileId] = useState(
    () => storedState.profileId ?? storedState.form?.profile_id ?? defaultProfile.profile_id
  );
  const [dashboard, setDashboard] = useState(null);
  const [recommendations, setRecommendations] = useState(null);
  const [selectedRun, setSelectedRun] = useState(() => storedState.selectedRun ?? null);
  const [recommendationFilter, setRecommendationFilter] = useState(() => storedState.recommendationFilter ?? "all");
  const [apiHealth, setApiHealth] = useState("checking");
  const [busy, setBusy] = useState(false);

  async function runTask(task) {
    setBusy(true);
    try {
      await task();
      setApiHealth("online");
    } catch (error) {
      if (String(error.message).includes("fetch")) {
        setApiHealth("offline");
      }
    } finally {
      setBusy(false);
    }
  }

  async function loadDashboard(id = profileId) {
    const data = await api(`/profiles/${id}/dashboard`);
    setDashboard(data);
    setProfileId(id);
  }

  async function createOrLoadProfile() {
    const payload = profilePayload(form);
    try {
      await api("/profiles", {
        method: "POST",
        body: JSON.stringify(payload)
      });
    } catch (error) {
      if (!String(error.message).includes("already exists")) {
        throw error;
      }
      await api(`/profiles/${payload.profile_id}`);
    }
    await loadDashboard(payload.profile_id);
  }

  async function runRecommendations() {
    const data = await api(`/profiles/${profileId}/recommend`, {
      method: "POST",
      body: JSON.stringify({
        top_k: 8,
        include_feedback: true,
        exclude_dismissed: true,
        exclude_applied: true,
        include_debug: true,
        save_run: true
      })
    });
    setRecommendations(data);
    setSelectedRun(data.run_id);
    await loadDashboard(profileId);
  }

  async function loadRun(runId) {
    const data = await api(`/profiles/${profileId}/recommendations/${runId}`);
    setRecommendations(data);
    setSelectedRun(runId);
  }

  async function actOnJob(jobId, action) {
    await api(`/profiles/${profileId}/jobs/${jobId}/action`, {
      method: "POST",
      body: JSON.stringify({ action, run_id: selectedRun })
    });
    await loadDashboard(profileId);
    if (recommendations && selectedRun) {
      await loadRun(selectedRun);
    }
  }

  useEffect(() => {
    let cancelled = false;
    document.title = "InternLens";

    async function restoreSession() {
      try {
        await api("/health");
        if (cancelled) return;
        setApiHealth("online");

        if (!storedState.profileId) {
          return;
        }

        const restoredDashboard = await api(`/profiles/${storedState.profileId}/dashboard`);
        if (cancelled) return;
        setDashboard(restoredDashboard);

        if (storedState.selectedRun) {
          try {
            const restoredRun = await api(`/profiles/${storedState.profileId}/recommendations/${storedState.selectedRun}`);
            if (cancelled) return;
            setRecommendations(restoredRun);
          } catch {
            if (!cancelled) {
              setSelectedRun(null);
            }
          }
        }
      } catch {
        if (cancelled) return;
        setApiHealth("offline");
      }
    }

    restoreSession();
    return () => {
      cancelled = true;
    };
  }, [storedState.profileId, storedState.selectedRun]);

  useEffect(() => {
    writeStoredState({ form, profileId, selectedRun, recommendationFilter });
  }, [form, profileId, selectedRun, recommendationFilter]);

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
          <span className={busy || apiHealth === "checking" ? "pulse-dot active" : "pulse-dot"} />
          <div>
            <p className="eyebrow">Server</p>
            <h2>{SERVER_STATUS_LABELS[apiHealth]}</h2>
          </div>
        </div>
      </header>

      <section className="grid two">
        <ProfilePanel
          form={form}
          setForm={setForm}
          busy={busy}
          onSubmit={() => runTask(createOrLoadProfile)}
        />
        <DashboardPanel
          dashboard={dashboard}
          profileId={profileId}
          busy={busy}
          onRefresh={() => runTask(() => loadDashboard(profileId))}
          onRun={() => runTask(runRecommendations)}
          onLoadRun={(runId) => runTask(() => loadRun(runId))}
        />
      </section>

      <RecommendationPanel
        recommendations={recommendations}
        selectedRun={selectedRun}
        filter={recommendationFilter}
        onFilterChange={setRecommendationFilter}
        busy={busy}
        onAction={(jobId, action) => runTask(() => actOnJob(jobId, action))}
      />
    </main>
  );
}

function ProfilePanel({ form, setForm, busy, onSubmit }) {
  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  return (
    <section className="panel profile-panel">
      <div className="panel-heading">
        <p className="eyebrow">Profile Setup</p>
        <h2>Candidate information</h2>
      </div>
      <div className="form-grid">
        <label>
          User ID
          <input value={form.profile_id} onChange={(event) => update("profile_id", event.target.value)} />
        </label>
        <label>
          Graduation
          <input type="month" value={form.grad_date} onChange={(event) => update("grad_date", event.target.value)} />
        </label>
        <label>
          Degree
          <select value={form.degree_level} onChange={(event) => update("degree_level", event.target.value)}>
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
        <label className="wide">
          Resume text
          <textarea value={form.resume_text} onChange={(event) => update("resume_text", event.target.value)} />
        </label>
        <label className="wide">
          Preferred roles
          <input value={form.preferred_roles} onChange={(event) => update("preferred_roles", event.target.value)} />
        </label>
        <label className="wide">
          Skills
          <input value={form.extracted_skills} onChange={(event) => update("extracted_skills", event.target.value)} />
        </label>
        <label>
          Locations
          <input value={form.preferred_locations} onChange={(event) => update("preferred_locations", event.target.value)} />
        </label>
        <label>
          Industries
          <input value={form.target_industries} onChange={(event) => update("target_industries", event.target.value)} />
        </label>
        <label className="check-row">
          <input
            type="checkbox"
            checked={form.sponsorship_need}
            onChange={(event) => update("sponsorship_need", event.target.checked)}
          />
          Needs sponsorship
        </label>
      </div>
      <button className="primary-action" disabled={busy} onClick={onSubmit}>
        Save profile
      </button>
    </section>
  );
}

function DashboardPanel({ dashboard, busy, onRefresh, onRun, onLoadRun }) {
  const summary = dashboard?.summary;

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
            <Metric label="Runs" value={summary.recommendation_run_count} />
            <Metric label="Saved" value={summary.saved_jobs_count} />
            <Metric label="Applied" value={summary.applied_jobs_count} />
            <Metric label="Dismissed" value={summary.dismissed_jobs_count} />
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

          <button className="primary-action" disabled={busy} onClick={onRun}>
            Run recommendations
          </button>

          <div className="mini-columns">
            <PreviewList title="Saved jobs" items={dashboard.saved_jobs} empty="No saved jobs yet." />
            <PreviewList title="Applied jobs" items={dashboard.applied_jobs} empty="No applied jobs yet." />
          </div>

          <div className="dashboard-lower">
            <ActivityList activities={dashboard.activity.activities} />
            <RunList runs={dashboard.recent_runs} onLoadRun={onLoadRun} />
          </div>
        </>
      )}
    </section>
  );
}

function RecommendationPanel({ recommendations, selectedRun, filter, onFilterChange, busy, onAction }) {
  const jobs = recommendations?.results ?? [];
  const counts = recommendationCounts(jobs);
  const visibleJobs = visibleRecommendations(jobs, filter);

  return (
    <section className="panel results-panel">
      <div className="panel-heading split">
        <div>
          <p className="eyebrow">Recommendations</p>
          <h2>{selectedRun ? `Run ${selectedRun.slice(0, 12)}` : "No run loaded"}</h2>
        </div>
        {recommendations && <span className="result-count">{visibleJobs.length} of {recommendations.returned_jobs} shown</span>}
      </div>

      {!recommendations ? (
        <div className="empty-state">
          <strong>No run loaded</strong>
          <span>Run recommendations or load a recent run to review ranked internship leads.</span>
        </div>
      ) : (
        <>
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

          {visibleJobs.length === 0 ? (
            <div className="empty-state">
              <strong>No jobs shown</strong>
              <span>
                {jobs.length === 0
                  ? "This run returned no visible jobs. Applied and dismissed jobs are excluded from new runs."
                  : "No jobs match the selected recommendation filter."}
              </span>
            </div>
          ) : (
            <div className="job-list">
              {visibleJobs.map((job) => (
                <JobCard key={job.job_id} job={job} busy={busy} onAction={onAction} />
              ))}
            </div>
          )}
        </>
      )}
    </section>
  );
}

function JobCard({ job, busy, onAction }) {
  const score = displayScore(job);
  const label = actionLabel(job);
  const action = actionValue(job);
  const currentState = job.user_job_state;
  const watchouts = job.watchouts ?? job.blocking_issues ?? [];
  const isSaved = currentState === "saved";
  const isApplied = currentState === "applied";
  const isDismissed = currentState === "dismissed";

  return (
    <article className={`job-card ${actionClass(label ?? action)} ${currentState ? `state-${currentState}` : ""}`}>
      <div>
        <div className="job-meta">
          <span>{job.company}</span>
          <span>{job.location}</span>
          <span>{job.fit_level}</span>
          {label && <span className={`action-pill ${actionClass(label)}`}>{label}</span>}
          {currentState && <span className={`state-pill ${currentState}`}>{JOB_STATE_LABELS[currentState] ?? currentState}</span>}
        </div>
        <h3>{job.title}</h3>
        <p>{job.summary}</p>
        <div className="job-detail-row">
          <span>{job.eligibility_status}</span>
          <span>{job.recommendation}</span>
          {job.user_job_state_source_run_id && <span>from run {job.user_job_state_source_run_id.slice(0, 12)}</span>}
        </div>

        <div className="evidence-grid">
          <EvidenceList title="Why it fits" items={job.why_apply} empty="No strong positive signals surfaced." />
          <EvidenceList title="Watchouts" items={watchouts} empty="No major watchouts surfaced." />
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
            {isDismissed ? "Dismissed" : "Dismiss"}
          </button>
          {currentState && (
            <button className="subtle-action" disabled={busy} onClick={() => onAction(job.job_id, "clear")}>
              Clear state
            </button>
          )}
        </div>
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

function Metric({ label, value }) {
  return (
    <div className="metric">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function ActivityList({ activities }) {
  return (
    <section className="activity-list">
      <h3>Activity</h3>
      {activities.length === 0 ? (
        <p className="muted">No recent activity yet.</p>
      ) : (
        activities.map((activity) => (
          <article key={`${activity.activity_type}-${activity.created_at}-${activity.job_id ?? activity.run_id ?? "none"}`}>
            <span className={`activity-badge ${actionClass(activity.activity_type)}`}>
              {activityLabel(activity.activity_type)}
            </span>
            <div>
              <strong>{activityTitle(activity)}</strong>
              <small>{compactTimestamp(activity.created_at)}</small>
            </div>
          </article>
        ))
      )}
    </section>
  );
}

function RunList({ runs, onLoadRun }) {
  return (
    <section className="run-list">
      <h3>Recent runs</h3>
      {runs.length === 0 ? (
        <p className="muted">No recommendation runs yet. Start one from this dashboard.</p>
      ) : (
        runs.map((run) => (
          <button key={run.run_id} onClick={() => onLoadRun(run.run_id)}>
            <span>{run.run_id.slice(0, 12)}</span>
            <small>{run.returned_jobs} jobs · {compactTimestamp(run.created_at)}</small>
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
            <strong>{item.job_snapshot?.title ?? item.job_id}</strong>
            <span>{item.job_snapshot?.company ?? item.state}</span>
          </div>
        ))
      )}
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
