export function compactTimestamp(value) {
  if (!value) {
    return "";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  }).format(date);
}

export function activityLabel(activityType = "") {
  const labels = {
    applied: "Applied",
    dismissed: "Dismissed",
    feedback: "Feedback",
    recommendation_run: "Recommendations",
    saved: "Saved"
  };
  return labels[activityType] ?? activityType.replace(/_/g, " ");
}

function looksInternal(value = "") {
  const text = String(value);
  return (
    text.startsWith("run_") ||
    text.startsWith("job_") ||
    text.includes("\\") ||
    text.includes("/") ||
    text.includes(".json") ||
    text.includes("data:")
  );
}

export function activityTitle(activity) {
  if (activity.title && !looksInternal(activity.title)) {
    return activity.title;
  }
  if (activity.summary && !looksInternal(activity.summary)) {
    return activity.summary;
  }
  if (activity.activity_type === "recommendation_run") {
    return "New recommendation set";
  }
  if (activity.activity_type === "saved") {
    return "Job saved";
  }
  if (activity.activity_type === "applied") {
    return "Job marked applied";
  }
  if (activity.activity_type === "dismissed") {
    return "Job dismissed";
  }
  return activityLabel(activity.activity_type);
}
