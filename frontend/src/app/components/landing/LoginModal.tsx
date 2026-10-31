"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

interface LoginModalProps {
  onClose?: () => void;
}

export default function LoginModal({ onClose }: LoginModalProps) {
  const router = useRouter();

  useEffect(() => {
    if (onClose) onClose();
    router.push("/login");
  }, [router, onClose]);

  return null;
}
