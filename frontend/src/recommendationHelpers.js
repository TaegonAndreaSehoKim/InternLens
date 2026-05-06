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
