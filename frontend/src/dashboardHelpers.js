export function compactTimestamp(value) {
  if (!value) {
    return "";
  }

  const normalized = String(value).replace("T", " ").replace("Z", "");
  return normalized.slice(0, 16);
}

export function activityLabel(activityType = "") {
  const labels = {
    applied: "Applied",
    dismissed: "Dismissed",
    feedback: "Feedback",
    recommendation_run: "Run",
    saved: "Saved"
  };
  return labels[activityType] ?? activityType.replace(/_/g, " ");
}

export function activityTitle(activity) {
  if (activity.title) {
    return activity.title;
  }
  if (activity.summary) {
    return activity.summary;
  }
  if (activity.job_id) {
    return activity.job_id;
  }
  if (activity.run_id) {
    return `Run ${activity.run_id.slice(0, 12)}`;
  }
  return activityLabel(activity.activity_type);
}
