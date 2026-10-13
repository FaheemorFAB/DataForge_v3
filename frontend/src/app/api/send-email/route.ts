import { NextResponse } from "next/server";
import { Resend } from "resend";

export async function GET() {
  return POST(new Request("http://localhost:3000/api/send-email", { method: "POST", body: JSON.stringify({}) }));
}

export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => ({}));
    const {
      to = "faheembaiza@gmail.com",
      subject = "Hello World",
      html = "<p>Congrats on sending your <strong>first email</strong>!</p>",
      from = "onboarding@resend.dev",
    } = body;

    // NOTE: Replace 're_xxxxxxxxx' with your real API key from https://resend.com/api-keys
    const apiKey = process.env.RESEND_API_KEY || "re_xxxxxxxxx";
    const resend = new Resend(apiKey);

    const result = await resend.emails.send({
      from,
      to: Array.isArray(to) ? to : [to],
      subject,
      html,
    });

    return NextResponse.json({ ok: true, data: result });
  } catch (err: any) {
    return NextResponse.json(
      { ok: false, error: err?.message || String(err) },
      { status: 500 }
    );
  }
}
