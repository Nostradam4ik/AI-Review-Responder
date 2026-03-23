import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const token = req.headers.get("authorization");

  const res = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL || "http://backend:8000"}/reviews/test-telegram`,
    {
      method: "POST",
      headers: {
        ...(token ? { Authorization: token } : {}),
        "Content-Type": "application/json",
      },
    }
  );

  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
