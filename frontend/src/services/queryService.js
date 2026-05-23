const BASE_URL = import.meta.env.VITE_QUERY_API_URL ?? "/api/query";

export async function askQuestion(question) {
  const response = await fetch(`${BASE_URL}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Query service error (${response.status}): ${body}`);
  }

  return response.json();
}
