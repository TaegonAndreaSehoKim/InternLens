export const ACTION_FILTERS = [
  { value: "all", label: "All" },
  { value: "apply_now", label: "Apply Now" },
  { value: "apply_later", label: "Apply Later" },
  { value: "skip", label: "Skip" }
];

export const JOB_SORT_OPTIONS = [
  { value: "recommended", label: "Recommended" },
  { value: "newest", label: "Newest posting" },
  { value: "checked", label: "Recently checked" },
  { value: "score", label: "Highest score" }
];

export function actionClass(value = "") {
  return value.toLowerCase().replace(/\s+/g, "-");
}

export function actionValue(job) {
  return job.recommendation ?? actionClass(job.action_label ?? "").replace(/-/g, "_");
}

export function actionLabel(job) {
  return job.action_label ?? ACTION_FILTERS.find((filter) => filter.value === job.recommendation)?.label;
}

export function displayScore(job) {
  const score = job.reranked_score ?? job.score;
  return typeof score === "number" ? Math.round(score) : null;
}

function dateValue(value) {
  if (!value) {
    return 0;
  }

  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? 0 : parsed.getTime();
}

export function postedAgeLabel(postingDate, now = new Date()) {
  if (!postingDate) {
    return "";
  }

  const [year, month, day] = String(postingDate).split("-").map(Number);
  if (!year || !month || !day) {
    return "";
  }

  const postedTime = Date.UTC(year, month - 1, day);
  const currentTime = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  const days = Math.floor((currentTime - postedTime) / 86400000);

  if (Number.isNaN(days)) {
    return "";
  }
  if (days <= 0) {
    return "posted today";
  }
  if (days === 1) {
    return "posted 1 day ago";
  }
  return `posted ${days} days ago`;
}

export function checkedAgeLabel(fetchedAt, now = new Date()) {
  if (!fetchedAt) {
    return "";
  }

  const fetched = new Date(fetchedAt);
  if (Number.isNaN(fetched.getTime())) {
    return "";
  }

  const fetchedDay = Date.UTC(fetched.getUTCFullYear(), fetched.getUTCMonth(), fetched.getUTCDate());
  const currentDay = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  const days = Math.floor((currentDay - fetchedDay) / 86400000);

  if (Number.isNaN(days)) {
    return "";
  }
  if (days <= 0) {
    return "checked today";
  }
  if (days === 1) {
    return "checked 1 day ago";
  }
  return `checked ${days} days ago`;
}

export function stateAgeLabel(state, updatedAt, now = new Date()) {
  if (!state || !updatedAt) {
    return "";
  }

  const updated = new Date(updatedAt);
  if (Number.isNaN(updated.getTime())) {
    return "";
  }

  const verbs = {
    applied: "applied",
    dismissed: "hidden",
    saved: "saved"
  };
  const verb = verbs[state] ?? state;
  const updatedDay = Date.UTC(updated.getUTCFullYear(), updated.getUTCMonth(), updated.getUTCDate());
  const currentDay = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  const days = Math.floor((currentDay - updatedDay) / 86400000);

  if (Number.isNaN(days)) {
    return "";
  }
  if (days <= 0) {
    return `${verb} today`;
  }
  if (days === 1) {
    return `${verb} 1 day ago`;
  }
  return `${verb} ${days} days ago`;
}

export function freshnessStatus(expiresAt, now = new Date()) {
  if (!expiresAt) {
    return null;
  }

  const expires = new Date(expiresAt);
  if (Number.isNaN(expires.getTime())) {
    return null;
  }

  const expiresDay = Date.UTC(expires.getUTCFullYear(), expires.getUTCMonth(), expires.getUTCDate());
  const currentDay = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  const daysLeft = Math.ceil((expiresDay - currentDay) / 86400000);

  if (Number.isNaN(daysLeft)) {
    return null;
  }
  if (daysLeft < 0) {
    return { label: "refresh due", tone: "stale" };
  }
  if (daysLeft === 0) {
    return { label: "refresh due today", tone: "stale" };
  }
  if (daysLeft <= 2) {
    return { label: `refresh in ${daysLeft}d`, tone: "soon" };
  }
  return { label: "fresh source", tone: "fresh" };
}

export function sourceFreshnessSummary(jobs = [], now = new Date()) {
  const summary = {
    total: jobs.length,
    fresh: 0,
    soon: 0,
    stale: 0,
    unknown: 0,
    latestFetchedAt: null,
    latestCheckedLabel: ""
  };

  jobs.forEach((job) => {
    const status = freshnessStatus(job.expires_at, now);
    if (status?.tone === "fresh") {
      summary.fresh += 1;
    } else if (status?.tone === "soon") {
      summary.soon += 1;
    } else if (status?.tone === "stale") {
      summary.stale += 1;
    } else {
      summary.unknown += 1;
    }

    const fetched = new Date(job.fetched_at);
    if (!Number.isNaN(fetched.getTime())) {
      const currentLatest = summary.latestFetchedAt ? new Date(summary.latestFetchedAt) : null;
      if (!currentLatest || fetched > currentLatest) {
        summary.latestFetchedAt = job.fetched_at;
      }
    }
  });

  summary.latestCheckedLabel = checkedAgeLabel(summary.latestFetchedAt, now);
  return summary;
}

export function recommendationCounts(jobs = []) {
  return ACTION_FILTERS.reduce((current, item) => {
    current[item.value] = item.value === "all"
      ? jobs.length
      : jobs.filter((job) => actionValue(job) === item.value).length;
    return current;
  }, {});
}

export function visibleRecommendations(jobs = [], filter = "all") {
  return filter === "all" ? jobs : jobs.filter((job) => actionValue(job) === filter);
}

export function sortJobs(jobs = [], sortValue = "recommended") {
  const indexedJobs = jobs.map((job, index) => ({ job, index }));

  if (sortValue === "newest") {
    indexedJobs.sort((a, b) => dateValue(b.job.posting_date) - dateValue(a.job.posting_date) || a.index - b.index);
  } else if (sortValue === "checked") {
    indexedJobs.sort((a, b) => dateValue(b.job.fetched_at) - dateValue(a.job.fetched_at) || a.index - b.index);
  } else if (sortValue === "score") {
    indexedJobs.sort((a, b) => (displayScore(b.job) ?? -1) - (displayScore(a.job) ?? -1) || a.index - b.index);
  }

  return indexedJobs.map((item) => item.job);
}
