import type { ApiError, VerifyRequest, VerifyResponse } from "./types";

export async function verifyComposition(
  payload: VerifyRequest,
  baseUrl = ""
): Promise<VerifyResponse> {
  const response = await fetch(`${baseUrl}/api/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (response.ok) {
    return (await response.json()) as VerifyResponse;
  }
  let message = `服务异常（HTTP ${response.status}）`;
  let field = "";
  try {
    const data = await response.json();
    if (data?.error?.message) {
      message = String(data.error.message);
      field = String(data.error.field ?? "");
    }
  } catch {
    // Non-JSON error body: keep the generic message.
  }
  throw { message, field } satisfies ApiError;
}
