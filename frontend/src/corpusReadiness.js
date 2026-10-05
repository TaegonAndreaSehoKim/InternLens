async function fetchCorpusReadiness(api) {
  try {
    return await api("/ready");
  } catch (error) {
    if (error.status === 503 && error.data?.status === "unavailable") {
      return error.data;
    }
    throw error;
  }
}

export { fetchCorpusReadiness };
