export const ACTION_FILTERS = [
  { value: "all", label: "All" },
  { value: "apply_now", label: "Apply Now" },
  { value: "apply_later", label: "Apply Later" },
  { value: "skip", label: "Skip" }
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
