import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://backend:8000";

export async function GET(req: NextRequest) {
  const token = req.headers.get("authorization");
  try {
    const res = await fetch(`${BACKEND}/users/me/telegram-status`, {
      headers: { ...(token ? { Authorization: token } : {}) },
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (e) {
    return NextResponse.json({ connected: false, error: String(e) }, { status: 502 });
  }
}
