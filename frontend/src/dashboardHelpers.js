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
    dismissed: "Hidden",
    feedback: "Feedback",
    recommendation_run: "Shortlist",
    saved: "Saved"
  };
  return labels[activityType] ?? activityType.replace(/_/g, " ");
}

export function activityBadgeLabel(activity) {
  if (activity.activity_type === "feedback" && activity.label) {
    const labels = {
      applied: "Applied",
      saved: "Saved",
      skipped: "Hidden"
    };
    return labels[activity.label] ?? activityLabel(activity.label);
  }
  return activityLabel(activity.activity_type);
}

function looksInternal(value = "") {
  const text = String(value);
  const lowerText = text.toLowerCase();
  return (
    lowerText.startsWith("run_") ||
    lowerText.startsWith("job_") ||
    /\b(?:run|job)_[a-z0-9_-]+\b/i.test(text) ||
    /\b(?:greenhouse|lever)_[a-z0-9_-]+_\d{5,}\b/i.test(text) ||
    text.includes("\\") ||
    text.includes("/") ||
    text.includes(".json") ||
    text.includes("data:")
  );
}

function splitTitleAndTerm(value) {
  const termMatch = value.match(/\b(Spring|Summer|Fall|Autumn|Winter)\s+20\d{2}\b/i);
  if (!termMatch) {
    return { title: value, term: null };
  }

  const term = termMatch[0].replace(/^Autumn/i, "Fall");
  const title = value
    .replace(/\s*\((Spring|Summer|Fall|Autumn|Winter)\s+20\d{2}\)\s*/i, " ")
    .replace(/\s*[-,|]\s*(Spring|Summer|Fall|Autumn|Winter)\s+20\d{2}\s*/i, " ")
    .replace(/\b(Spring|Summer|Fall|Autumn|Winter)\s+20\d{2}\b/i, " ")
    .replace(/\s{2,}/g, " ")
    .replace(/\s*[-,|]\s*$/g, "")
    .trim();

  return { title: title || value, term };
}

export function formatJobReference(snapshot) {
  if (!snapshot) {
    return null;
  }
  const company = snapshot.company && !looksInternal(snapshot.company) ? snapshot.company : null;
  const title = snapshot.title && !looksInternal(snapshot.title) ? snapshot.title : null;

  if (!title) {
    return company;
  }

  const titleParts = splitTitleAndTerm(title);
  return [company, titleParts.title, titleParts.term].filter(Boolean).join("_");
}

export function activityTitle(activity, jobLookup = {}) {
  const relatedJob = jobLookup[activity.job_id];
  const jobReference = formatJobReference(relatedJob?.job_snapshot ?? relatedJob);

  if (activity.activity_type === "feedback") {
    const action = activityBadgeLabel(activity).toLowerCase();
    if (jobReference) {
      return `Marked ${jobReference} as ${action}`;
    }
    if (activity.summary && !looksInternal(activity.summary) && !activity.summary.toLowerCase().startsWith("marked ")) {
      return activity.summary;
    }
    return `Marked role as ${action}`;
  }
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
    return jobReference ? `Applied to ${jobReference}` : "Job marked applied";
  }
  if (activity.activity_type === "dismissed") {
    return jobReference ? `Hid ${jobReference}` : "Job hidden";
  }
  return activityLabel(activity.activity_type);
}
