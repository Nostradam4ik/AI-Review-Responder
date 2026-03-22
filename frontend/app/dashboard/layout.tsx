"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { logout } from "@/lib/auth";
import { useLocaleContext, type Locale } from "@/components/LocaleProvider";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { usersApi, reviewsApi } from "@/lib/api";
import { useTheme } from "next-themes";
import {
  LayoutDashboard,
  MessageSquare,
  Settings,
  CreditCard,
  LogOut,
  Star,
  ChevronLeft,
  ChevronRight,
  Sun,
  Moon,
  Menu,
  X,
} from "lucide-react";

const LANGS: { code: Locale; label: string }[] = [
  { code: "en", label: "EN" },
  { code: "fr", label: "FR" },
  { code: "uk", label: "UK" },
  { code: "de", label: "DE" },
  { code: "pl", label: "PL" },
  { code: "es", label: "ES" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const t = useTranslations("nav");
  const { locale, setLocale } = useLocaleContext();
  const { resolvedTheme, setTheme } = useTheme();

  const [mounted, setMounted] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [user, setUser] = useState<{ email?: string; business_name?: string } | null>(null);
  const [pendingCount, setPendingCount] = useState(0);

  useEffect(() => { setMounted(true); }, []);

  useEffect(() => {
    usersApi.me().then(setUser).catch(() => {});
    reviewsApi.list({ status: "pending", limit: 1 }).then((d) => setPendingCount(d.total)).catch(() => {});
  }, []);

  const navItems = [
    { href: "/dashboard", label: t("dashboard"), icon: LayoutDashboard, exact: true },
    { href: "/dashboard/reviews", label: t("reviews"), icon: MessageSquare, badge: pendingCount > 0 ? pendingCount : null },
    { href: "/dashboard/settings", label: t("settings"), icon: Settings },
    { href: "/dashboard/billing", label: t("billing"), icon: CreditCard },
  ];

  const isActive = (href: string, exact?: boolean) =>
    exact ? pathname === href : pathname === href || pathname.startsWith(href + "/");

  const sidebarContent = (
    <>
      {/* Logo */}
      <div className={`flex items-center gap-3 px-4 py-5 border-b border-[#2A2A3E] ${collapsed ? "justify-center" : ""}`}>
        <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center shrink-0">
          <Star className="w-4 h-4 text-white" fill="currentColor" />
        </div>
        {!collapsed && (
          <div>
            <p className="text-[13px] font-semibold text-white leading-tight">AI Review Responder</p>
            <p className="text-[11px] text-slate-500 mt-0.5">by Nostra</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-2 space-y-0.5">
        {navItems.map(({ href, label, icon: Icon, badge, exact }) => {
          const active = isActive(href, exact);
          return (
            <Link
              key={href}
              href={href}
              onClick={() => setMobileOpen(false)}
              title={collapsed ? label : undefined}
              className={`flex items-center gap-3 rounded-lg text-sm font-medium transition-all duration-150 relative group ${
                active
                  ? "bg-indigo-600/10 text-white border-l-2 border-indigo-500 pl-[10px] pr-3 py-2.5"
                  : "text-slate-400 hover:text-white hover:bg-[#1A1A2E]/70 border-l-2 border-transparent pl-[10px] pr-3 py-2.5"
              } ${collapsed ? "justify-center" : ""}`}
            >
              <Icon className={`w-[18px] h-[18px] shrink-0 ${active ? "text-indigo-400" : ""}`} />
              {!collapsed && (
                <>
                  <span className="flex-1 truncate">{label}</span>
                  {badge != null && (
                    <span className="bg-amber-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center leading-none">
                      {badge}
                    </span>
                  )}
                </>
              )}
              {collapsed && badge != null && (
                <span className="absolute top-1 right-1 w-2 h-2 bg-amber-500 rounded-full pulse-dot" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Bottom: lang + user + logout */}
      <div className="border-t border-[#2A2A3E] p-3 space-y-3">
        {/* Language switcher */}
        {!collapsed && (
          <div className="flex flex-wrap gap-0.5 px-1">
            {LANGS.map((lang, i) => (
              <span key={lang.code} className="flex items-center">
                {i > 0 && <span className="text-slate-700 text-[10px] mx-0.5">|</span>}
                <button
                  onClick={() => setLocale(lang.code)}
                  className={`px-1 py-0.5 text-[11px] font-medium transition-colors ${
                    locale === lang.code ? "text-indigo-400" : "text-slate-600 hover:text-slate-300"
                  }`}
                >
                  {lang.label}
                </button>
              </span>
            ))}
          </div>
        )}

        {/* User info row */}
        <div className={`flex items-center gap-2 ${collapsed ? "justify-center" : ""}`}>
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-[11px] font-bold shrink-0">
            {(user?.business_name || user?.email || "U")[0].toUpperCase()}
          </div>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-[12px] font-medium text-white truncate leading-tight">{user?.business_name || "User"}</p>
              <p className="text-[11px] text-slate-500 truncate">{user?.email}</p>
            </div>
          )}
          {/* Theme toggle */}
          <button
            onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
            title="Toggle theme"
            className="w-6 h-6 rounded-md flex items-center justify-center text-slate-500 hover:text-slate-300 hover:bg-[#1A1A2E] transition shrink-0"
          >
            {mounted ? (resolvedTheme === "dark" ? <Sun className="w-3 h-3" /> : <Moon className="w-3 h-3" />) : <div className="w-3 h-3" />}
          </button>
        </div>

        {/* Logout */}
        <button
          onClick={logout}
          title={collapsed ? t("signOut") : undefined}
          className={`flex items-center gap-2 w-full px-2 py-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-[#1A1A2E]/70 transition text-xs ${
            collapsed ? "justify-center" : ""
          }`}
        >
          <LogOut className="w-3.5 h-3.5 shrink-0" />
          {!collapsed && <span>{t("signOut")}</span>}
        </button>
      </div>
    </>
  );

  return (
    <div className="min-h-screen bg-[#0A0A0F] flex">
      {/* Desktop sidebar */}
      <aside
        className={`hidden md:flex fixed left-0 top-0 h-full flex-col bg-[#111118] border-r border-[#2A2A3E] z-30 transition-all duration-200 ${
          collapsed ? "w-[60px]" : "w-[240px]"
        }`}
      >
        {sidebarContent}
        {/* Collapse button */}
        <button
          onClick={() => setCollapsed((v) => !v)}
          className="absolute -right-3 top-[72px] w-6 h-6 bg-[#1A1A2E] border border-[#2A2A3E] rounded-full flex items-center justify-center text-slate-500 hover:text-white transition z-10"
        >
          {collapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}
        </button>
      </aside>

      {/* Mobile topbar */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-40 bg-[#111118] border-b border-[#2A2A3E] px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-indigo-600 rounded-md flex items-center justify-center">
            <Star className="w-3 h-3 text-white" fill="currentColor" />
          </div>
          <span className="text-[13px] font-semibold text-white">AI Review Responder</span>
        </div>
        <button onClick={() => setMobileOpen((v) => !v)} className="text-slate-400 hover:text-white transition p-1">
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile sidebar overlay */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-30" onClick={() => setMobileOpen(false)}>
          <div className="absolute inset-0 bg-black/60" />
          <aside
            className="absolute left-0 top-0 h-full w-[240px] bg-[#111118] border-r border-[#2A2A3E] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {sidebarContent}
          </aside>
        </div>
      )}

      {/* Main content */}
      <main
        className={`flex-1 min-h-screen transition-all duration-200 ${
          collapsed ? "md:ml-[60px]" : "md:ml-[240px]"
        } pt-[52px] md:pt-0 p-6 md:p-8 max-w-none`}
      >
        {children}
      </main>
    </div>
  );
}
