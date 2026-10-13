import { createClient } from "@supabase/supabase-js";

const supabaseUrl =
  process.env.NEXT_PUBLIC_SUPABASE_URL ||
  process.env.SUPABASE_URL ||
  "https://gifwhorzaubjysfukykr.supabase.co";

const supabaseAnonKey =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
  process.env.SUPABASE_KEY ||
  process.env.SUPABASE_SERVICE_KEY ||
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdpZndob3J6YXVianlzZnVreWtyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NDM3ODYwOCwiZXhwIjoyMDk5OTU0NjA4fQ.BogTI5ee1ClpT5-LxxRShQChNUNhE1cEg8U1WmeDCiM";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

