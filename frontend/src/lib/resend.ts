import { Resend } from "resend";

// NOTE: Replace 're_xxxxxxxxx' with your real API key from https://resend.com/api-keys
// in your .env or .env.local file as RESEND_API_KEY.
const apiKey = process.env.RESEND_API_KEY;

export const resend = new Resend(apiKey);

export interface SendEmailOptions {
  from?: string;
  to: string | string[];
  subject: string;
  html?: string;
  text?: string;
}

/**
 * Sends an email using the Resend API.
 */
export async function sendEmail({
  from = process.env.RESEND_FROM_EMAIL || "onboarding@resend.dev",
  to,
  subject,
  html = "<p>Congrats on sending your <strong>first email</strong>!</p>",
  text,
}: SendEmailOptions) {
  try {
    const data = await resend.emails.send({
      from,
      to: Array.isArray(to) ? to : [to],
      subject,
      html,
      text,
    });
    return { success: true, data };
  } catch (error: any) {
    console.error("[Resend] Failed to send email:", error);
    return { success: false, error: error?.message || error };
  }
}

/**
 * Direct test email helper matching your Resend setup.
 */
export async function sendTestEmail(to = "faheembaiza@gmail.com") {
  return await resend.emails.send({
    from: process.env.RESEND_FROM_EMAIL || "onboarding@resend.dev",
    to,
    subject: "Hello World",
    html: "<p>Congrats on sending your <strong>first email</strong>!</p>",
  });
}
