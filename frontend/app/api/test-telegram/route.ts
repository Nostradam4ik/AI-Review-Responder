import { NextRequest, NextResponse } from "next/server";

// Server-side: use internal Docker hostname, not localhost
const BACKEND = process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://backend:8000";

export async function POST(req: NextRequest) {
  const token = req.headers.get("authorization");

  try {
    const res = await fetch(`${BACKEND}/reviews/test-telegram`, {
      method: "POST",
      headers: {
        ...(token ? { Authorization: token } : {}),
        "Content-Type": "application/json",
      },
    });

    const text = await res.text();
    let data: unknown;
    try {
      data = JSON.parse(text);
    } catch {
      data = { ok: false, message: text || "Empty response from backend" };
    }

    return NextResponse.json(data, { status: res.status });
  } catch (e) {
    console.error("[test-telegram proxy] fetch error:", e);
    return NextResponse.json(
      { ok: false, message: `Could not reach backend: ${String(e)}` },
      { status: 502 }
    );
  }
}
