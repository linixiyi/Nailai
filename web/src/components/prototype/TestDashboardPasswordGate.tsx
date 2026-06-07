"use client";

import { FormEvent, useEffect, useState } from "react";
import { LockKeyhole } from "lucide-react";
import { getTestDashboardPassword, setTestDashboardPassword } from "@/lib/testDashboardAuth";

type TestDashboardPasswordGateProps = {
  title: string;
  description: string;
  error?: string | null;
  onUnlock: () => void | Promise<void>;
};

export function TestDashboardPasswordGate({
  title,
  description,
  error,
  onUnlock,
}: TestDashboardPasswordGateProps) {
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setPassword(getTestDashboardPassword());
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setTestDashboardPassword(password.trim());
    try {
      await onUnlock();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-[#f7f4f2] p-4 text-[#2b1820]">
      <form onSubmit={handleSubmit} className="w-full max-w-md rounded-[28px] border border-black/10 bg-white p-6 shadow-[0_18px_60px_rgba(43,24,32,0.08)]">
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[#fff0f4] text-[#ff5c74]">
            <LockKeyhole size={20} />
          </div>
          <div>
            <p className="text-xs font-bold text-[#ff5c74]">PRIVATE QA</p>
            <h1 className="text-lg font-black">{title}</h1>
          </div>
        </div>
        <p className="mt-4 text-sm leading-6 text-[#7f6870]">{description}</p>
        <label className="mt-5 block text-sm font-bold">
          访问密码
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="mt-2 w-full rounded-2xl border border-black/10 bg-[#faf7f6] px-4 py-3 outline-none transition focus:border-[#ff8da0] focus:bg-white"
            placeholder="输入测试面板密码"
            autoComplete="current-password"
          />
        </label>
        {error ? <p className="mt-3 text-sm font-bold text-red-600">{error}</p> : null}
        <button
          type="submit"
          disabled={!password.trim() || submitting}
          className="mt-5 w-full rounded-2xl bg-[#2b1820] px-4 py-3 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? "验证中..." : "进入测试面板"}
        </button>
      </form>
    </main>
  );
}
