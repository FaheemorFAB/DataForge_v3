/**
 * DataForge Human Face Avatar System
 * Curated 12 distinct human face avatars with guaranteed local availability (zero broken images).
 */

export interface HumanAvatar {
  id: string;
  name: string;
  role: string;
  url: string;
  bg: string;
}

export const HUMAN_AVATARS: HumanAvatar[] = [
  {
    id: "avatar-1",
    name: "Elena Rostova",
    role: "Lead Data Scientist",
    url: "/avatars/avatar-1.svg",
    bg: "linear-gradient(135deg, #3b82f6, #1d4ed8)",
  },
  {
    id: "avatar-2",
    name: "Marcus Vance",
    role: "Chief Architect",
    url: "/avatars/avatar-2.svg",
    bg: "linear-gradient(135deg, #6366f1, #4338ca)",
  },
  {
    id: "avatar-3",
    name: "Sarah Chen",
    role: "Principal Data Engineer",
    url: "/avatars/avatar-3.svg",
    bg: "linear-gradient(135deg, #10b981, #047857)",
  },
  {
    id: "avatar-4",
    name: "David Kim",
    role: "ML Infrastructure Lead",
    url: "/avatars/avatar-4.svg",
    bg: "linear-gradient(135deg, #06b6d4, #0e7490)",
  },
  {
    id: "avatar-5",
    name: "Maya Patel",
    role: "Analytics Director",
    url: "/avatars/avatar-5.svg",
    bg: "linear-gradient(135deg, #ec4899, #be185d)",
  },
  {
    id: "avatar-6",
    name: "Alex Morgan",
    role: "AI Research Scientist",
    url: "/avatars/avatar-6.svg",
    bg: "linear-gradient(135deg, #8b5cf6, #6d28d9)",
  },
  {
    id: "avatar-7",
    name: "Amara Okafor",
    role: "Data Governance Lead",
    url: "/avatars/avatar-7.svg",
    bg: "linear-gradient(135deg, #f59e0b, #b45309)",
  },
  {
    id: "avatar-8",
    name: "Liam O'Connor",
    role: "Quant Analyst",
    url: "/avatars/avatar-8.svg",
    bg: "linear-gradient(135deg, #14b8a6, #0f766e)",
  },
  {
    id: "avatar-9",
    name: "Amina Al-Mansoor",
    role: "Security & Compliance",
    url: "/avatars/avatar-9.svg",
    bg: "linear-gradient(135deg, #a855f7, #7e22ce)",
  },
  {
    id: "avatar-10",
    name: "Robert Vance",
    role: "VP of Engineering",
    url: "/avatars/avatar-10.svg",
    bg: "linear-gradient(135deg, #64748b, #334155)",
  },
  {
    id: "avatar-11",
    name: "Chloe Dupont",
    role: "Product Analytics Lead",
    url: "/avatars/avatar-11.svg",
    bg: "linear-gradient(135deg, #f43f5e, #be123c)",
  },
  {
    id: "avatar-12",
    name: "Kenji Sato",
    role: "Full Stack ML Engineer",
    url: "/avatars/avatar-12.svg",
    bg: "linear-gradient(135deg, #38bdf8, #0284c7)",
  },
];

export const DEFAULT_AVATAR = HUMAN_AVATARS[0];

export function getSavedAvatarId(): string {
  if (typeof window === "undefined") return DEFAULT_AVATAR.id;
  try {
    const direct = localStorage.getItem("df_user_avatar");
    if (direct && (direct.startsWith("avatar-") || direct.startsWith("/"))) return direct;
    const cache = localStorage.getItem("df_user_cache");
    if (cache) {
      const u = JSON.parse(cache);
      if (u?.avatar && (u.avatar.startsWith("avatar-") || u.avatar.startsWith("/"))) return u.avatar;
    }
  } catch {}
  return DEFAULT_AVATAR.id;
}

export function getAvatarById(id?: string | null): HumanAvatar {
  const targetId = id || (typeof window !== "undefined" ? getSavedAvatarId() : DEFAULT_AVATAR.id);
  return HUMAN_AVATARS.find((a) => a.id === targetId) || DEFAULT_AVATAR;
}

export function resolveAvatarUrl(avatarOrId?: string | null): string {
  let target = avatarOrId;
  if (!target && typeof window !== "undefined") {
    target = getSavedAvatarId();
  }
  if (!target) return DEFAULT_AVATAR.url;

  if (target.startsWith("avatar-")) {
    const found = HUMAN_AVATARS.find((a) => a.id === target);
    return found ? found.url : DEFAULT_AVATAR.url;
  }
  if (
    target.startsWith("/") ||
    target.startsWith("http://") ||
    target.startsWith("https://")
  ) {
    if (target.includes("dicebear")) {
      return DEFAULT_AVATAR.url;
    }
    return target;
  }
  return DEFAULT_AVATAR.url;
}
